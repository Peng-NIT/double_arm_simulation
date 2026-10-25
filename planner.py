"""Small, transparent dual-arm PDDL teaching layer."""

from __future__ import annotations

from dataclasses import dataclass
import re


DOMAIN_PDDL = """(define (domain dual-arm-power-maintenance)
  (:requirements :strips :typing)
  (:types component location arm route)
  (:predicates
    (at ?x - component ?p - location)
    (arm-empty ?a - arm)
    (holding ?a - arm ?x - component)
    (fixture-stable ?p - location)
    (stabilizing ?a - arm ?p - location)
    (stabilized ?x - component)
    (stripped ?x - component)
    (tested ?x - component ?p - location)
    (operated ?x - component ?p - location)
    (hazard-mapped ?p - location)
    (route-open ?r - route)
    (route-approved ?a - arm ?p - location))

  (:action verify-safe-route
    :parameters (?a - arm ?p - location ?r - route)
    :precondition (and (arm-empty ?a) (hazard-mapped ?p) (route-open ?r))
    :effect (route-approved ?a ?p))

  (:action pick
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (and (at ?x ?p) (arm-empty ?a))
    :effect (and (holding ?a ?x) (not (at ?x ?p)) (not (arm-empty ?a))))

  (:action place
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (holding ?a ?x)
    :effect (and (at ?x ?p) (arm-empty ?a) (not (holding ?a ?x))))

  (:action insert-component
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (holding ?a ?x)
    :effect (and (at ?x ?p) (arm-empty ?a) (not (holding ?a ?x))))

  (:action seat-component
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (holding ?a ?x)
    :effect (and (at ?x ?p) (arm-empty ?a) (not (holding ?a ?x))))

  (:action test-component
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (holding ?a ?x)
    :effect (tested ?x ?p))

  (:action operate-component
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (holding ?a ?x)
    :effect (operated ?x ?p))

  (:action stage-component
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (and (holding ?a ?x) (route-approved ?a ?p))
    :effect (holding ?a ?x))

  (:action stabilize-fixture
    :parameters (?a - arm ?p - location)
    :precondition (and (arm-empty ?a) (route-approved ?a ?p))
    :effect (and (fixture-stable ?p) (stabilizing ?a ?p)
                 (not (arm-empty ?a))))

  (:action assisted-place
    :parameters (?primary ?assistant - arm ?x - component ?p - location)
    :precondition (and (holding ?primary ?x) (fixture-stable ?p)
                       (stabilizing ?assistant ?p))
    :effect (and (at ?x ?p) (arm-empty ?primary)
                 (not (holding ?primary ?x))))

  (:action assisted-insert
    :parameters (?primary ?assistant - arm ?x - component ?p - location)
    :precondition (and (holding ?primary ?x) (fixture-stable ?p)
                       (stabilizing ?assistant ?p))
    :effect (and (at ?x ?p) (arm-empty ?primary)
                 (not (holding ?primary ?x))))

  (:action assisted-seat
    :parameters (?primary ?assistant - arm ?x - component ?p - location)
    :precondition (and (holding ?primary ?x) (fixture-stable ?p)
                       (stabilizing ?assistant ?p))
    :effect (and (at ?x ?p) (arm-empty ?primary)
                 (not (holding ?primary ?x))))

  (:action assisted-cover
    :parameters (?primary ?assistant - arm ?x - component ?p - location)
    :precondition (and (holding ?primary ?x) (fixture-stable ?p)
                       (stabilizing ?assistant ?p))
    :effect (and (at ?x ?p) (arm-empty ?primary)
                 (not (holding ?primary ?x))))

  (:action assisted-mount
    :parameters (?primary ?assistant - arm ?x - component ?p - location)
    :precondition (and (holding ?primary ?x) (fixture-stable ?p)
                       (stabilizing ?assistant ?p))
    :effect (and (at ?x ?p) (arm-empty ?primary)
                 (not (holding ?primary ?x))))

  (:action assisted-test
    :parameters (?primary ?assistant - arm ?x - component ?p - location)
    :precondition (and (holding ?primary ?x) (fixture-stable ?p)
                       (stabilizing ?assistant ?p))
    :effect (tested ?x ?p))

  (:action assisted-operate
    :parameters (?primary ?assistant - arm ?x - component ?p - location)
    :precondition (and (holding ?primary ?x) (fixture-stable ?p)
                       (stabilizing ?assistant ?p))
    :effect (operated ?x ?p))

  (:action release-fixture
    :parameters (?a - arm ?p - location)
    :precondition (stabilizing ?a ?p)
    :effect (and (arm-empty ?a) (not (stabilizing ?a ?p))
                 (not (fixture-stable ?p))))

  (:action hold-wire
    :parameters (?a - arm ?x - component)
    :precondition (holding ?a ?x)
    :effect (stabilized ?x))

  (:action strip-wire
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (and (arm-empty ?a) (stabilized ?x))
    :effect (stripped ?x))

  (:action insert-wire
    :parameters (?a - arm ?x - component ?p - location)
    :precondition (and (holding ?a ?x) (stripped ?x))
    :effect (at ?x ?p))

  (:action return-home
    :parameters (?a - arm)
    :precondition (arm-empty ?a)
    :effect (arm-empty ?a)))
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
    locations = sorted({safe_symbol(item["location"]) for item in items} |
                       {intent.target, "home", "wire_strip_station", "terminal_slot"})
    init = "\n    ".join(
        f"(at {safe_symbol(item['name'])} {safe_symbol(item['location'])})" for item in items
    )
    selected = next((item for item in items if safe_symbol(item["name"]) == intent.item), None)
    kind = selected.get("kind") if selected else None
    goal = ((f"(tested {intent.item} {intent.target})" if kind == "probe" else
             f"(operated {intent.item} {intent.target})" if kind == "operating_rod" else
             f"(at {intent.item} {intent.target})"))
    return f"""(define (problem dual-arm-maintenance-task)
  (:domain dual-arm-power-maintenance)
  (:objects
    {' '.join(names) or 'placeholder'} - component
    {' '.join(locations)} - location
    left_arm right_arm - arm
    route_left route_right route_high route_direct - route)
  (:init
    (arm-empty left_arm)
    (arm-empty right_arm)
    {init}
    {' '.join(f'(hazard-mapped {location})' for location in locations)}
    (route-open route_left) (route-open route_right)
    (route-open route_high) (route-open route_direct))
  (:goal {goal}))
"""


def _preferred_arm(item: dict, target: str) -> str:
    from lab_config import TARGETS
    target_y = float(TARGETS.get(target, item["position"])[1])
    return "left_arm" if target_y >= 0 else "right_arm"


def make_plan(items: list[dict], intent: Intent, execution_arm: str | None = None,
              route_choice: str = "route_auto") -> list[dict]:
    from lab_config import TASK_MODES

    item = next((x for x in items if safe_symbol(x["name"]) == intent.item), None)
    if item is None:
        raise ValueError(f"场景中不存在物体：{intent.item}")
    if route_choice not in {"route_auto", "route_left", "route_right", "route_high", "route_direct"}:
        raise ValueError("未知安全路线，请使用 route_left、route_right、route_high 或 route_direct。")
    source = safe_symbol(item["location"])
    mode = TASK_MODES[item["kind"]]
    if route_choice == "route_auto":
        route_arm = (execution_arm or
                     ("left_arm" if item["kind"] == "wire" else _preferred_arm(item, intent.target)))
        route_choice = "route_left" if route_arm == "left_arm" else "route_right"
    if mode == "dual" and execution_arm is not None:
        raise ValueError("该任务已锁定为双臂协作，不能传入左臂或右臂单臂选项。")
    if mode == "single" and execution_arm not in {None, "left_arm", "right_arm"}:
        raise ValueError("单臂任务的执行机械臂必须是 left_arm 或 right_arm。")
    if source == intent.target:
        if mode == "single":
            arm = execution_arm or _preferred_arm(item, intent.target)
            return [{"action": "return-home", "args": [arm]}]
        return [{"action": "return-home", "args": ["left_arm"]},
                {"action": "return-home", "args": ["right_arm"]}]

    if item["kind"] == "wire":
        if execution_arm is not None:
            raise ValueError("导线剝线与接线任务必须使用双臂，不能指定单臂。")
        return [
            {"action": "pick", "args": ["left_arm", intent.item, source]},
            {"action": "verify-safe-route", "args": ["left_arm", "wire_strip_station", route_choice]},
            {"action": "verify-safe-route", "args": ["right_arm", "wire_strip_station", route_choice]},
            {"action": "hold-wire", "args": ["left_arm", intent.item]},
            {"action": "strip-wire", "args": ["right_arm", intent.item, "wire_strip_station"]},
            {"action": "insert-wire", "args": ["left_arm", intent.item, "terminal_slot"]},
            {"action": "place", "args": ["left_arm", intent.item, "terminal_slot"]},
            {"action": "return-home", "args": ["left_arm"]},
            {"action": "return-home", "args": ["right_arm"]},
        ]

    if mode == "single":
        arm = execution_arm or _preferred_arm(item, intent.target)
        task_action = {
            "fuse": "insert-component", "terminal": "insert-component",
            "breaker": "seat-component", "probe": "test-component",
            "operating_rod": "operate-component",
        }[item["kind"]]
        plan = [
            {"action": "pick", "args": [arm, intent.item, source]},
            {"action": "verify-safe-route", "args": [arm, intent.target, route_choice]},
            {"action": "stage-component", "args": [arm, intent.item, intent.target]},
            {"action": task_action, "args": [arm, intent.item, intent.target]},
        ]
        if item["kind"] in {"probe", "operating_rod"}:
            plan.append({"action": "place", "args": [arm, intent.item, source]})
        plan.append({"action": "return-home", "args": [arm]})
        return plan

    primary = _preferred_arm(item, intent.target)
    assistant = "right_arm" if primary == "left_arm" else "left_arm"
    # The assistant now interacts with the actual destination fixture/area and
    # remains there while the primary arm seats the component.  This is a
    # causal collaboration rather than an unrelated gesture near the source.
    collaboration_action = {
        "fuse": "assisted-insert", "terminal": "assisted-insert",
        "breaker": "assisted-seat", "insulator": "assisted-seat",
        "shield": "assisted-cover", "busbar": "assisted-mount",
        "probe": "assisted-test", "operating_rod": "assisted-operate",
    }.get(item["kind"], "assisted-place")
    plan = [
        {"action": "pick", "args": [primary, intent.item, source]},
        {"action": "verify-safe-route", "args": [primary, intent.target, route_choice]},
        {"action": "stage-component", "args": [primary, intent.item, intent.target]},
        {"action": "verify-safe-route", "args": [assistant, intent.target, route_choice]},
        {"action": "stabilize-fixture", "args": [assistant, intent.target]},
        {"action": collaboration_action, "args": [primary, assistant, intent.item, intent.target]},
        {"action": "release-fixture", "args": [assistant, intent.target]},
    ]
    if item["kind"] in {"probe", "operating_rod"}:
        plan.append({"action": "place", "args": [primary, intent.item, source]})
    plan.extend([{"action": "return-home", "args": [primary]},
                 {"action": "return-home", "args": [assistant]}])
    return plan


def plan_as_text(plan: list[dict]) -> str:
    return "\n".join(
        f"{index}: ({step['action']} {' '.join(step['args'])})".rstrip()
        for index, step in enumerate(plan)
    )


def pddl_fill_exercise(level: str, intent: Intent, item_kind: str = "",
                       route_choice: str = "route_left") -> dict:
    """Return a deterministic course exercise tied to the current task."""
    goal_predicate = {
        "probe": "tested",
        "operating_rod": "operated",
    }.get(item_kind, "at")
    if level == "基础":
        return {
            "title": "识别Problem的Domain与目标",
            "template": ("(:domain ____1____)\n(:goal (" + goal_predicate +
                         " {item} ____2____))").format(item=intent.item),
            "blanks": [
                {"label": "空格1：Domain名称", "answer": "dual-arm-power-maintenance",
                 "hint": "Problem必须引用本页只读Domain顶部define中的名称。"},
                {"label": "空格2：目标位置", "answer": intent.target,
                 "hint": "目标位置来自本次自然语言任务识别结果。"},
            ],
        }
    if level == "进阶":
        return {
            "title": "补全带电环境安全状态",
            "template": ("(:init\n  (____1____ {target})\n  (arm-empty left_arm))\n"
                         "(:goal (____2____ {item} {target}))").format(
                             item=intent.item, target=intent.target),
            "blanks": [
                {"label": "空格1：风险区已完成映射", "answer": "hazard-mapped",
                 "hint": "该谓词表示规划器已经知道目标附近的带电风险分布。"},
                {"label": "空格2：目标谓词", "answer": goal_predicate,
                 "hint": ({"tested": "验电任务的目标表示检测已完成。",
                           "operated": "开关操作任务的目标表示操作已完成。"}
                          .get(goal_predicate,
                               "普通安装任务使用描述物体位置的二元谓词。"))},
            ],
        }
    return {
        "title": "补全安全路线并将其传递给后续运动",
        "template": ("(:action verify-safe-route\n"
                     " :parameters (?a - arm ?p - location ?r - route)\n"
                     " :precondition (and (arm-empty ?a) (____1____ ?p) (route-open ?r))\n"
                     " :effect (route-approved ?a ?p))\n"
                     "\n; 本次选择的绕行路线\n"
                     "(verify-safe-route left_arm {target} ____2____)"
                     ).format(target=intent.target),
        "blanks": [
            {"label": "空格1：目标风险已建图", "answer": "hazard-mapped",
             "hint": "只有已完成风险建图的位置才能进行路线验证。"},
            {"label": "空格2：传递给运动规划的路线名", "answer": route_choice,
             "hint": "这个 route 对象会直接决定第三页生成的绕行路点。"},
        ],
    }


def grade_pddl_blanks(exercise: dict, responses: list[str]) -> tuple[int, list[bool]]:
    def normalized(value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower()).strip("() ")
    checks = [normalized(response) == normalized(blank["answer"])
              for response, blank in zip(responses, exercise["blanks"])]
    return sum(checks), checks


def intent_from_problem(problem: str, items: list[dict], targets: dict[str, tuple]) -> Intent:
    clean = re.sub(r";[^\n]*", "", problem)
    if clean.count("(") != clean.count(")"):
        raise ValueError("PDDL 括号不平衡，请检查是否遗漏左括号或右括号。")
    if not re.search(r"\(\s*:domain\s+dual-arm-power-maintenance\s*\)", clean, re.IGNORECASE):
        raise ValueError("Problem PDDL 必须使用 dual-arm-power-maintenance Domain。")
    goal = re.search(
        r"\(\s*:goal\s+\(\s*(?:at|tested|operated)\s+([\w-]+)\s+([\w-]+)\s*\)\s*\)",
        clean, re.IGNORECASE)
    if not goal:
        raise ValueError("教学版规划器需要 at、tested 或 operated 形式的单一目标。")
    item, target = map(safe_symbol, goal.groups())
    if item not in {safe_symbol(entry["name"]) for entry in items}:
        raise ValueError(f"目标中的物体 {item} 不在当前场景中。")
    if target not in targets:
        raise ValueError(f"目标区域 {target} 未定义。")
    return Intent(item, target)


def heuristic_intent(text: str, items: list[dict], targets: dict[str, tuple]) -> Intent:
    normalized = text.lower().replace("号区域", "").replace("区域", "")
    matched_item = next((safe_symbol(item["name"]) for item in items
                         if item["name"].lower() in normalized or item["label"] in text), None)
    if matched_item is None and len(items) == 1:
        matched_item = safe_symbol(items[0]["name"])
    aliases = {
        "回收": "recycle_area", "更换": "replacement_area", "工具": "tool_area",
        "绝缘子检修座": "insulator_stand", "绝缘子座": "insulator_stand",
        "母排安装位": "busbar_mount", "母排位": "busbar_mount",
        "安全": "safe_area", "1": "slot_1", "2": "slot_2", "3": "slot_3",
        "熔断器安装槽": "fuse_slot", "端子插槽": "terminal_slot", "接线": "terminal_slot",
        "剥线": "terminal_slot", "断路器安装位": "breaker_bay", "检测点": "test_point",
        "开关操作点": "switch_point", "覆盖区": "cover_area",
    }
    matched_target = next((target for phrase, target in aliases.items()
                           if phrase in normalized and target in targets), None)
    if not matched_target:
        matched_target = next((target for target in targets if target.lower() in normalized), None)
    if not matched_item:
        raise ValueError("无法确定要操作的物体，请在指令中写出物体名称。")
    if not matched_target:
        raise ValueError("无法确定目标区域，请写明回收区、安全区、固定工位或接线任务。")
    return Intent(matched_item, matched_target)
