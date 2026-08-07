# -*- coding: utf-8 -*-
"""语音识别（ASR）抽象基类."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ASRResult:
    text: str
    language: str = ""
    confidence: float = 0.0
    raw: Any = None


class ASRProvider(ABC):
    """语音识别 Provider 抽象基类."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def transcribe(self, audio_path: str, **kwargs) -> ASRResult:
        """将音频文件识别为文本.

        Args:
            audio_path: 音频文件本地路径
            **kwargs: 额外参数，如 language、prompt 等

        Returns:
            ASRResult 包含识别文本和元信息
        """
        pass

    def transcribe_bytes(self, audio_bytes: bytes, **kwargs) -> ASRResult:
        """将音频字节流识别为文本.

        默认实现写入临时文件后调用 transcribe，子类可覆盖以优化性能。
        """
        import tempfile
        from pathlib import Path

        suffix = kwargs.get("format", ".mp3")
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            return self.transcribe(tmp_path, **kwargs)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def transcribe_from_url(self, audio_url: str, **kwargs) -> ASRResult:
        """下载音频 URL 并识别为文本."""
        import requests

        # SSRF 防护：audio_url 可能来自外部输入（IM 语音消息、CLI --audio-url），
        # 若不限制可被用来访问内网元数据端点（如 169.254.169.254）或本地服务，
        # 并把响应内容通过 transcribe_bytes 转发到外部 ASR 厂商造成数据外泄。
        self._assert_safe_url(audio_url)

        resp = requests.get(audio_url, timeout=kwargs.get("timeout", 60), allow_redirects=False)
        # 禁止跳转：跳转目标可能指向内网地址，绕过上面的校验
        if resp.is_redirect or resp.is_permanent_redirect:
            raise ValueError(f"拒绝跟随重定向以避免 SSRF: {audio_url} -> {resp.headers.get('Location')}")
        resp.raise_for_status()
        return self.transcribe_bytes(resp.content, **kwargs)

    @staticmethod
    def _assert_safe_url(audio_url: str) -> None:
        from urllib.parse import urlparse

        parsed = urlparse(audio_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"仅允许 http/https 音频 URL，拒绝: {audio_url}")
        host = parsed.hostname or ""
        if not host:
            raise ValueError(f"音频 URL 缺少主机名: {audio_url}")
        import ipaddress

        # 解析主机为 IP（如果是域名则解析其 A 记录）
        candidates = []
        try:
            ip = ipaddress.ip_address(host)
            candidates.append(ip)
        except ValueError:
            # 域名：做一次解析，校验所有返回地址
            import socket

            try:
                infos = socket.getaddrinfo(host, None)
            except socket.gaierror:
                raise ValueError(f"无法解析音频 URL 主机名: {host}")
            for info in infos:
                try:
                    candidates.append(ipaddress.ip_address(info[4][0]))
                except (ValueError, IndexError):
                    continue

        for ip in candidates:
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise ValueError(
                    f"拒绝访问内网/保留地址的音频 URL 以防止 SSRF: {host} ({ip})"
                )
