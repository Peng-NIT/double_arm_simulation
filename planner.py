"""Small, transparent PDDL teaching layer for the Streamlit experiment."""

from __future__ import annotations

from dataclasses import dataclass
import re


DOMAIN_PDDL = """(define (domain power-maintenance)
  (:requirements :strips :typing)
  (:types component location)
  (:predicates
    (at ?x - component ?p - location)
    (hand-empty)
    (holding ?x - component))

  (:action pick
    :parameters (?x - component ?p - location)
    :precondition (and (at ?x ?p) (hand-empty))
    :effect (and (holding ?x) (not (at ?x ?p)) (not (hand-empty))))

  (:action place
    :parameters (?x - component ?p - location)
    :precondition (holding ?x)
    :effect (and (at ?x ?p) (hand-empty) (not (holding ?x))))

  (:action return-home
    :parameters ()
    :precondition (hand-empty)
    :effect (hand-empty)))
"""


@dataclass(frozen=True)
class Intent:
    item: str
    target: str


def safe_symbol(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_\-]", "_", value.strip().lower())
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "item"


def build_problem(items: list[dict], intent: Intent) -> str:
    names = [safe_symbol(item["name"]) for item in items]
    locations = sorted({safe_symbol(item["location"]) for item in items} | {intent.target, "home"})
    objects = " ".join(names) or "placeholder"
    locs = " ".join(locations)
    init = "\n    ".join(
        f"(at {safe_symbol(item['name'])} {safe_symbol(item['location'])})" for item in items
    )
    return f"""(define (problem maintenance-task)
  (:domain power-maintenance)
  (:objects
    {objects} - component
    {locs} - location)
  (:init
    (hand-empty)
    {init})
  (:goal (at {intent.item} {intent.target})))
"""


def make_plan(items: list[dict], intent: Intent) -> list[dict]:
    """Solve the deliberately small pick/place domain without an external binary."""
    item = next((x for x in items if safe_symbol(x["name"]) == intent.item), None)
    if item is None:
        raise ValueError(f"场景中不存在物体：{intent.item}")
    source = safe_symbol(item["location"])
    if source == intent.target:
        return [{"action": "return-home", "args": []}]
    return [
        {"action": "pick", "args": [intent.item, source]},
        {"action": "place", "args": [intent.item, intent.target]},
        {"action": "return-home", "args": []},
    ]


def plan_as_text(plan: list[dict]) -> str:
    rows = []
    for index, step in enumerate(plan):
        args = " ".join(step["args"])
        call = f"{step['action']} {args}".rstrip()
        rows.append(f"{index}: ({call})")
    return "\n".join(rows)


def intent_from_problem(problem: str, items: list[dict], targets: dict[str, tuple]) -> Intent:
    """Validate the editable teaching problem and recover its single at-goal."""
    clean = re.sub(r";[^\n]*", "", problem)
    if clean.count("(") != clean.count(")"):
        raise ValueError("PDDL 括号不平衡，请检查是否遗漏左括号或右括号。")
    if not re.search(r"\(\s*:domain\s+power-maintenance\s*\)", clean, re.IGNORECASE):
        raise ValueError("Problem PDDL 必须使用 power-maintenance Domain。")
    goal_block = re.search(r"\(\s*:goal\s+\(\s*at\s+([\w-]+)\s+([\w-]+)\s*\)\s*\)", clean, re.IGNORECASE)
    if not goal_block:
        raise ValueError("教学版规划器需要 (:goal (at 物体 目标区域)) 形式的单一目标。")
    item, target = map(safe_symbol, goal_block.groups())
    item_names = {safe_symbol(entry["name"]) for entry in items}
    if item not in item_names:
        raise ValueError(f"目标中的物体 {item} 不在当前场景中。")
    if target not in targets:
        raise ValueError(f"目标区域 {target} 未定义。")
    return Intent(item, target)


def heuristic_intent(text: str, items: list[dict], targets: dict[str, tuple]) -> Intent:
    """Offline fallback: match a known item and target in Chinese or English text."""
    normalized = text.lower().replace("号区域", "").replace("区域", "")
    matched_item = None
    for item in items:
        if item["name"].lower() in normalized or item["label"] in text:
            matched_item = safe_symbol(item["name"])
            break
    if matched_item is None and len(items) == 1:
        matched_item = safe_symbol(items[0]["name"])
    matched_target = None
    aliases = {
        "回收": "recycle_area", "更换": "replacement_area", "工具": "tool_area",
        "安全": "safe_area", "1": "slot_1", "2": "slot_2", "3": "slot_3",
        "熔断器安装槽": "fuse_slot", "端子插槽": "terminal_slot",
        "断路器安装位": "breaker_bay", "检测点": "test_point",
        "开关操作点": "switch_point", "覆盖区": "cover_area",
    }
    for phrase, target in aliases.items():
        if phrase in normalized and target in targets:
            matched_target = target
            break
    for target in targets:
        if target.lower() in normalized:
            matched_target = target
            break
    if not matched_item:
        raise ValueError("无法确定要操作的物体，请在指令中写出物体名称。")
    if not matched_target:
        raise ValueError("无法确定目标区域，请写明回收区、更换区、安全区或 slot_1～3。")
    return Intent(matched_item, matched_target)

