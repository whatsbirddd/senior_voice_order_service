from __future__ import annotations

import io
import os
from urllib.parse import parse_qs, urlparse
from typing import Any, Dict, List, Optional, Tuple


class AzureLLM:
    """Thin wrapper for Azure OpenAI Chat Completions with tool/function-calling.

    Uses environment variables:
      - AZURE_OPENAI_API_KEY
      - AZURE_OPENAI_ENDPOINT
      - AZURE_OPENAI_DEPLOYMENT (model deploy name)
      - AZURE_OPENAI_API_VERSION (default: 2024-08-01-preview)
    """

    def __init__(self) -> None:
        self.key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
        raw_endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip()
        self.deployment = (os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip()
        self.api_version = (os.getenv("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()

        base, deployment, api_version = _parse_azure_endpoint(raw_endpoint)
        if base:
            self.endpoint = base
        else:
            self.endpoint = raw_endpoint or None
        if deployment and not self.deployment:
            self.deployment = deployment
        if api_version:
            self.api_version = api_version

        self._client = None
        if self.key and self.endpoint and self.deployment:
            try:
                from openai import AzureOpenAI  # type: ignore

                self._client = AzureOpenAI(
                    api_key=self.key,
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint,
                )
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, tool_choice: Optional[str] = None) -> Dict[str, Any]:
        if not self.available:
            return {"error": "LLM not configured"}
        try:
            resp = self._client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                tools=tools or None,
                tool_choice=tool_choice or "auto",
                temperature=0.3,
            )
            choice = resp.choices[0]
            msg = choice.message
            out: Dict[str, Any] = {"role": msg.role or "assistant", "content": msg.content}
            if msg.tool_calls:
                tc = msg.tool_calls[0]
                out["tool_call"] = {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
            return out
        except Exception as e:
            return {"error": str(e)}


class AzureAudioTranscriber:
    """Wrapper to call Azure OpenAI audio transcription (Whisper / GPT-4o-transcribe)."""

    def __init__(self) -> None:
        self.key = (os.getenv("AZURE_OPENAI_API_KEY") or "").strip()
        raw_endpoint = (os.getenv("AUDIO_OPENAI_ENDPOINT") or os.getenv("AZURE_AUDIO_ENDPOINT") or "").strip()
        self.deployment = (os.getenv("AUDIO_OPENAI_DEPLOYMENT") or "").strip()
        self.api_version = (os.getenv("AUDIO_OPENAI_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview").strip()

        base, deployment, api_version = _parse_azure_endpoint(raw_endpoint)
        if base:
            self.endpoint = base
        else:
            self.endpoint = raw_endpoint or None
        if deployment and not self.deployment:
            self.deployment = deployment
        if api_version:
            self.api_version = api_version

        self._client = None
        if self.key and self.endpoint and self.deployment:
            try:
                from openai import AzureOpenAI  # type: ignore

                self._client = AzureOpenAI(
                    api_key=self.key,
                    api_version=self.api_version,
                    azure_endpoint=self.endpoint,
                )
            except Exception:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def transcribe(self, audio: bytes, filename: str = "audio.wav", mime_type: str = "audio/wav") -> Dict[str, Any]:
        if not self.available:
            return {"error": "Audio model not configured"}
        try:
            buffer = io.BytesIO(audio)
            buffer.name = filename
            result = self._client.audio.transcriptions.create(  # type: ignore[call-arg]
                model=self.deployment,
                file=buffer,
                response_format="verbose_json",
            )
            text = getattr(result, "text", None)
            if text is None and isinstance(result, dict):
                text = result.get("text")
            raw_payload: Optional[Dict[str, Any]] = None
            if hasattr(result, "to_dict_recursive"):
                raw_payload = result.to_dict_recursive()  # type: ignore[attr-defined]
            elif isinstance(result, dict):
                raw_payload = result
            return {
                "text": text,
                "raw": raw_payload,
            }
        except Exception as exc:  # pragma: no cover - network failures
            return {"error": str(exc)}


def _parse_azure_endpoint(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not url:
        return None, None, None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None, None, None
    segments = [seg for seg in parsed.path.split("/") if seg]
    base_segments: List[str] = []
    deployment = None
    if "deployments" in segments:
        idx = segments.index("deployments")
        base_segments = segments[:idx]
        if idx + 1 < len(segments):
            deployment = segments[idx + 1]
    else:
        base_segments = segments
    base_path = "/".join(base_segments)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base_path:
        base = f"{base}/{base_path}"
    if base and not base.endswith("/"):
        base = base + "/"
    query = parse_qs(parsed.query or "")
    api_version = (query.get("api-version") or [None])[0]
    return base, deployment, api_version


__all__ = ["AzureLLM", "AzureAudioTranscriber"]
