import logging
from typing import Optional
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)

class OllamaTranslationService:
    """
    Service to translate foundation purposes from old/legalese Swedish to modern Swedish
    using the Ollama API at https://ollama.labb.site
    """
    
    def __init__(self):
        # Use the configured OLLAMA_URL from settings, falling back to the labb.site address
        self.ollama_url = getattr(settings, 'OLLAMA_URL', 'https://ollama.labb.site')
        # Using a model that should work well with 16GB RAM, such as Phi 3 or Llama 3
        self.model = getattr(settings, 'OLLAMA_MODEL', 'phi3:14b')  # Default to phi3 which works well on 16GB
        self.timeout = 60  # seconds
    
    def translate_purpose(self, purpose: str, model: str = None, custom_prompt: str = None) -> Optional[str]:
        """
        Translate a foundation purpose from old/legalese Swedish to modern Swedish
        
        Args:
            purpose: The original purpose text to translate
            model: Optional model override (defaults to self.model)
            custom_prompt: Optional custom prompt template (use {purpose} as placeholder)
            
        Returns:
            Translated purpose text, or None if translation fails
        """
        if not purpose or not purpose.strip():
            return purpose
        
        use_model = model or self.model
        
        if custom_prompt:
            prompt = custom_prompt.replace("{purpose}", purpose)
        else:
            prompt = self._create_translation_prompt(purpose)
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": use_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for more consistent translations
                        "num_ctx": 4096,     # Context length
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result.get('response', '').strip()
                
                # If translation is empty, return original
                if not translated_text:
                    logger.warning(f"Empty translation returned for purpose: {purpose[:100]}...")
                    return purpose
                
                return translated_text
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during translation: {e}")
            return None
    
    def get_default_model(self) -> str:
        """Return the default model being used"""
        return self.model
    
    def get_default_prompt_template(self) -> str:
        """Return the default prompt template with {purpose} placeholder"""
        return (
            "Du är en expert på äldre juridisk och formell svenska. "
            "Din uppgift är att översätta äldre, formell språkbruk till modern, korrekt och formell svenska. "
            "Bevara den fullständiga juridiska innebörden och den ursprungliga tonen. "
            "Använd modern, juridisk terminologi där det är lämpligt, "
            "till exempel \"ekonomiskt stöd\" eller \"bidrag\" istället för \"understöd\". "
            "Svara endast med den översatta texten.\\n\\n"
            "Text: {purpose}"
        )

    def _create_translation_prompt(self, purpose: str) -> str:
        """
        Create a prompt to translate old/legalese Swedish to modern Swedish
        
        Args:
            purpose: The original purpose text
            
        Returns:
            Formatted prompt for the LLM
        """
        return (
            "Du är en expert på äldre juridisk och formell svenska. "
            "Din uppgift är att översätta äldre, formell språkbruk till modern, korrekt och formell svenska. "
            "Bevara den fullständiga juridiska innebörden och den ursprungliga tonen. "
            "Använd modern, juridisk terminologi där det är lämpligt, "
            "till exempel \"ekonomiskt stöd\" eller \"bidrag\" istället för \"understöd\". "
            "Svara endast med den översatta texten.\n\n"
            f"Text: {purpose}"
        )

    def health_check(self) -> bool:
        """
        Check if the Ollama service is accessible
        
        Returns:
            True if the service is accessible, False otherwise
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            return response.status_code == 200
        except:
            return False


# Create a global instance
ollama_translation_service = OllamaTranslationService()