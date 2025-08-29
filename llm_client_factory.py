"""
Generic LLM Client Factory
Creates instructor clients for different LLM providers based on configuration
Supports Gemini, OpenAI, Claude, and other providers
"""

import os
import logging
from typing import Dict, Any
import instructor

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """Factory for creating LLM clients with instructor support"""
    
    SUPPORTED_PROVIDERS = {
        'gemini': 'google-genai',
        'openai': 'openai', 
        'claude': 'anthropic',
    }
    
    @classmethod
    def create_client(cls, provider: str, model: str, api_parameters: Dict[str, Any] = None) -> instructor.Instructor:
        """
        Create an instructor client for the specified provider
        
        Args:
            provider: LLM provider name (gemini, openai, claude)
            model: Model name to use
            api_parameters: Additional parameters for the API
            
        Returns:
            Configured instructor client
            
        Raises:
            ValueError: If provider is not supported
            RuntimeError: If API key is not found or client creation fails
        """
        provider = provider.lower()
        api_parameters = api_parameters or {}
        
        if provider not in cls.SUPPORTED_PROVIDERS:
            supported = ', '.join(cls.SUPPORTED_PROVIDERS.keys())
            raise ValueError(f"Unsupported provider '{provider}'. Supported: {supported}")
        
        try:
            if provider == 'gemini':
                return cls._create_gemini_client(model, api_parameters)
            elif provider == 'openai':
                return cls._create_openai_client(model, api_parameters)
            elif provider == 'claude':
                return cls._create_claude_client(model, api_parameters)
            
        except Exception as e:
            logger.error(f"Failed to create {provider} client: {e}")
            raise RuntimeError(f"Could not initialize {provider} client: {e}")
    
    @classmethod
    def _create_gemini_client(cls, model: str, api_parameters: Dict[str, Any]) -> instructor.Instructor:
        """Create Gemini client using google-genai"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable not found")
        
        try:
            from google import genai
            
            # Create Gemini client
            genai_client = genai.Client(api_key=api_key)
            
            # Create instructor client
            client = instructor.from_genai(
                client=genai_client,
                mode=instructor.Mode.GENAI_TOOLS
            )
            
            logger.info(f"✅ Gemini client created successfully (model: {model})")
            return client
            
        except ImportError as e:
            raise RuntimeError(f"google-genai package not installed: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to create Gemini client: {e}")
    
    @classmethod
    def _create_openai_client(cls, model: str, api_parameters: Dict[str, Any]) -> instructor.Instructor:
        """Create OpenAI client"""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable not found")
        
        try:
            import openai
            
            # Create OpenAI client
            openai_client = openai.OpenAI(api_key=api_key)
            
            # Create instructor client
            client = instructor.from_openai(
                client=openai_client,
                mode=instructor.Mode.TOOLS
            )
            
            logger.info(f"✅ OpenAI client created successfully (model: {model})")
            return client
            
        except ImportError as e:
            raise RuntimeError(f"openai package not installed: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to create OpenAI client: {e}")
    
    @classmethod
    def _create_claude_client(cls, model: str, api_parameters: Dict[str, Any]) -> instructor.Instructor:
        """Create Claude client"""
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            raise RuntimeError("CLAUDE_API_KEY environment variable not found")
        
        try:
            import anthropic
            
            # Create Anthropic client
            anthropic_client = anthropic.Anthropic(api_key=api_key)
            
            # Create instructor client
            client = instructor.from_anthropic(
                client=anthropic_client,
                mode=instructor.Mode.TOOLS
            )
            
            logger.info(f"✅ Claude client created successfully (model: {model})")
            return client
            
        except ImportError as e:
            raise RuntimeError(f"anthropic package not installed: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to create Claude client: {e}")
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """Get list of supported providers"""
        return list(cls.SUPPORTED_PROVIDERS.keys())
    
    @classmethod
    def validate_provider_config(cls, provider: str) -> Dict[str, str]:
        """
        Validate provider configuration and return status
        
        Returns:
            Dict with provider status and required environment variables
        """
        provider = provider.lower()
        status = {
            'provider': provider,
            'supported': provider in cls.SUPPORTED_PROVIDERS,
            'api_key_found': False,
            'api_key_env_var': '',
            'package_available': False
        }
        
        if not status['supported']:
            return status
        
        # Check API key
        if provider == 'gemini':
            env_var = 'GEMINI_API_KEY'
            status['api_key_found'] = bool(os.getenv(env_var))
            status['api_key_env_var'] = env_var
            try:
                import google.genai
                status['package_available'] = True
            except ImportError:
                status['package_available'] = False
                
        elif provider == 'openai':
            env_var = 'OPENAI_API_KEY'
            status['api_key_found'] = bool(os.getenv(env_var))
            status['api_key_env_var'] = env_var
            try:
                import openai
                status['package_available'] = True
            except ImportError:
                status['package_available'] = False
                
        elif provider == 'claude':
            env_var = 'CLAUDE_API_KEY'
            status['api_key_found'] = bool(os.getenv(env_var))
            status['api_key_env_var'] = env_var
            try:
                import anthropic
                status['package_available'] = True
            except ImportError:
                status['package_available'] = False
        
        return status


def get_default_provider() -> str:
    """
    Get the default provider based on available API keys
    Prioritizes in order: Gemini, OpenAI, Claude
    """
    providers = ['gemini', 'openai', 'claude']
    
    for provider in providers:
        status = LLMClientFactory.validate_provider_config(provider)
        if status['api_key_found'] and status['package_available']:
            logger.info(f"Using default provider: {provider}")
            return provider
    
    # Fallback to gemini even without API key for configuration
    logger.warning("No LLM provider API keys found, defaulting to gemini")
    return 'gemini'


def validate_all_providers() -> Dict[str, Dict[str, str]]:
    """Validate configuration for all supported providers"""
    results = {}
    for provider in LLMClientFactory.get_supported_providers():
        results[provider] = LLMClientFactory.validate_provider_config(provider)
    return results