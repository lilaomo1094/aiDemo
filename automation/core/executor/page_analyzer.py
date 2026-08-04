# -*- coding: utf-8 -*-
"""页面状态分析器：提取 DOM 结构、可交互元素、无障碍信息和截图.

为 LLM 决策提供结构化的页面描述，支持三种提取策略：
1. DOM 提取：解析 HTML 元素，提取按钮/输入框/链接/表单等
2. Accessibility Tree：利用 Playwright 无障碍快照获取语义化页面结构
3. 截图：获取页面截图(base64)，供支持 Vision 的 LLM 使用
"""

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import Page


# ──────────────── 交互元素权重配置 ────────────────
# 不同元素类型对 LLM 决策的重要性（用于数量超限时排序截断）
_ELEMENT_WEIGHT = {
    "button": 10,
    "link": 8,
    "textbox": 9,
    "searchbox": 9,
    "combobox": 8,
    "checkbox": 5,
    "radio": 5,
    "switch": 5,
    "option": 4,
    "tab": 7,
    "menuitem": 7,
    "heading": 3,
    "navigation": 6,
    "listitem": 3,
    "generic": 0,
    "text": 1,
    "image": 2,
    "form": 4,
    "dialog": 7,
    "alert": 10,
}


@dataclass
class InteractiveElement:
    """页面可交互元素."""
    role: str
    name: str = ""
    tag: str = ""
    selector: str = ""
    text: str = ""
    placeholder: str = ""
    value: str = ""
    href: str = ""
    input_type: str = ""
    aria_label: str = ""
    visible: bool = True
    disabled: bool = False
    checked: bool = False
    index: int = 0
    rect: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "role": self.role,
            "name": self.name,
            "tag": self.tag,
            "text": self.text,
            "placeholder": self.placeholder,
            "value": self.value,
            "href": self.href,
            "input_type": self.input_type,
            "visible": self.visible,
            "disabled": self.disabled,
            "checked": self.checked,
            "selector_preview": self.selector[:120] if self.selector else "",
        }

    def to_llm_desc(self) -> str:
        """生成供 LLM 理解的简短描述."""
        parts = [f"[{self.index}] {self.role}"]
        if self.name:
            parts.append(f'"{self.name}"')
        if self.tag:
            parts.append(f"<{self.tag}>")
        if self.text:
            parts.append(f"text={self.text[:40]}")
        if self.placeholder:
            parts.append(f"placeholder={self.placeholder[:30]}")
        if self.input_type:
            parts.append(f"type={self.input_type}")
        if self.href:
            parts.append(f"href={self.href[:60]}")
        if self.disabled:
            parts.append("(disabled)")
        if not self.visible:
            parts.append("(hidden)")
        return " | ".join(parts)


@dataclass
class PageState:
    """页面完整状态."""
    url: str = ""
    title: str = ""
    loaded: bool = False
    elements: List[InteractiveElement] = field(default_factory=list)
    form_groups: List[List[InteractiveElement]] = field(default_factory=list)
    navigation_items: List[InteractiveElement] = field(default_factory=list)
    dialogs: List[InteractiveElement] = field(default_factory=list)
    alerts: List[InteractiveElement] = field(default_factory=list)
    error_texts: List[str] = field(default_factory=list)
    screenshot_base64: str = ""
    total_elements: int = 0
    visible_elements: int = 0

    def to_llm_context(self, max_elements: int = 60) -> str:
        """生成紧凑的 LLM 上下文描述."""
        lines = [
            f"URL: {self.url}",
            f"Title: {self.title}",
        ]

        if self.alerts:
            lines.append("⚠ Alerts: " + "; ".join(self.alerts))

        if self.dialogs:
            lines.append("📦 Dialogs/Modals present: " + ", ".join(
                e.name or e.role for e in self.dialogs
            ))

        if self.error_texts:
            lines.append("❌ Error messages: " + "; ".join(self.error_texts))

        # 交互元素列表
        visible = [e for e in self.elements if e.visible]
        truncated = self._truncate_elements(visible, max_elements)

        lines.append(f"\nInteractable elements ({len(truncated)}/{self.visible_elements} shown):")
        for elem in truncated:
            lines.append(f"  {elem.to_llm_desc()}")

        if self.navigation_items:
            lines.append("\nNavigation:")
            lines.append("  " + " → ".join(e.name or e.text for e in self.navigation_items[:10]))

        if self.form_groups:
            lines.append(f"\nForms detected: {len(self.form_groups)}")

        return "\n".join(lines)

    def _truncate_elements(
        self, elements: List[InteractiveElement], max_count: int
    ) -> List[InteractiveElement]:
        """按权重排序后截断，优先保留高价值元素."""
        if len(elements) <= max_count:
            return elements
        sorted_elems = sorted(
            elements,
            key=lambda e: _ELEMENT_WEIGHT.get(e.role, 0),
            reverse=True,
        )
        return sorted_elems[:max_count]


class PageAnalyzer:
    """页面状态分析器.

    通过 Playwright Page 对象提取结构化页面信息，
    同时支持 DOM、Accessibility Tree 和截图三种数据源。
    """

    # ── DOM 扫描元素 ──
    SCAN_SELECTORS = [
        # 按钮类
        ("button, [role='button'], input[type='button'], input[type='submit'], input[type='reset']", "button"),
        # 链接
        ("a[href]", "link"),
        # 文本输入
        ("input[type='text'], input[type='email'], input[type='password'], "
         "input[type='number'], input[type='tel'], input[type='url'], "
         "input[type='search'], input:not([type]), textarea", "textbox"),
        # 选择类
        ("select", "combobox"),
        # 复选框/开关
        ("input[type='checkbox']", "checkbox"),
        # 单选框
        ("input[type='radio']", "radio"),
        # 导航
        ("nav a, nav button, [role='navigation'] a, [role='navigation'] button", "navigation"),
        # 标签页
        ("[role='tab']", "tab"),
        # 菜单项
        ("[role='menuitem']", "menuitem"),
        # 对话框
        ("[role='dialog'], .modal, .dialog", "dialog"),
    ]

    def __init__(self, max_elements_per_page: int = 200, extract_forms: bool = True):
        self.max_elements_per_page = max_elements_per_page
        self.extract_forms = extract_forms

    def analyze(self, page: Page, take_screenshot: bool = False) -> PageState:
        """分析页面当前状态.

        Args:
            page: Playwright Page 对象
            take_screenshot: 是否截取截图(base64)

        Returns:
            PageState: 页面状态结构化数据
        """
        state = PageState()

        try:
            state.url = page.url
            state.title = page.title()
            state.loaded = True
        except Exception:
            state.loaded = False
            return state

        # 1. DOM 元素提取
        state.elements = self._extract_elements(page)

        # 2. 无障碍快照（补充语义信息）
        try:
            self._enrich_with_accessibility(state, page)
        except Exception:
            pass  # accessibility 失败不阻塞

        # 3. 分组
        state.visible_elements = sum(1 for e in state.elements if e.visible)
        state.total_elements = len(state.elements)
        state.navigation_items = [e for e in state.elements if e.role == "navigation"]
        state.dialogs = [e for e in state.elements if e.role == "dialog"]
        state.alerts = self._extract_alerts(page)
        state.error_texts = self._extract_error_texts(page)

        if self.extract_forms:
            state.form_groups = self._group_forms(state.elements)

        # 4. 截图
        if take_screenshot:
            state.screenshot_base64 = self._take_screenshot(page)

        return state

    def _extract_elements(self, page: Page) -> List[InteractiveElement]:
        """从 DOM 提取所有可交互元素."""
        elements: List[InteractiveElement] = []
        seen_selectors: set = set()
        index = 0

        for selector, role in self.SCAN_SELECTORS:
            if index >= self.max_elements_per_page:
                break
            try:
                nodes = page.locator(selector)
                count = nodes.count()
                for i in range(min(count, self.max_elements_per_page - index)):
                    try:
                        elem = nodes.nth(i)
                        if not elem.is_visible():
                            continue

                        # 生成唯一选择器
                        elem_selector = self._build_best_selector(elem, page, i, selector)

                        # 去重
                        if elem_selector in seen_selectors:
                            continue
                        seen_selectors.add(elem_selector)

                        interactive = self._parse_element(elem, role, index, elem_selector)
                        elements.append(interactive)
                        index += 1
                    except Exception:
                        continue
            except Exception:
                continue

        return elements

    def _parse_element(
        self, elem, role: str, index: int, selector: str
    ) -> InteractiveElement:
        """从 Playwright Locator 解析出 InteractiveElement."""
        tag = ""
        text = ""
        placeholder = ""
        value = ""
        href = ""
        input_type = ""
        name = ""

        try:
            tag = elem.evaluate("el => el.tagName.toLowerCase()")
        except Exception:
            pass

        try:
            text = (elem.inner_text() or "").strip()
            name = text[:60]
        except Exception:
            pass

        try:
            placeholder = elem.get_attribute("placeholder") or ""
        except Exception:
            pass

        try:
            value = elem.get_attribute("value") or elem.input_value() or ""
        except Exception:
            pass

        try:
            href = elem.get_attribute("href") or ""
        except Exception:
            pass

        try:
            input_type = elem.get_attribute("type") or ""
        except Exception:
            pass

        # aria 属性
        aria_label = ""
        try:
            aria_label = elem.get_attribute("aria-label") or ""
        except Exception:
            pass

        if aria_label and not name:
            name = aria_label

        disabled = False
        try:
            disabled = elem.is_disabled()
        except Exception:
            pass

        checked = False
        try:
            checked = elem.is_checked()
        except Exception:
            pass

        visible = True
        try:
            visible = elem.is_visible()
        except Exception:
            pass

        # 根据 role/tag 优化名称
        if not name:
            if tag == "button":
                name = value or placeholder or "button"
            elif tag in ("input", "textarea"):
                name = placeholder or f"{input_type or 'text'} input"
            elif tag == "a":
                name = text or href or "link"

        return InteractiveElement(
            role=role,
            name=name,
            tag=tag,
            selector=selector,
            text=text,
            placeholder=placeholder,
            value=value,
            href=href,
            input_type=input_type,
            aria_label=aria_label,
            visible=visible,
            disabled=disabled,
            checked=checked,
            index=index,
        )

    def _build_best_selector(self, elem, page: Page, nth: int, fallback: str) -> str:
        """生成最优选择器，优先级: data-testid > id > aria-label > text > css."""
        try:
            testid = elem.get_attribute("data-testid")
            if testid:
                return f'[data-testid="{testid}"]'
        except Exception:
            pass

        try:
            elem_id = elem.get_attribute("id")
            if elem_id:
                return f"#{elem_id}"
        except Exception:
            pass

        try:
            aria_label = elem.get_attribute("aria-label")
            if aria_label:
                return f'[aria-label="{aria_label}"]'
        except Exception:
            pass

        return fallback

    def _enrich_with_accessibility(self, state: PageState, page: Page):
        """使用无障碍快照补充元素信息."""
        try:
            snapshot = page.accessibility.snapshot()
            if snapshot:
                self._walk_accessibility(snapshot, state.elements, 0)
        except Exception:
            pass

    def _walk_accessibility(self, node: Dict, elements: List[InteractiveElement], depth: int):
        """递归遍历无障碍树并补充到 elements."""
        if depth > 10:
            return
        role = node.get("role", "")
        name = node.get("name", "")
        if role and name:
            for elem in elements:
                if elem.name == name or (name and name in (elem.text or "")):
                    if not elem.role or elem.role == "generic":
                        elem.role = role
                    break

        for child in node.get("children", []):
            self._walk_accessibility(child, elements, depth + 1)

    def _extract_alerts(self, page: Page) -> List[str]:
        """提取页面中的 alert/toast 消息."""
        alerts = []
        alert_selectors = [
            "[role='alert']",
            ".alert",
            ".toast",
            ".message",
            ".notification",
            "[class*='error']",
            "[class*='warning']",
            "[class*='success']",
        ]
        for sel in alert_selectors:
            try:
                locator = page.locator(sel)
                count = locator.count()
                for i in range(min(count, 5)):
                    try:
                        text = locator.nth(i).inner_text()
                        if text.strip():
                            alerts.append(text.strip()[:120])
                    except Exception:
                        continue
            except Exception:
                continue
        return alerts[:5]

    def _extract_error_texts(self, page: Page) -> List[str]:
        """提取页面错误信息."""
        errors = []
        error_selectors = [
            ".error-message",
            ".field-error",
            ".form-error",
            "[class*='error']",
            ".invalid-feedback",
        ]
        for sel in error_selectors:
            try:
                locator = page.locator(sel)
                count = locator.count()
                for i in range(min(count, 5)):
                    try:
                        elem = locator.nth(i)
                        if elem.is_visible():
                            text = elem.inner_text()
                            if text.strip():
                                errors.append(text.strip()[:200])
                    except Exception:
                        continue
            except Exception:
                continue
        return errors[:10]

    def _group_forms(self, elements: List[InteractiveElement]) -> List[List[InteractiveElement]]:
        """将元素按表单分组."""
        groups = []
        current = []
        form_roles = {"textbox", "searchbox", "combobox", "checkbox", "radio", "button", "switch"}

        for elem in elements:
            if elem.role in form_roles:
                current.append(elem)
            else:
                if len(current) >= 2:
                    groups.append(current)
                    current = []
        if len(current) >= 2:
            groups.append(current)

        return groups

    def _take_screenshot(self, page: Page) -> str:
        """截取页面截图并返回 base64."""
        try:
            screenshot_bytes = page.screenshot(type="png", full_page=False)
            return base64.b64encode(screenshot_bytes).decode("utf-8")
        except Exception:
            return ""

    def diff(self, before: PageState, after: PageState) -> Dict[str, Any]:
        """对比两个页面状态，检测变化.

        Returns:
            包含新增/移除元素、文本变化、URL 变化的字典
        """
        before_urls = {e.selector for e in before.elements}
        after_urls = {e.selector for e in after.elements}

        added = [e.to_dict() for e in after.elements if e.selector not in before_urls]
        removed = [e.to_dict() for e in before.elements if e.selector not in after_urls]

        return {
            "url_changed": before.url != after.url,
            "url_before": before.url,
            "url_after": after.url,
            "title_changed": before.title != after.title,
            "elements_added": len(added),
            "elements_removed": len(removed),
            "added": added[:20],
            "removed": removed[:20],
            "new_alerts": [a for a in after.alerts if a not in before.alerts],
            "new_errors": [e for e in after.error_texts if e not in before.error_texts],
            "new_dialogs": [
                d.name for d in after.dialogs
                if not any(d.selector == bd.selector for bd in before.dialogs)
            ],
        }

    def find_element_by_text(
        self, elements: List[InteractiveElement], text: str, fuzzy: bool = True
    ) -> Optional[InteractiveElement]:
        """通过文本查找元素（支持模糊匹配）."""
        text_lower = text.lower()
        for elem in elements:
            if elem.text and text_lower in elem.text.lower():
                return elem
            if elem.name and text_lower in elem.name.lower():
                return elem
            if elem.placeholder and text_lower in elem.placeholder.lower():
                return elem
        if not fuzzy:
            return None
        # 宽松匹配：部分匹配
        for elem in elements:
            for field in [elem.text, elem.name, elem.placeholder, elem.value]:
                if field and any(t in field.lower() for t in text_lower.split()):
                    return elem
        return None
