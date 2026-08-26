from __future__ import annotations

import os
from typing import Optional

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover
    genai = None
    types = None


class LLMError(RuntimeError):
    pass


class GeminiGenerator:
    """Small Gemini wrapper used only for grounded response generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY", "")
        ).strip()

        self.model = (
            model
            or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        ).strip()

        self.use_llm = (
            os.getenv("USE_LLM", "true")
            .strip()
            .lower()
            not in {"0", "false", "no", "off"}
        )

        self._client = None

    @property
    def configured(self) -> bool:
        return (
            self.use_llm
            and bool(self.api_key)
            and genai is not None
            and types is not None
        )

    def _client_or_raise(self):
        if not self.use_llm:
            raise LLMError("LLM usage is disabled by USE_LLM")

        if not self.api_key:
            raise LLMError("GEMINI_API_KEY is not configured")

        if genai is None or types is None:
            raise LLMError(
                "google-genai is not installed"
            )

        if self._client is None:
            self._client = genai.Client(
                api_key=self.api_key
            )

        return self._client

    def generate(
        self,
        system_instruction: str,
        prompt: str,
    ) -> str:

        client = self._client_or_raise()

        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.0,
                max_output_tokens=500,
            )

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            text = getattr(response, "text", None)

            if not text:
                raise LLMError(
                    "Gemini returned an empty response"
                )

            return text.strip()

        except LLMError:
            raise

        except Exception as exc:
            raise LLMError(
                f"Gemini request failed: {type(exc).__name__}: {exc}"
            ) from exc