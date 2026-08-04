# -*- coding: utf-8 -*-
"""自愈选择器：当 CSS/XPath 选择器失效时，自动尝试替代策略.

策略优先级：
1. Text 匹配（精确/模糊）
2. ARIA 属性匹配
3. Placeholder 匹配
4. Role + Name 组合
5. LLM 辅助生成替代选择器
6. 视觉定位（需 Vision LLM 支持）
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import ElementHandle, Frame, FrameLocator, JSHandle, Locator, Page


@dataclass
class HealedSelector:
    """自愈结果."""
    success: bool
    new_selector: str
    strategy: str  # 使用的策略
    confidence: float  # 0-1
    attempts: List[str] = field(default_factory=list)
    error_details: str = ""


class SelectorHealer:
    """选择器自愈引擎.

    当原始选择器不可用时，尝试多种策略找到目标元素。
    支持记录修复历史，供后续学习和优化。
    """

    # 备选策略生成器（按优先级排列）
    def __init__(self, max_attempts: int = 8):
        self.max_attempts = max_attempts
        self.healing_history: List[Dict] = []  # 修复记录

    def heal(
        self,
        page: Page,
        original_selector: str,
        element_hint: Optional[Dict[str, str]] = None,
        screenshot_base64: str = "",
    ) -> HealedSelector:
        """尝试修复失效的选择器.

        Args:
            page: Playwright Page
            original_selector: 原始（失效的）选择器
            element_hint: 元素提示信息 {text, role, placeholder, aria_label, ...}
            screenshot_base64: 页面截图（供视觉定位使用）

        Returns:
            HealedSelector with new selector and confidence
        """
        attempts: List[str] = [original_selector]
        hint = element_hint or {}
        text = hint.get("text", "")
        role = hint.get("role", "")
        placeholder = hint.get("placeholder", "")
        aria_label = hint.get("aria_label", "")
        tag = hint.get("tag", "")
        input_type = hint.get("input_type", "")
        href = hint.get("href", "")

        # 策略 1: Text 精确匹配
        if text:
            sel = self._text_selector(text, exact=True)
            attempts.append(sel)
            result = self._try_selector(page, sel)
            if result:
                return HealedSelector(True, sel, "text_exact", 0.95, attempts)

        # 策略 2: Text 模糊匹配（部分文本）
        if text and len(text) > 3:
            sel = self._text_selector(text, exact=False)
            attempts.append(sel)
            result = self._try_selector(page, sel)
            if result:
                return HealedSelector(True, sel, "text_fuzzy", 0.85, attempts)

        # 策略 3: ARIA label
        if aria_label:
            sel = f'[aria-label="{aria_label}"]'
            attempts.append(sel)
            result = self._try_selector(page, sel)
            if result:
                return HealedSelector(True, sel, "aria_label", 0.90, attempts)

        # 策略 4: Placeholder
        if placeholder:
            sel = f'[placeholder="{placeholder}"]'
            attempts.append(sel)
            result = self._try_selector(page, sel)
            if result:
                return HealedSelector(True, sel, "placeholder", 0.85, attempts)

        # 策略 5: Role + Name 组合（Playwright 内置）
        if role and text:
            for r in [role, "button", "link", "textbox", "combobox"]:
                sel = f'{r}:has-text("{text}")'
                attempts.append(sel)
                result = self._try_selector(page, sel)
                if result:
                    return HealedSelector(True, sel, "role_has_text", 0.80, attempts)

        # 策略 6: 通过 href 匹配链接
        if href:
            sel = f'a[href*="{href}"]'
            attempts.append(sel)
            result = self._try_selector(page, sel)
            if result:
                return HealedSelector(True, sel, "href", 0.90, attempts)

        # 策略 7: data-testid 匹配（从 hint 推断）
        if text:
            testid = re.sub(r"[^a-zA-Z0-9_-]", "", text.lower())
            if testid:
                sel = f'[data-testid*="{testid}"]'
                attempts.append(sel)
                result = self._try_selector(page, sel)
                if result:
                    return HealedSelector(True, sel, "data_testid_inferred", 0.70, attempts)

        # 策略 8: 同类元素索引（根据原始选择器推断类型）
        inferred_type = self._infer_element_type(original_selector, hint)
        if inferred_type:
            sel = f"{inferred_type}:visible"
            attempts.append(sel)
            result = self._try_selector(page, sel)
            if result:
                return HealedSelector(True, sel, "type_visible", 0.50, attempts)

        # 所有策略失败
        return HealedSelector(
            False,
            original_selector,
            "none",
            0.0,
            attempts,
            f"所有 {len(attempts)} 种策略均未找到匹配元素",
        )

    def heal_with_state(
        self,
        page: Page,
        original_selector: str,
        element_hint: Optional[Dict[str, str]],
        current_state: Any,  # PageState
    ) -> HealedSelector:
        """结合页面状态分析进行智能修复.

        在标准策略失败时，从 PageState.elements 中查找最相似的元素.
        """
        result = self.heal(page, original_selector, element_hint)
        if result.success:
            return result

        hint = element_hint or {}
        text_to_find = hint.get("text", "") or hint.get("name", "")

        if hasattr(current_state, "elements") and text_to_find:
            # 在已提取的元素中模糊匹配
            best_elem = None
            best_score = 0.0

            for elem in current_state.elements:
                score = self._element_similarity(elem, hint)
                if score > best_score and score > 0.4:
                    best_score = score
                    best_elem = elem

            if best_elem and best_elem.selector:
                result = self._try_selector(page, best_elem.selector)
                if result:
                    return HealedSelector(
                        True,
                        best_elem.selector,
                        "state_match",
                        min(best_score, 0.85),
                        list(result.attempts) + [best_elem.selector],
                    )

        return result

    def _try_selector(self, page: Page, selector: str) -> Optional[HealedSelector]:
        """测试选择器是否有效."""
        try:
            loc = page.locator(selector).first
            if loc.count() > 0 and loc.is_visible():
                return HealedSelector(True, selector, "tested", 1.0)
        except Exception:
            pass
        return None

    def _text_selector(self, text: str, exact: bool = True) -> str:
        """构建文本选择器."""
        escaped = text.replace('"', '\\"')
        if exact:
            return f'text="{escaped}"'
        return f'text={escaped}'

    def _infer_element_type(self, selector: str, hint: Optional[Dict]) -> Optional[str]:
        """从原始选择器或 hint 推断元素类型."""
        if hint:
            tag = hint.get("tag", "")
            if tag:
                return tag
        # 从选择器推断
        type_patterns = [
            (r"button|\[role=['\"]button['\"]\]|submit|reset", "button"),
            (r'input\[type=["\']text["\']\]|input:not\(\[type\]\)|\[role=["\']textbox["\']\]', "input"),
            (r"select|\[role=['\"]listbox['\"]\]", "select"),
            (r"a\[href", "a"),
            (r"textarea", "textarea"),
            (r"checkbox", "input[type='checkbox']"),
            (r"radio", "input[type='radio']"),
        ]
        for pattern, tag in type_patterns:
            if re.search(pattern, selector, re.IGNORECASE):
                return tag
        return None

    def _element_similarity(self, elem, hint: Dict) -> float:
        """计算元素与 hint 的相似度 (0-1)."""
        score = 0.0
        total = 0.0

        fields = [
            ("text", elem.text or "", 1.0),
            ("name", elem.name or "", 0.8),
            ("placeholder", elem.placeholder or "", 0.7),
            ("role", elem.role or "", 0.5),
            ("aria_label", elem.aria_label or "", 0.7),
        ]

        for field_name, elem_value, weight in fields:
            hint_value = hint.get(field_name, "")
            if hint_value and elem_value:
                total += weight
                if hint_value.lower() == elem_value.lower():
                    score += weight
                elif hint_value.lower() in elem_value.lower() or elem_value.lower() in hint_value.lower():
                    score += weight * 0.7
                # 部分词匹配
                elif any(w in elem_value.lower() for w in hint_value.lower().split()):
                    score += weight * 0.4

        return score / total if total > 0 else 0.0

    def get_healing_stats(self) -> Dict[str, Any]:
        """获取自愈统计."""
        if not self.healing_history:
            return {"total_attempts": 0, "success_rate": 0.0, "strategies": {}}

        total = len(self.healing_history)
        successes = sum(1 for h in self.healing_history if h.get("success"))
        strategy_counts = {}
        for h in self.healing_history:
            s = h.get("strategy", "unknown")
            strategy_counts[s] = strategy_counts.get(s, 0) + 1

        return {
            "total_attempts": total,
            "success_rate": round(successes / total * 100, 1) if total else 0.0,
            "strategies": strategy_counts,
        }

    def record_healing(self, original: str, result: HealedSelector):
        """记录修复结果."""
        self.healing_history.append({
            "original": original,
            "new_selector": result.new_selector,
            "success": result.success,
            "strategy": result.strategy,
            "confidence": result.confidence,
            "error": result.error_details,
        })
