# -*- coding: utf-8 -*-
"""回归测试：ASR transcribe_from_url 的 SSRF 防护.

旧实现对 audio_url 不做任何限制，可被用来访问内网元数据端点
(如 169.254.169.254) 或本地服务，并把响应内容转发给外部 ASR 厂商。
"""
from unittest.mock import patch

import pytest

from automation.core.voice.base import ASRProvider


class TestAssertSafeUrl:
    def _resolve_to(self, ip: str):
        """构造一个 getaddrinfo 假返回，把任意域名解析到指定 IP."""
        return lambda host, *args, **kwargs: [(None, None, None, None, (ip, 0))]

    def test_rejects_link_local_metadata_endpoint(self):
        # AWS / GCP / Azure 元数据端点
        with pytest.raises(ValueError, match="SSRF"):
            ASRProvider._assert_safe_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_loopback_ipv4(self):
        with pytest.raises(ValueError):
            ASRProvider._assert_safe_url("http://127.0.0.1:8000/admin")

    def test_rejects_loopback_ipv6(self):
        with pytest.raises(ValueError):
            ASRProvider._assert_safe_url("http://[::1]:8000/admin")

    def test_rejects_private_rfc1918(self):
        for ip in ("10.0.0.1", "192.168.1.1", "172.16.0.1"):
            with pytest.raises(ValueError, match="SSRF"):
                ASRProvider._assert_safe_url(f"http://{ip}/x")

    def test_rejects_non_http_scheme(self):
        with pytest.raises(ValueError, match="http"):
            ASRProvider._assert_safe_url("file:///etc/passwd")
        with pytest.raises(ValueError, match="http"):
            ASRProvider._assert_safe_url("ftp://example.com/x")

    def test_rejects_domain_resolving_to_private_ip(self):
        # 即使 URL 看似公网域名，若 DNS 解析到内网地址也应拒绝
        with patch("socket.getaddrinfo", side_effect=self._resolve_to("10.0.0.1")):
            with pytest.raises(ValueError, match="SSRF"):
                ASRProvider._assert_safe_url("http://internal-proxy.evil/audio.mp3")

    def test_accepts_public_domain(self):
        with patch("socket.getaddrinfo", side_effect=self._resolve_to("93.184.216.34")):
            # 不应抛异常
            ASRProvider._assert_safe_url("http://example.com/audio.mp3")

    def test_accepts_public_ip_literal(self):
        # 不应抛异常
        ASRProvider._assert_safe_url("http://93.184.216.34/audio.mp3")

    def test_rejects_missing_host(self):
        with pytest.raises(ValueError):
            ASRProvider._assert_safe_url("http:///audio.mp3")


class TestTranscribeFromUrlRejectsSsrf:
    """端到端：transcribe_from_url 在拉取前就拒绝内网 URL，不会发起 requests.get."""

    def test_does_not_fetch_internal_url(self):
        # 用一个可实例化的最小子类
        class _DummyASR(ASRProvider):
            def transcribe(self, audio_path, **kwargs):
                return None  # 不会被调用

        asr = _DummyASR({})

        with patch("requests.get") as mock_get:
            with pytest.raises(ValueError, match="SSRF"):
                asr.transcribe_from_url("http://169.254.169.254/latest/meta-data/")
        mock_get.assert_not_called(), "内网 URL 应在校验阶段被拒绝，不应发起 HTTP 请求"
