# -*- coding: utf-8 -*-
"""飞书 Lark Skill 包装层.

优先使用 trae-remote-official:lark:lark-im skill 发送消息；
当 skill 不可用时，提供本地 OpenAPI 兜底实现。
"""

import json
import os
from typing import Any, Dict

import requests


def _get_lark_credentials() -> Dict[str, str]:
    """从环境变量或配置文件读取飞书凭证."""
    return {
        "app_id": os.environ.get("LARK_APP_ID", ""),
        "app_secret": os.environ.get("LARK_APP_SECRET", ""),
    }


def _get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取飞书 tenant access token."""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(
        url,
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 tenant_token 失败: {data}")
    return data["tenant_access_token"]


def send_lark_text(receiver: str, content: str, **kwargs) -> bool:
    """发送飞书文本消息.

    Args:
        receiver: 接收者 open_id 或 chat_id
        content: 消息内容
    """
    try:
        # 优先尝试调用 lark-im skill（需用户授权）
        from trae_remote_official.lark import lark_im

        return lark_im.send_text(receiver, content, **kwargs)
    except Exception:
        pass

    # 兜底：使用飞书 OpenAPI 直接发送
    creds = _get_lark_credentials()
    app_id = kwargs.get("app_id") or creds["app_id"]
    app_secret = kwargs.get("app_secret") or creds["app_secret"]
    if not app_id or not app_secret:
        raise RuntimeError("缺少飞书 app_id / app_secret")

    token = _get_tenant_token(app_id, app_secret)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    receive_id_type = kwargs.get("receive_id_type", "open_id")
    if receiver.startswith("oc_"):
        receive_id_type = "chat_id"

    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": receive_id_type}
    body = {
        "receive_id": receiver,
        "msg_type": "text",
        "content": json.dumps({"text": content}, ensure_ascii=False),
    }
    resp = requests.post(url, params=params, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"发送飞书消息失败: {data}")
    return True


def send_lark_file(receiver: str, file_path: str, **kwargs) -> bool:
    """发送飞书文件消息."""
    try:
        from trae_remote_official.lark import lark_im

        return lark_im.send_file(receiver, file_path, **kwargs)
    except Exception:
        pass

    creds = _get_lark_credentials()
    app_id = kwargs.get("app_id") or creds["app_id"]
    app_secret = kwargs.get("app_secret") or creds["app_secret"]
    if not app_id or not app_secret:
        raise RuntimeError("缺少飞书 app_id / app_secret")

    token = _get_tenant_token(app_id, app_secret)
    headers = {"Authorization": f"Bearer {token}"}

    receive_id_type = kwargs.get("receive_id_type", "open_id")
    if receiver.startswith("oc_"):
        receive_id_type = "chat_id"

    # 1. 上传文件
    upload_url = "https://open.feishu.cn/open-apis/im/v1/files"
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        data = {"file_type": kwargs.get("file_type", "stream"), "file_name": os.path.basename(file_path)}
        resp = requests.post(upload_url, headers=headers, files=files, data=data, timeout=60)
    resp.raise_for_status()
    upload_data = resp.json()
    if upload_data.get("code") != 0:
        raise RuntimeError(f"上传飞书文件失败: {upload_data}")
    file_key = upload_data["data"]["file_key"]

    # 2. 发送文件消息
    send_url = "https://open.feishu.cn/open-apis/im/v1/messages"
    params = {"receive_id_type": receive_id_type}
    body = {
        "receive_id": receiver,
        "msg_type": "file",
        "content": json.dumps({"file_key": file_key}, ensure_ascii=False),
    }
    resp = requests.post(send_url, params=params, headers={**headers, "Content-Type": "application/json"}, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"发送飞书文件消息失败: {data}")
    return True
