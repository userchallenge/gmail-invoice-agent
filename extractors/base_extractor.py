from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import anthropic
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Base class for all email content extractors"""
    
    def __init__(self, config_section: Dict, claude_client: anthropic.Anthropic):
        self.config = config_section
        self.claude = claude_client
        
    @abstractmethod
    def should_process(self, email_content: str, sender: str, subject: str) -> bool:
        """Determine if this extractor should process the given email"""
        pass
        
    @abstractmethod
    def extract(self, email_content: str, email_metadata: Dict) -> List[Dict]:
        """Extract relevant data from email content. Returns list of extracted items."""
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this extractor"""
        pass
        
    @property
    @abstractmethod
    def output_filename(self) -> str:
        """CSV filename for this extractor's output"""
        pass
        
    def get_search_keywords(self) -> List[str]:
        """Get keywords for Gmail search query building"""
        keywords = []
        if 'keywords' in self.config:
            if 'swedish' in self.config['keywords']:
                keywords.extend(self.config['keywords']['swedish'])
            if 'english' in self.config['keywords']:
                keywords.extend(self.config['keywords']['english'])
        return keywords
    
    def get_additional_search_filters(self) -> List[str]:
        """Get additional search filters specific to this extractor (e.g., attachment filters)"""
        return []
        
    def _check_keywords_in_content(self, content: str, keywords: List[str]) -> bool:
        """Helper method to check if any keywords appear in content"""
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in keywords)
    
    def _clean_text(self, text: str) -> str:
        """Clean text to handle encoding issues and special characters"""
        if not text:
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Replace common problematic characters
        replacements = {
            '\xb4': "'",  # Acute accent
            '\u2019': "'",  # Right single quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u00a0': ' ',  # Non-breaking space
        }
        
        for old_char, new_char in replacements.items():
            text = text.replace(old_char, new_char)
        
        # Remove any remaining non-printable characters
        text = ''.join(char for char in text if char.isprintable() or char.isspace())
        
        # Ensure we can encode to UTF-8
        try:
            text.encode('utf-8')
            return text
        except UnicodeEncodeError:
            # If still problematic, replace non-ASCII with safe alternatives
            return text.encode('ascii', errors='replace').decode('ascii')
        except Exception:
            # Last resort: return empty string
            return ""
    
    def _call_claude(self, prompt: str, max_tokens: int = 1500) -> str:
        """Make a call to Claude API with proper error handling"""
        try:
            # Clean the entire prompt to avoid encoding issues
            cleaned_prompt = self._clean_text(prompt)
            
            logger.debug(f"Sending {self.name} prompt to Claude (first 200 chars): {cleaned_prompt[:200]!r}")

            # Get model from config, fallback to current working model
            model = self.config.get('claude_model', 'claude-3-5-sonnet-20241022')
            
            response = self.claude.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": cleaned_prompt}]
            )
            
            # Extract text from Claude's response - handle different response types
            try:
                if hasattr(response.content[0], 'text'):
                    response_text = response.content[0].text.strip()
                else:
                    # Handle other content types like ToolUseBlock, etc.
                    response_text = str(response.content[0]).strip()
            except (AttributeError, IndexError):
                response_text = str(response.content).strip()
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error calling Claude for {self.name}: {e}")
            return ""
    
    def _parse_json_response(self, response_text: str, is_array: bool = False) -> Dict | List[Dict]:
        """Parse Claude's JSON response with robust error handling"""
        try:
            # Clean up response (remove any markdown formatting)
            json_text = response_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]
            
            # Extract JSON part from response
            if is_array:
                # Looking for array format
                json_start = json_text.find('[')
                json_end = json_text.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    extracted_json = json_text[json_start:json_end]
                    
                    # Log reasoning if there's extra text
                    self._log_claude_reasoning(response_text, json_start, json_end)
                    
                    return json.loads(extracted_json)
                    
                # Fallback: try single object wrapped in array
                json_start = json_text.find('{')
                json_end = json_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    extracted_json = json_text[json_start:json_end]
                    single_item = json.loads(extracted_json)
                    return [single_item] if single_item else []
            else:
                # Looking for object format
                if "{" in json_text and "}" in json_text:
                    start = json_text.find("{")
                    # Find the closing brace by counting braces
                    brace_count = 0
                    end = start
                    for i, char in enumerate(json_text[start:], start):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    extracted_json = json_text[start:end]
                    
                    # Log reasoning if there's extra text
                    self._log_claude_reasoning(response_text, start, end)
                    
                    return json.loads(extracted_json)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON for {self.name}: {e}")
            logger.error(f"Response was: {response_text}")
        except Exception as e:
            logger.error(f"Error parsing Claude response for {self.name}: {e}")
            
        return [] if is_array else {}
    
    def _log_claude_reasoning(self, full_response: str, json_start: int, json_end: int):
        """Log Claude's reasoning text that appears before/after JSON"""
        # Log reasoning before JSON
        if json_start > 0:
            reasoning_before = full_response[:json_start].strip()
            if reasoning_before:
                logger.info(f"Claude's {self.name} reasoning (before): {reasoning_before}")
        
        # Log reasoning after JSON
        if json_end < len(full_response):
            reasoning_after = full_response[json_end:].strip()
            if reasoning_after:
                logger.info(f"Claude's {self.name} reasoning (after): {reasoning_after}")
    
    def _add_email_metadata(self, extracted_items: List[Dict], email_metadata: Dict) -> List[Dict]:
        """Add common email metadata to extracted items"""
        processed_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for item in extracted_items:
            item.update({
                'email_date': email_metadata.get('date', ''),
                'source_sender': email_metadata.get('sender', ''),
                'source_subject': email_metadata.get('subject', ''),
                'email_id': email_metadata.get('id', ''),
                'processed_date': processed_date
            })
        
        return extracted_items