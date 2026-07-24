"""语音识别（ASR）模块."""
from .base import ASRProvider, ASRResult
from .factory import create_asr_provider, register_asr_provider
from .openai_whisper import OpenAIWhisperASR

__all__ = ["ASRProvider", "ASRResult", "OpenAIWhisperASR", "create_asr_provider", "register_asr_provider"]
