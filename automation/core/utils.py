# -*- coding: utf-8 -*-
"""框架通用工具函数：统计、上下文压缩、模块提取等."""

import json
import re
from typing import Any, Dict, List, Optional


# ============= 统计工具 =============

def count_by(items: List[Dict], key: str) -> Dict[str, int]:
    """按指定字段统计列表中各值出现的次数."""
    counts: Dict[str, int] = {}
    for item in items:
        value = item.get(key, "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def calculate_pass_rate(results: List[Dict], passed_status: str = "passed") -> float:
    """计算通过率."""
    total = len(results)
    if total == 0:
        return 0.0
    passed = sum(1 for r in results if r.get("status") == passed_status)
    return round(passed / total * 100, 2)


def calculate_summary(results: List[Dict], statuses: List[str]) -> Dict[str, int]:
    """按多个状态统计结果数量."""
    return {status: sum(1 for r in results if r.get("status") == status) for status in statuses}


# ============= 上下文压缩工具 =============

def estimate_tokens(text: str) -> int:
    """粗略估算文本 token 数量（按中文字符 + 英文单词）."""
    if not text:
        return 0
    # 中文字符按 1 token 估算，英文按空白分词
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    english = len(re.findall(r"[a-zA-Z]+", text))
    others = len(re.findall(r"[0-9_]+", text))
    return chinese + english + others


def truncate_text(text: str, max_tokens: int, suffix: str = "\n...[已截断]") -> str:
    """按估算 token 数截断文本."""
    if estimate_tokens(text) <= max_tokens:
        return text
    tokens = 0
    end = 0
    for i, char in enumerate(text):
        if re.match(r"[\u4e00-\u9fff]", char):
            tokens += 1
        elif char.isalpha():
            # 简单处理连续字母为一个 token
            if i == 0 or not text[i - 1].isalpha():
                tokens += 1
        elif char.isdigit() or char == "_":
            if i == 0 or not (text[i - 1].isdigit() or text[i - 1] == "_"):
                tokens += 1
        if tokens > max_tokens:
            end = i
            break
    return text[:end] + suffix


def truncate_list(items: List[Dict], max_tokens: int, keep_fields: Optional[List[str]] = None) -> List[Dict]:
    """截断列表长度以控制 token 预算，可选只保留关键字段."""
    if not items:
        return []
    if keep_fields:
        items = [{k: item.get(k) for k in keep_fields if k in item} for item in items]
    budget = max_tokens
    result = []
    for item in items:
        text = json.dumps(item, ensure_ascii=False)
        cost = estimate_tokens(text)
        if cost > budget and result:
            break
        result.append(item)
        budget -= cost
    return result


def compact_json(data: Any, max_tokens: int = 4000) -> str:
    """将数据压缩为 JSON 字符串并控制长度."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if estimate_tokens(text) <= max_tokens:
        return text
    return truncate_text(text, max_tokens)


# ============= 模块/路径提取工具 =============

def extract_module_from_path(path: str, default: str = "common") -> str:
    """从 API 路径中提取模块名，例如 /api/users/1 -> users."""
    path = path.strip()
    if not path or path == "/":
        return default
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] in ("api", "v1", "v2", "v3"):
        return parts[1]
    if len(parts) >= 1:
        return parts[0]
    return default


def normalize_id(prefix: str, index: int) -> str:
    """生成统一格式的 ID."""
    return f"{prefix}-{index + 1:03d}"
