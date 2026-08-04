# -*- coding: utf-8 -*-
"""Vision LLM 提供者：支持带图片（截图）的多模态 LLM 调用.

扩展标准 LLMProvider，允许在 prompt 中携带 base64 截图，
使 LLM 能够"看到"页面并做出视觉感知的决策。

支持：
- OpenAI GPT-4V / GPT-4o  (通过 Chat Completions API 传入 image_url)
- Anthropic Claude 3+        (通过 Messages API 传入 image content block)
- 未来可扩展其他 Vision 模型
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .base import ChatResponse, LLMProvider
from .openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


class VisionPrompt:
    """多模态 Prompt 构造器.

    封装文本+图片的消息构建逻辑，同时输出 OpenAI 和 Anthropic 格式.
    """

    def __init__(self, text: str, images_base64: Optional[List[str]] = None):
        self.text = text
        self.images_base64 = images_base64 or []

    def to_openai_messages(self, system: Optional[str] = None) -> List[Dict]:
        """构建 OpenAI Vision API 格式消息."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        content: List[Dict] = [{"type": "text", "text": self.text}]
        for img in self.images_base64:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img}",
                    "detail": "high",
                },
            })

        messages.append({"role": "user", "content": content})
        return messages

    def to_anthropic_messages(self, system: Optional[str] = None) -> Dict:
        """构建 Anthropic Vision API 格式消息."""
        content: List[Dict] = []
        for img in self.images_base64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img,
                },
            })
        content.append({"type": "text", "text": self.text})

        result = {
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            result["system"] = system
        return result


class VisionOpenAIProvider(OpenAIProvider):
    """支持 Vision 的 OpenAI 提供者.

    基于标准 OpenAI LLMProvider，增加了图片处理能力。
    适用于 GPT-4V, GPT-4o, GPT-4o-mini 等支持 Vision 的模型。
    """

    def complete_with_vision(
        self,
        prompt: str,
        images_base64: Optional[List[str]] = None,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> ChatResponse:
        """带图片的多模态对话.

        Args:
            prompt: 文本 prompt
            images_base64: base64 编码图片列表
            system: 系统消息
            temperature: 温度
            max_tokens: 最大 token

        Returns:
            ChatResponse
        """
        vp = VisionPrompt(prompt, images_base64)
        messages = vp.to_openai_messages(system)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return ChatResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    def extract_json_from_vision(
        self,
        prompt: str,
        images_base64: Optional[List[str]] = None,
        system: Optional[str] = None,
        fallback: Any = None,
    ) -> Any:
        """带图片的多模态调用并解析 JSON 输出."""
        try:
            resp = self.complete_with_vision(prompt, images_base64, system)
            text = self.extract_json(resp.content)
            return json.loads(text)
        except Exception as e:
            logger.warning(f"Vision JSON extraction failed: {e}")
            return fallback


class VisionLLM:
    """Vision LLM 统一门面.

    自动检测底层 LLM Provider 是否支持 Vision，
    并对不支持的 Provider 提供降级（仅使用文本 + DOM 描述）。
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.supports_vision = self._detect_vision_support()

    def _detect_vision_support(self) -> bool:
        """检测 Provider 是否支持 Vision."""
        if isinstance(self.provider, VisionOpenAIProvider):
            return True
        # 检查模型名是否暗示 Vision 能力
        model = getattr(self.provider, "model", "")
        vision_indicators = [
            "gpt-4v", "gpt-4o", "gpt-4-turbo",
            "claude-3", "claude-3.5", "claude-3-opus",
            "gemini-1.5", "gemini-2",
            "vision",
        ]
        return any(ind in model.lower() for ind in vision_indicators)

    def analyze_page(
        self,
        goal: str,
        page_state_text: str,
        history_text: str = "",
        screenshot_base64: str = "",
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分析页面状态并决定下一步操作.

        Args:
            goal: 用户测试目标
            page_state_text: 页面状态文本描述 (PageState.to_llm_context())
            history_text: 历史操作记录
            screenshot_base64: 页面截图base64
            system: 系统提示

        Returns:
            {"action": str, "selector": str, "value": str, "reasoning": str, "done": bool}
        """
        prompt = self._build_exploration_prompt(goal, page_state_text, history_text)

        if self.supports_vision and screenshot_base64:
            return self._call_with_vision(prompt, screenshot_base64, system)
        else:
            return self._call_text_only(prompt, system)

    def _build_exploration_prompt(
        self, goal: str, page_state: str, history: str
    ) -> str:
        parts = [
            "你是一个UI自动化测试探索Agent。根据以下信息，决定下一步操作。",
            "",
            f"## 测试目标",
            goal,
            "",
            "## 当前页面状态",
            page_state,
        ]
        if history:
            parts.extend([
                "",
                "## 已执行的操作历史",
                history,
            ])

        parts.extend([
            "",
            "## 可用操作",
            "返回JSON，包含以下字段：",
            "- action: 操作类型 (click|fill|scroll|navigate|wait|screenshot|done)",
            "- selector: CSS选择器或文本 (click/fill 时必填，使用页面元素前的[index]索引号或CSS选择器)",
            "- value: 输入的值 (fill/navigate 时填写)",
            "- reasoning: 简短的操作理由",
            "- done: 是否已完成目标 (true/false)",
            "",
            "## 决策规则",
            "1. 如果页面有弹窗/对话框，优先处理弹窗",
            "2. 如果目标已完成或遇到阻塞，设置 done=true 并说明原因",
            "3. 如果找不到目标元素，尝试滚动页面",
            "4. 每个操作之前，考虑当前页面状态是否合理",
            "5. 如果页面出现错误信息，记录并设置 done=true",
            "",
            "## 示例输出",
            '{"action": "click", "selector": "[index=3]", "value": "", "reasoning": "点击登录按钮", "done": false}',
            '{"action": "fill", "selector": "[index=0]", "value": "admin", "reasoning": "输入用户名", "done": false}',
            '{"action": "done", "selector": "", "value": "", "reasoning": "目标已达成，页面显示欢迎信息", "done": true}',
            "",
            "现在请根据页面状态决定下一步操作，只返回JSON：",
        ])

        return "\n".join(parts)

    def _call_with_vision(
        self, prompt: str, screenshot_base64: str, system: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用 Vision 能力调用 LLM."""
        try:
            if isinstance(self.provider, VisionOpenAIProvider):
                result = self.provider.extract_json_from_vision(
                    prompt,
                    images_base64=[screenshot_base64],
                    system=system,
                    fallback={"action": "screenshot", "reasoning": "Vision调用失败，回退到截图确认", "done": True},
                )
                return result or {"action": "screenshot", "reasoning": "Vision理解失败", "done": True}
        except Exception:
            pass
        # 降级到纯文本
        return self._call_text_only(prompt, system)

    def _call_text_only(
        self, prompt: str, system: Optional[str] = None
    ) -> Dict[str, Any]:
        """纯文本调用 LLM."""
        try:
            resp = self.provider.complete(prompt, system=system)
            text = self.provider.extract_json(resp.content)
            return json.loads(text)
        except Exception:
            return {
                "action": "done",
                "reasoning": "LLM调用失败，终止探索",
                "done": True,
            }


def create_vision_llm(provider: LLMProvider) -> VisionLLM:
    """创建 VisionLLM 实例."""
    return VisionLLM(provider)
