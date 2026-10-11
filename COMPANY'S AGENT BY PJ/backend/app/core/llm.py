"""Thin wrapper around the Gemini API (google-genai SDK).

Raises LLMNotConfigured when no API key is set so callers can fall back to
demo mode instead of crashing.
"""
from __future__ import annotations

import json
import re

from google import genai
from google.genai import types


class LLMNotConfigured(RuntimeError):
    pass


class LLMClient:
    def __init__(self, api_key: str, model: str, temperature: float = 0.2):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    @property
    def client(self) -> genai.Client:
        if not self.api_key:
            raise LLMNotConfigured("GEMINI_API_KEY is not set (see backend/.env.example)")
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _config(self, temperature: float | None, json_mode: bool) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=self.temperature if temperature is None else temperature,
            response_mime_type="application/json" if json_mode else None,
        )

    def generate(self, prompt: str, temperature: float | None = None, json_mode: bool = False) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._config(temperature, json_mode),
        )
        return response.text or ""


def extract_json(text: str):
    """Pull the first JSON object/array out of an LLM reply (models sometimes
    wrap JSON in markdown fences or prose)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None
