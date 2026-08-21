import logging

import requests

from app.core.config import settings
from app.services.llm_client import chat_completion, litellm_headers, litellm_url

logger = logging.getLogger(__name__)

class LLMTranslationService:
    """
    Service to translate foundation purposes from old/legalese Swedish to modern Swedish
    using the LiteLLM OpenAI-compatible chat completions API.
    """

    def __init__(self):
        self.model = getattr(settings, 'LITELLM_TEXT_MODEL', 'gemma-4-12b')
        self.timeout = 120  # seconds

    def translate_purpose(self, purpose: str, model: str | None = None, custom_prompt: str | None = None) -> str | None:
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

        translated_text = chat_completion(prompt, model=use_model, temperature=0.1, timeout=self.timeout)

        # If translation failed or is empty, fall back appropriately
        if translated_text is None:
            return None
        if not translated_text:
            logger.warning(f"Empty translation returned for purpose: {purpose[:100]}...")
            return purpose

        return translated_text

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
        Check if the LiteLLM service is accessible and the configured text model is served.

        Returns:
            True if the service is accessible, False otherwise
        """
        try:
            response = requests.get(f"{litellm_url()}/v1/models", headers=litellm_headers(), timeout=10)
            if response.status_code == 200:
                models_data = response.json().get('data', [])
                model_ids = [m.get('id', '') for m in models_data]
                return any(self.model in mid for mid in model_ids)
            return False
        except Exception:
            return False


# Create a global instance
llm_translation_service = LLMTranslationService()
