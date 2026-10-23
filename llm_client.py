"""Natural-language intent extraction through an OpenAI-compatible Chat API."""

from __future__ import annotations

import json
import os
from openai import OpenAI

from planner import Intent, safe_symbol

DEFAULT_BASE_URL = "https://api.apiyi.com/v1"
DEFAULT_MODEL = "gpt-4.1"


def _setting(name: str, default: str = "") -> str:
    """Read Streamlit Cloud secrets first, then local environment variables."""
    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value:
            return str(value).strip()
    except Exception:
        # No secrets file is expected during local offline tests.
        pass
    return os.getenv(name, default).strip()


def _client() -> OpenAI:
    api_key = _setting("OPENAI_API_KEY")
    base_url = _setting("OPENAI_BASE_URL", DEFAULT_BASE_URL)
    if not api_key:
        raise RuntimeError(
            "服务器尚未配置大模型密钥。请在 Streamlit Cloud 的 App settings → Secrets "
            "中设置 OPENAI_API_KEY，或在本地设置同名环境变量。"
        )
    return OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=1)


def _model() -> str:
    return _setting("OPENAI_MODEL", DEFAULT_MODEL)


def parse_intent_with_chatgpt(
    instruction: str,
    items: list[dict],
    targets: dict[str, tuple],
) -> Intent:
    client = _client()
    item_names = [safe_symbol(x["name"]) for x in items]
    target_names = list(targets)
    prompt = f"""你是双臂机器人教学实验的任务解析器。
只从给定列表中选择一个物体和一个目标区域。
物体：{item_names}
目标区域：{target_names}
用户指令：{instruction}
只输出 JSON，例如 {{"item":"faulty_fuse_1","target":"recycle_area"}}。
禁止创造新的物体或区域。"""
    response = client.chat.completions.create(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(response.choices[0].message.content)
    item = safe_symbol(str(data.get("item", "")))
    target = safe_symbol(str(data.get("target", "")))
    if item not in item_names:
        raise ValueError(f"大模型返回了不存在的物体：{item}")
    if target not in targets:
        raise ValueError(f"大模型返回了不存在的区域：{target}")
    return Intent(item, target)


def generate_learning_hint(problem: str, items: list[dict], targets: list[str], level: str) -> str:
    """Generate short, bounded teaching advice for editing the current PDDL."""
    client = _client()
    prompt = f"""你是本科机器人课程助教。根据下面的 PDDL problem 给学生一段中文学习提示。
难度：{level}
允许的物体：{[x['name'] for x in items]}
允许的目标区域：{targets}
PDDL：
{problem}

要求：
1. 指出学生可以修改的 1～2 个具体参数（物体名、目标区域或初始区域）；
2. 说明修改后预计会改变什么规划或轨迹结果；
3. 不建议未定义的动作、谓词或对象；
4. 最多 120 个汉字；
5. 只输出提示正文。"""
    response = client.chat.completions.create(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def generate_deep_explanation(
    topic: str,
    context: str,
    question: str = "",
) -> str:
    """Generate renderer-safe Markdown for a course-scoped visual explanation."""
    client = _client()
    prompt = f"""你是“强电检修双6DOF机械臂虚拟仿真实验”的本科课程助教。
主题：{topic}
学生问题：{question or '请系统解读当前内容'}
实验上下文：
{context}

边界：
1. 只解释本实验的双臂PDDL、任务分配、左右6DOF、路点、关节角、轨迹、MuJoCo和上述强电检修对象。
2. 若问题与实验无关，只回答“该问题不在本实验讲解范围内”，并给出一个可提问的实验示例。
3. 不提供真实带电检修步骤、安全许可或设备控制指令。
4. 输出结构化 Markdown，不要输出 HTML、SVG、外部链接或三反引号代码块。
5. 必须包含：任务结论、关键关系、参数因果、可修改项、风险/失败条件、学生思考题。
6. 使用简洁中文，保留必要的 PDDL 符号和参数值，不超过 900 中文字。
"""
    response = client.chat.completions.create(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.25,
    )
    return response.choices[0].message.content.strip()

