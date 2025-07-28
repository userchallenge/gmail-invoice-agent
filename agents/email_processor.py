from typing import Dict, List
import anthropic
import logging
from extractors.base_extractor import BaseExtractor
from extractors.invoice_extractor import InvoiceExtractor  
from extractors.concert_extractor import ConcertExtractor

logger = logging.getLogger(__name__)

class EmailProcessor:
    """Processes emails through multiple specialized extractors"""
    
    def __init__(self, config: Dict, claude_api_key: str):
        self.config = config
        self.claude = anthropic.Anthropic(api_key=claude_api_key)
        self.extractors = self._initialize_extractors()
        
    def _initialize_extractors(self) -> List[BaseExtractor]:
        """Initialize all enabled extractors from config"""
        extractors = []
        
        extractors_config = self.config.get('extractors', {})
        
        # Initialize invoice extractor if enabled
        if extractors_config.get('invoices', {}).get('enabled', True):
            invoice_config = extractors_config['invoices']
            # Add model config to extractor config
            invoice_config['claude_model'] = self.config.get('claude', {}).get('model', 'claude-3-5-sonnet-20241022')
            extractors.append(InvoiceExtractor(invoice_config, self.claude))
            logger.info("✓ Invoice extractor initialized")
            
        # Initialize concert extractor if enabled  
        if extractors_config.get('concerts', {}).get('enabled', False):
            concert_config = extractors_config['concerts']
            # Add model config to extractor config
            concert_config['claude_model'] = self.config.get('claude', {}).get('model', 'claude-3-5-sonnet-20241022')
            extractors.append(ConcertExtractor(concert_config, self.claude))
            logger.info("✓ Concert extractor initialized")
            
        logger.info(f"Initialized {len(extractors)} extractors")
        return extractors
    
    def get_extractor_by_name(self, name: str):
        """Get a specific extractor by name"""
        for extractor in self.extractors:
            if extractor.name == name:
                return extractor
        return None
    
    def process_email(self, email_content: str, email_metadata: Dict) -> Dict:
        """Process email through all applicable extractors"""
        results = {}
        
        sender = email_metadata.get('sender', '')
        subject = email_metadata.get('subject', '')
        
        logger.debug(f"Processing email: {subject[:50]}...")
        
        for extractor in self.extractors:
            try:
                if extractor.should_process(email_content, sender, subject):
                    logger.debug(f"Running {extractor.name} extractor on email")
                    extracted_items = extractor.extract(email_content, email_metadata)
                    if extracted_items:
                        results[extractor.name] = extracted_items
                        logger.info(f"✓ {extractor.name} extractor found {len(extracted_items)} item(s)")
                else:
                    logger.debug(f"{extractor.name} extractor skipped email (no match criteria)")
            except Exception as e:
                logger.error(f"Error in {extractor.name} extractor: {e}")
                continue
                    
        return results
    
    def get_search_keywords(self) -> List[str]:
        """Get combined keywords for Gmail search from all extractors"""
        all_keywords = []
        for extractor in self.extractors:
            keywords = extractor.get_search_keywords()
            all_keywords.extend(keywords)
        
        # Remove duplicates while preserving order
        unique_keywords = []
        seen = set()
        for keyword in all_keywords:
            if keyword.lower() not in seen:
                unique_keywords.append(keyword)
                seen.add(keyword.lower())
        
        logger.debug(f"Combined search keywords from {len(self.extractors)} extractors: {len(unique_keywords)} unique keywords")
        return unique_keywords
    
    def get_search_filters(self) -> List[str]:
        """Get combined search filters from all extractors"""
        all_filters = []
        for extractor in self.extractors:
            filters = extractor.get_additional_search_filters()
            all_filters.extend(filters)
        
        # Remove duplicates
        unique_filters = list(set(all_filters))
        logger.debug(f"Combined search filters from {len(self.extractors)} extractors: {unique_filters}")
        return unique_filters
    
    def get_enabled_extractors(self) -> List[str]:
        """Get list of enabled extractor names"""
        return [extractor.name for extractor in self.extractors]
    
    def get_extractor_output_files(self) -> Dict[str, str]:
        """Get mapping of extractor names to their output files"""
        return {extractor.name: extractor.output_filename for extractor in self.extractors}