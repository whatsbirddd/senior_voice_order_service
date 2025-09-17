from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:  # External dependency; keep optional for tests
    import azure.cognitiveservices.speech as speechsdk  # type: ignore
except ImportError:  # pragma: no cover - gracefully degrade if package missing
    speechsdk = None  # type: ignore


@dataclass
class SpeechResult:
    text: Optional[str]
    raw: Dict[str, Any]
    error: Optional[str] = None


class AzureSpeechService:
    """Thin wrapper around Azure Cognitive Services Speech SDK for file transcription."""

    def __init__(self) -> None:
        self.key = (os.getenv("AZURE_SPEECH_KEY") or os.getenv("SPEECH_KEY") or "").strip()
        self.region = (os.getenv("AZURE_SPEECH_REGION") or os.getenv("SPEECH_REGION") or "").strip()
        self.endpoint = (os.getenv("AZURE_SPEECH_ENDPOINT") or os.getenv("SPEECH_ENDPOINT") or "").strip()
        self.language = (os.getenv("AZURE_SPEECH_LANGUAGE") or "ko-KR").strip()

        self._config = None
        if speechsdk is None:
            return
        if not self.key:
            return
        try:
            if self.endpoint:
                cfg = speechsdk.SpeechConfig(subscription=self.key, endpoint=self.endpoint)
            elif self.region:
                cfg = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
            else:
                return
            cfg.speech_recognition_language = self.language
            self._config = cfg
        except Exception:
            self._config = None

    @property
    def available(self) -> bool:
        return self._config is not None and speechsdk is not None

    def transcribe(self, audio: bytes) -> SpeechResult:
        if not self.available:
            return SpeechResult(text=None, raw={}, error="Azure Speech SDK not configured")
        assert speechsdk is not None  # for type checkers
        stream = speechsdk.audio.PushAudioInputStream()
        stream.write(audio)
        stream.close()
        audio_config = speechsdk.audio.AudioConfig(stream=stream)
        recognizer = speechsdk.SpeechRecognizer(speech_config=self._config, audio_config=audio_config)
        try:
            result = recognizer.recognize_once_async().get()
        except Exception as exc:  # pragma: no cover - network/runtime errors
            return SpeechResult(text=None, raw={}, error=str(exc))

        payload: Dict[str, Any] = {
            "reason": getattr(result, "reason", None),
            "offset": getattr(result, "offset", None),
            "duration": getattr(result, "duration", None),
        }

        reason = getattr(result, "reason", None)
        if reason == speechsdk.ResultReason.RecognizedSpeech:
            payload["text"] = result.text
            return SpeechResult(text=result.text, raw=payload)
        if reason == speechsdk.ResultReason.NoMatch:
            payload["details"] = str(result.no_match_details)
            return SpeechResult(text=None, raw=payload, error="No speech match")
        if reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details
            payload["details"] = str(details.reason)
            if details.reason == speechsdk.CancellationReason.Error:
                payload["error_details"] = details.error_details
            return SpeechResult(text=None, raw=payload, error="Recognition canceled")
        return SpeechResult(text=None, raw=payload, error="Unknown recognition result")


__all__ = ["AzureSpeechService", "SpeechResult"]
