"""LLM Provider 抽象."""
from .base import LLMProvider, LLMResponse, ToolDefinition
from .factory import create_llm_provider, register_provider
from .tools import AgentTools

try:
    from .vision_provider import VisionLLM, VisionPrompt, VisionOpenAIProvider, create_vision_llm
except ImportError:
    VisionLLM = None  # type: ignore
    VisionPrompt = None  # type: ignore
    VisionOpenAIProvider = None  # type: ignore
    create_vision_llm = None  # type: ignore

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ToolDefinition",
    "AgentTools",
    "create_llm_provider",
    "register_provider",
    "VisionLLM",
    "VisionPrompt",
    "VisionOpenAIProvider",
    "create_vision_llm",
]
