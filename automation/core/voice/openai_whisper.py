# -*- coding: utf-8 -*-
"""OpenAI Whisper API 语音识别实现."""

from typing import Any, Dict

import requests

from .base import ASRProvider, ASRResult


class OpenAIWhisperASR(ASRProvider):
    """调用 OpenAI Whisper API 进行语音识别."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = (config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        self.model = config.get("model", "whisper-1")
        self.language = config.get("language", "zh")
        self.timeout = config.get("timeout", 60)

    def transcribe(self, audio_path: str, **kwargs) -> ASRResult:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {
            "model": kwargs.get("model", self.model),
            "language": kwargs.get("language", self.language),
            "response_format": "json",
        }
        if "prompt" in kwargs:
            data["prompt"] = kwargs["prompt"]

        with open(audio_path, "rb") as f:
            files = {"file": (audio_path, f, "audio/mpeg")}
            resp = requests.post(
                f"{self.base_url}/audio/transcriptions",
                headers=headers,
                data=data,
                files=files,
                timeout=self.timeout,
            )
        resp.raise_for_status()
        result = resp.json()
        return ASRResult(
            text=result.get("text", "").strip(),
            language=result.get("language", self.language),
            raw=result,
        )
