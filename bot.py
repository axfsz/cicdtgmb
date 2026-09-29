#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ugtesta-tgmb
Telegram group build panel for Jenkins testa jobs.

Features:
- Inline button panel in Telegram group
- Shows who clicked the build button
- Sends trigger status to the group
- Uses Jenkins API token + crumb + cookie + buildWithParameters
- Job token rule: <job-name>-token
"""

import html
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
TG_ALLOWED_CHAT_ID = os.getenv("TG_ALLOWED_CHAT_ID", "-1003919548725").strip()

JENKINS_URL = os.getenv("JENKINS_URL", "https://ugjekins.ugmid888.com").rstrip("/")
JENKINS_USER = os.getenv("JENKINS_USER", "ugadmin").strip()
JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN", "").strip()

DEFAULT_BRANCH = os.getenv("DEFAULT_BRANCH", "main").strip()
DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE", "testa").strip()
DEFAULT_PUSH_LATEST = os.getenv("DEFAULT_PUSH_LATEST", "true").strip().lower()
DEFAULT_RUN_GO_TEST = os.getenv("DEFAULT_RUN_GO_TEST", "false").strip().lower()

ALLOWED_USER_IDS_RAW = os.getenv("ALLOWED_USER_IDS", "").strip()
ALLOWED_USER_IDS = {x.strip() for x in ALLOWED_USER_IDS_RAW.split(",") if x.strip()}

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_FILE = os.path.join(BASE_DIR, "jobs.json")

if not TG_BOT_TOKEN:
    logging.error("TG_BOT_TOKEN is required")
    sys.exit(1)

if not JENKINS_API_TOKEN:
    logging.error("JENKINS_API_TOKEN is required")
    sys.exit(1)

TG_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}"


@dataclass
class JobItem:
    name: str
    type: str
    service: str


def h(value: Any) -> str:
    return html.escape("-" if value is None else str(value), quote=False)


def load_jobs() -> List[JobItem]:
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    jobs = []
    for item in data.get("jobs", []):
        jobs.append(JobItem(
            name=item["name"],
            type=item.get("type", "unknown"),
            service=item.get("service", item["name"]),
        ))
    return jobs


JOBS = load_jobs()
JOB_MAP = {job.name: job for job in JOBS}


def tg_request(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{TG_API}/{method}"
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        data = resp.json()
    except Exception:
        data = {"ok": False, "raw": resp.text}
    if not resp.ok or not data.get("ok"):
        logging.error("Telegram API failed: method=%s status=%s response=%s", method, resp.status_code, data)
    return data


def send_message(chat_id: Any, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("sendMessage", payload)


def edit_message(chat_id: Any, message_id: Any, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_request("editMessageText", payload)


def answer_callback(callback_query_id: str, text: str = "已收到", show_alert: bool = False) -> None:
    tg_request("answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": show_alert,
    })


def user_display(user: Dict[str, Any]) -> str:
    user_id = user.get("id", "-")
    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    username = user.get("username")
    full_name = (first_name + " " + last_name).strip() or username or str(user_id)
    mention = f'<a href="tg://user?id={h(user_id)}">{h(full_name)}</a>'
    if username:
        return f"{mention} (@{h(username)})"
    return mention


def check_chat_allowed(chat_id: Any) -> bool:
    return str(chat_id) == str(TG_ALLOWED_CHAT_ID)


def check_user_allowed(user: Dict[str, Any]) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return str(user.get("id")) in ALLOWED_USER_IDS


def main_keyboard() -> Dict[str, Any]:
    rows = []
    # Category buttons
    rows.append([
        {"text": "RPC 服务", "callback_data": "cat:rpc"},
        {"text": "BFF 服务", "callback_data": "cat:bff"},
        {"text": "独立服务", "callback_data": "cat:standalone"},
    ])
    rows.append([
        {"text": "全部服务", "callback_data": "cat:all"},
        {"text": "帮助", "callback_data": "help"},
    ])
    return {"inline_keyboard": rows}


def jobs_keyboard(category: str = "all") -> Dict[str, Any]:
    jobs = JOBS if category == "all" else [j for j in JOBS if j.type == category]
    rows = []
    for job in jobs:
        rows.append([
            {"text": f"🚀 {job.name}", "callback_data": f"build:{job.name}"}
        ])
    rows.append([
        {"text": "返回主菜单", "callback_data": "menu"}
    ])
    return {"inline_keyboard": rows}


def menu_text() -> str:
    return (
        "<b>UG TestA Jenkins 构建面板</b>\n\n"
        "请选择要发布的服务。\n"
        "点击服务按钮后，机器人会在群内显示：\n"
        "1. 触发人\n"
        "2. 服务名\n"
        "3. Jenkins 触发状态\n"
        "4. 队列地址 / 构建地址\n\n"
        f"<b>默认分支:</b> <code>{h(DEFAULT_BRANCH)}</code>\n"
        f"<b>默认命名空间:</b> <code>{h(DEFAULT_NAMESPACE)}</code>\n"
        f"<b>Jenkins:</b> {h(JENKINS_URL)}"
    )


def help_text() -> str:
    return (
        "<b>命令说明</b>\n\n"
        "/start - 打开构建面板\n"
        "/menu - 打开构建面板\n"
        "/jobs - 查看服务列表\n"
        "/status - 查看机器人状态\n\n"
        "<b>触发规则</b>\n"
        "每个 Jenkins Job 的远程构建身份令牌规则为：\n"
        "<code>job名-token</code>\n\n"
        "例如：\n"
        "<code>activity-rpc-testa-token</code>"
    )


def jobs_text() -> str:
    lines = ["<b>TestA 服务列表</b>", ""]
    for job in JOBS:
        lines.append(f"• <code>{h(job.name)}</code> [{h(job.type)}]")
    return "\n".join(lines)


def get_jenkins_crumb(session: requests.Session) -> Tuple[str, str]:
    url = f"{JENKINS_URL}/crumbIssuer/api/json"
    resp = session.get(url, auth=(JENKINS_USER, JENKINS_API_TOKEN), timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    return data["crumbRequestField"], data["crumb"]


def trigger_jenkins(job_name: str) -> Dict[str, Any]:
    session = requests.Session()
    result: Dict[str, Any] = {
        "job_name": job_name,
        "ok": False,
        "http_status": None,
        "queue_url": None,
        "build_url": None,
        "error": None,
    }
    try:
        crumb_field, crumb_value = get_jenkins_crumb(session)
        job_token = f"{job_name}-token"
        encoded_job = quote(job_name, safe="")
        url = f"{JENKINS_URL}/job/{encoded_job}/buildWithParameters?token={quote(job_token, safe='')}"
        params = {
            "BRANCH_NAME": DEFAULT_BRANCH,
            "K8S_NAMESPACE": DEFAULT_NAMESPACE,
            "PUSH_LATEST": DEFAULT_PUSH_LATEST,
            "RUN_GO_TEST": DEFAULT_RUN_GO_TEST,
        }
        headers = {crumb_field: crumb_value}
        resp = session.post(
            url,
            auth=(JENKINS_USER, JENKINS_API_TOKEN),
            headers=headers,
            data=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        result["http_status"] = resp.status_code
        result["queue_url"] = resp.headers.get("Location")
        if resp.status_code in (200, 201, 202, 302):
            result["ok"] = True
            # Try to find build url from queue item.
            if result["queue_url"]:
                result["build_url"] = poll_queue_for_build(session, result["queue_url"])
        else:
            result["error"] = resp.text[:1000]
    except Exception as e:
        logging.exception("trigger jenkins failed: %s", job_name)
        result["error"] = str(e)
    return result


def poll_queue_for_build(session: requests.Session, queue_url: str) -> Optional[str]:
    api_url = queue_url.rstrip("/") + "/api/json"
    for _ in range(10):
        try:
            resp = session.get(api_url, auth=(JENKINS_USER, JENKINS_API_TOKEN), timeout=REQUEST_TIMEOUT_SECONDS)
            if resp.ok:
                data = resp.json()
                executable = data.get("executable")
                if executable and executable.get("url"):
                    return executable.get("url")
        except Exception as e:
            logging.warning("poll queue failed: %s", e)
        time.sleep(POLL_INTERVAL_SECONDS)
    return None


def build_start_message(job: JobItem, user: Dict[str, Any]) -> str:
    return (
        "🚀 <b>Jenkins 构建触发中</b>\n\n"
        f"<b>触发人:</b> {user_display(user)}\n"
        f"<b>服务:</b> <code>{h(job.name)}</code>\n"
        f"<b>类型:</b> <code>{h(job.type)}</code>\n"
        f"<b>分支:</b> <code>{h(DEFAULT_BRANCH)}</code>\n"
        f"<b>命名空间:</b> <code>{h(DEFAULT_NAMESPACE)}</code>\n"
        "<b>触发状态:</b> ⏳ 请求 Jenkins 中"
    )


def build_result_message(job: JobItem, user: Dict[str, Any], result: Dict[str, Any]) -> str:
    if result.get("ok"):
        status_line = "✅ 已成功加入 Jenkins 构建队列"
    else:
        status_line = "❌ Jenkins 触发失败"
    lines = [
        "📣 <b>Jenkins 构建触发结果</b>",
        "",
        f"<b>触发人:</b> {user_display(user)}",
        f"<b>服务:</b> <code>{h(job.name)}</code>",
        f"<b>类型:</b> <code>{h(job.type)}</code>",
        f"<b>分支:</b> <code>{h(DEFAULT_BRANCH)}</code>",
        f"<b>命名空间:</b> <code>{h(DEFAULT_NAMESPACE)}</code>",
        f"<b>触发状态:</b> {status_line}",
        f"<b>HTTP状态:</b> <code>{h(result.get('http_status'))}</code>",
    ]
    if result.get("queue_url"):
        lines.append(f"<b>队列地址:</b> {h(result.get('queue_url'))}")
    if result.get("build_url"):
        lines.append(f"<b>构建地址:</b> {h(result.get('build_url'))}")
    if result.get("error"):
        lines.append(f"<b>错误:</b> <code>{h(result.get('error'))}</code>")
    return "\n".join(lines)


def handle_command(message: Dict[str, Any]) -> None:
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    user = message.get("from", {})

    if not check_chat_allowed(chat_id):
        send_message(chat_id, "❌ 当前群未授权使用此机器人。")
        return

    if text.startswith("/start") or text.startswith("/menu"):
        send_message(chat_id, menu_text(), main_keyboard())
    elif text.startswith("/jobs"):
        send_message(chat_id, jobs_text())
    elif text.startswith("/status"):
        send_message(chat_id, (
            "✅ <b>ugtesta-tgmb 运行正常</b>\n"
            f"<b>授权群:</b> <code>{h(TG_ALLOWED_CHAT_ID)}</code>\n"
            f"<b>Jenkins:</b> {h(JENKINS_URL)}\n"
            f"<b>Job数量:</b> <code>{len(JOBS)}</code>"
        ))
    elif text.startswith("/help"):
        send_message(chat_id, help_text())


def handle_callback(callback: Dict[str, Any]) -> None:
    callback_id = callback.get("id")
    user = callback.get("from", {})
    message = callback.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    data = callback.get("data", "")

    if not check_chat_allowed(chat_id):
        answer_callback(callback_id, "当前群未授权", True)
        return

    if not check_user_allowed(user):
        answer_callback(callback_id, "你没有触发构建权限", True)
        send_message(chat_id, f"⛔ {user_display(user)} 尝试触发构建，但不在授权用户列表中。")
        return

    if data == "menu":
        answer_callback(callback_id, "返回主菜单")
        edit_message(chat_id, message_id, menu_text(), main_keyboard())
        return

    if data == "help":
        answer_callback(callback_id, "帮助")
        edit_message(chat_id, message_id, help_text(), main_keyboard())
        return

    if data.startswith("cat:"):
        category = data.split(":", 1)[1]
        answer_callback(callback_id, "请选择服务")
        title = "全部服务" if category == "all" else category.upper()
        edit_message(chat_id, message_id, f"<b>{h(title)} 构建列表</b>\n\n点击服务按钮立即触发 Jenkins 构建。", jobs_keyboard(category))
        return

    if data.startswith("build:"):
        job_name = data.split(":", 1)[1]
        job = JOB_MAP.get(job_name)
        if not job:
            answer_callback(callback_id, "Job 不存在", True)
            return

        answer_callback(callback_id, f"正在触发 {job_name}")
        send_message(chat_id, build_start_message(job, user))
        result = trigger_jenkins(job_name)
        send_message(chat_id, build_result_message(job, user, result))
        return

    answer_callback(callback_id, "未知操作", True)


def get_updates(offset: Optional[int]) -> Dict[str, Any]:
    params = {
        "timeout": 30,
        "allowed_updates": ["message", "callback_query"],
    }
    if offset is not None:
        params["offset"] = offset
    resp = requests.post(f"{TG_API}/getUpdates", json=params, timeout=40)
    return resp.json()


def run() -> None:
    logging.info("ugtesta-tgmb started")
    logging.info("Allowed chat id: %s", TG_ALLOWED_CHAT_ID)
    logging.info("Jenkins URL: %s", JENKINS_URL)
    logging.info("Loaded jobs: %s", len(JOBS))

    # Send boot message to authorized group.
    send_message(TG_ALLOWED_CHAT_ID, (
        "🤖 <b>ugtesta-tgmb 已启动</b>\n"
        "输入 /menu 打开 Jenkins 构建面板。"
    ))

    offset: Optional[int] = None
    while True:
        try:
            data = get_updates(offset)
            if not data.get("ok"):
                logging.warning("getUpdates failed: %s", data)
                time.sleep(3)
                continue
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    handle_command(update["message"])
                elif "callback_query" in update:
                    handle_callback(update["callback_query"])
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.exception("main loop error: %s", e)
            time.sleep(3)


if __name__ == "__main__":
    run()
