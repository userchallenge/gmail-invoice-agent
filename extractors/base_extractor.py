from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import anthropic
import json
import logging
import os
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
            
            logger.debug(f"Making HTTP request to Claude API - Model: {model}, Max tokens: {max_tokens}")
            
            response = self.claude.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": cleaned_prompt}]
            )
            
            logger.debug(f"Claude API response received - Usage: {getattr(response, 'usage', 'N/A')}")
            
            # Extract text from Claude's response - handle different response types
            try:
                content_block = response.content[0]
                if hasattr(content_block, 'text'):
                    response_text = content_block.text.strip()
                else:
                    # Handle other content types by converting to string
                    response_text = str(content_block).strip()
            except (AttributeError, IndexError):
                response_text = str(response.content).strip()
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error calling Claude for {self.name}: {e}")
            return ""
    
    def _parse_json_response(self, response_text: str, is_array: bool = False) -> tuple[Dict | List[Dict], Dict[str, str]]:
        """Parse Claude's JSON response with robust error handling and extract reasoning"""
        reasoning_data = {"before": "", "after": ""}
        
        try:
            # Clean up response (remove any markdown formatting)
            json_text = response_text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0]
            
            # Extract JSON part from response
            if is_array:
                # Looking for array format - find properly balanced brackets
                json_start = json_text.find('[')
                if json_start >= 0:
                    bracket_count = 0
                    json_end = json_start
                    for i, char in enumerate(json_text[json_start:], json_start):
                        if char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                json_end = i + 1
                                break
                    
                    if json_end > json_start:
                        extracted_json = json_text[json_start:json_end]
                        
                        # Extract reasoning and log
                        reasoning_data = self._extract_reasoning(response_text, json_start, json_end)
                        
                        try:
                            parsed_data = json.loads(extracted_json)
                            logger.debug(f"Claude {self.name} JSON output: {extracted_json}")
                            return parsed_data, reasoning_data
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse array JSON, trying fallback: {e}")
                            # Continue to fallback
                    
                # Fallback: try single object wrapped in array
                json_start = json_text.find('{')
                json_end = json_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    extracted_json = json_text[json_start:json_end]
                    reasoning_data = self._extract_reasoning(response_text, json_start, json_end)
                    single_item = json.loads(extracted_json)
                    result = [single_item] if single_item else []
                    logger.debug(f"Claude {self.name} JSON output: {extracted_json}")
                    return result, reasoning_data
            else:
                # Looking for object format
                json_start = json_text.find("{")
                if json_start >= 0:
                    # Find the closing brace by counting braces
                    brace_count = 0
                    json_end = json_start
                    for i, char in enumerate(json_text[json_start:], json_start):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    
                    if json_end > json_start:
                        extracted_json = json_text[json_start:json_end]
                        
                        # Extract reasoning and log
                        reasoning_data = self._extract_reasoning(response_text, json_start, json_end)
                        
                        try:
                            parsed_data = json.loads(extracted_json)
                            logger.debug(f"Claude {self.name} JSON output: {extracted_json}")
                            return parsed_data, reasoning_data
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse object JSON: {e}")
                            # Fall through to error handling
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON for {self.name}: {e}")
            logger.debug(f"Full Claude response: {response_text}")
        except Exception as e:
            logger.error(f"Error parsing Claude response for {self.name}: {e}")
            
        return ([] if is_array else {}), reasoning_data
    
    def _extract_reasoning(self, full_response: str, json_start: int, json_end: int) -> Dict[str, str]:
        """Extract Claude's reasoning text that appears before/after JSON"""
        reasoning_data = {"before": "", "after": ""}
        
        # Extract reasoning before JSON
        if json_start > 0:
            reasoning_before = full_response[:json_start].strip()
            if reasoning_before:
                reasoning_data["before"] = reasoning_before
                logger.debug(f"Claude's {self.name} reasoning (before): {reasoning_before}")
        
        # Extract reasoning after JSON
        if json_end < len(full_response):
            reasoning_after = full_response[json_end:].strip()
            if reasoning_after:
                reasoning_data["after"] = reasoning_after
                logger.debug(f"Claude's {self.name} reasoning (after): {reasoning_after}")
        
        return reasoning_data
    
    def _save_email_backup(self, email_content: str, email_metadata: Dict) -> str:
        """Save email content to consolidated processing file"""
        try:
            # Create directory structure: emails/
            backup_dir = 'emails'
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create consolidated filename with timestamp 
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            backup_filename = f"processing_{timestamp}.txt"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Get or create the global file for this processing session
            if not hasattr(self.__class__, '_current_backup_file') or not self.__class__._current_backup_file:
                self.__class__._current_backup_file = backup_path
                # Write header for new session
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== EMAIL PROCESSING SESSION ===\n")
                    f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'='*50}\n\n")
            
            # Prepare email content (without PDF info)
            email_id = email_metadata.get('id', 'unknown')
            subject = email_metadata.get('subject', '')
            sender = email_metadata.get('sender', '') 
            date = email_metadata.get('date', '')
            attachments = email_metadata.get('attachments', [])
            
            email_entry = f"""--- EMAIL {email_id} ---
Subject: {subject}
From: {sender}
Date: {date}
Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Extractor: {self.name}
Attachments: {len(attachments)} files

EMAIL BODY:
{email_content}

{'='*80}

"""
            
            # Append to consolidated file
            with open(self.__class__._current_backup_file, 'a', encoding='utf-8') as f:
                f.write(email_entry)
            
            logger.debug(f"Email appended to backup: {self.__class__._current_backup_file}")
            return self.__class__._current_backup_file
            
        except Exception as e:
            logger.error(f"Error saving email backup: {e}")
            return ""
    
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
    
    def _format_prompt_template(self, email_content: str, email_metadata: Dict, **kwargs) -> str:
        """Format the prompt template with dynamic content"""
        template = self.config.get('prompt_template', '')
        if not template:
            raise ValueError(f"No prompt_template found in config for {self.name} extractor")
        
        # Prepare email content with metadata (exclude PDF content)
        subject = self._clean_text(email_metadata.get('subject', ''))
        sender = self._clean_text(email_metadata.get('sender', ''))
        
        # Remove PDF content from email body
        body = self._clean_text(email_content)
        if "--- PDF CONTENT ---" in body:
            body = body.split("--- PDF CONTENT ---")[0].strip()
        body = body[:2000]  # Limit body length
        
        email_content_formatted = f"""
Subject: {subject}
From: {sender}
Date: {email_metadata.get('date', '')}
Body: {body}

Attachments: {[self._clean_text(att.get('filename', '')) for att in email_metadata.get('attachments', [])]}
"""
        
        # Default template variables
        template_vars = {
            'email_content': email_content_formatted,
            'swedish_keywords': ', '.join(self.config.get('keywords', {}).get('swedish', [])),
            'english_keywords': ', '.join(self.config.get('keywords', {}).get('english', [])),
        }
        
        # Add any additional variables passed as kwargs
        template_vars.update(kwargs)
        
        try:
            return template.format(**template_vars)
        except KeyError as e:
            logger.error(f"Missing template variable {e} in {self.name} prompt template")
            raise ValueError(f"Template variable {e} not provided for {self.name} extractor")
        except Exception as e:
            logger.error(f"Error formatting prompt template for {self.name}: {e}")
            raise