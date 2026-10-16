"""Natural-language intent extraction through an OpenAI-compatible Chat API."""

from __future__ import annotations

import json
import os
from openai import OpenAI

from planner import Intent, safe_symbol

# 课程演示环境使用的 OpenAI-compatible ChatGPT 接口。
# 按项目要求直接写在调用脚本中，部署到公开仓库前请删除或更换密钥。
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = "https://api.apiyi.com/v1"
MODEL = "gpt-4.1"


def parse_intent_with_chatgpt(
    instruction: str,
    items: list[dict],
    targets: dict[str, tuple],
) -> Intent:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30.0, max_retries=1)
    item_names = [safe_symbol(x["name"]) for x in items]
    target_names = list(targets)
    prompt = f"""你是机械臂教学实验的任务解析器。
只从给定列表中选择一个物体和一个目标区域。
物体：{item_names}
目标区域：{target_names}
用户指令：{instruction}
只输出 JSON，例如 {{"item":"faulty_fuse_1","target":"recycle_area"}}。
禁止创造新的物体或区域。"""
    response = client.chat.completions.create(
        model=MODEL,
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
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30.0, max_retries=1)
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
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()

