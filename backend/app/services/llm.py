from __future__ import annotations

from groq import Groq

from app.core.config import Settings


class LLMService:
    """
    Handles communication with the Groq LLM API.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not configured.")

        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.llm_model

    def generate(
        self,
        prompt: str,
        temperature: float = 0.0,
    ) -> str:
        """
        Generate a response from the configured Groq model.
        """
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=temperature,
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError("LLM returned an empty response.")

        return content