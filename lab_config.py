"""Shared teaching configuration for the power-maintenance lab."""

from __future__ import annotations

import random

# Expanded workbench: the top height remains 0.07 m so existing object and
# trajectory Z values stay valid, while the longer/deeper surface lets storage
# zones and operating stations remain visually independent.
WORKBENCH = {"center": (0.68, 0.0, 0.035), "half_size": (0.90, 1.10, 0.035)}

# Fixed overhead conductors constrain high-Z detours.  The safety envelope is
# deliberately larger than the visible wire radius and remains a teaching
# abstraction rather than a statutory live-work distance.
POWER_LINES = [
    {"name": "hv_line_1", "start": (0.42, -0.82, 0.72), "end": (0.42, 0.82, 0.72),
     "radius": 0.014, "safe_margin": 0.085, "rgba": "0.72 0.08 0.12 0.62"},
    {"name": "hv_line_2", "start": (0.62, -0.82, 0.75), "end": (0.62, 0.82, 0.75),
     "radius": 0.014, "safe_margin": 0.085, "rgba": "0.84 0.12 0.10 0.62"},
    {"name": "hv_line_3", "start": (0.82, -0.82, 0.72), "end": (0.82, 0.82, 0.72),
     "radius": 0.014, "safe_margin": 0.085, "rgba": "0.72 0.08 0.12 0.62"},
]

# These are teaching visualisations, not statutory live-work clearances.  Each
# task gets two sizeable exclusion volumes beside a central approach corridor.
# Keeping the corridor explicit avoids tiny decorative zones and guarantees
# that a generated scene can still be used by the compact dual-arm model.
HAZARD_LEVELS = {
    "低": {"margin": 0.020, "rgba": "0.94 0.58 0.12 0.18"},
    "中": {"margin": 0.030, "rgba": "0.92 0.31 0.10 0.22"},
    "高": {"margin": 0.040, "rgba": "0.78 0.10 0.08 0.26"},
}


def generate_hazard_zones(facility_name: str, seed: int = 20261024,
                          level: str = "中",
                          start_position: tuple | list | None = None) -> list[dict]:
    """Generate a reproducible obstacle on the transport corridor.

    Unlike the former decorative zones behind the fixture, this volume is
    placed between the selected object's start and its target.  A seeded
    lateral offset keeps exercises varied while leaving both side routes on
    the expanded workbench.
    """
    if facility_name not in FACILITIES:
        return []
    config = HAZARD_LEVELS.get(level, HAZARD_LEVELS["中"])
    rng = random.Random(int(seed) + sum(map(ord, facility_name)))
    tx, ty, _ = FACILITIES[facility_name]["position"]
    sx0, sy0 = ((float(start_position[0]), float(start_position[1]))
                if start_position is not None else REGIONS["inspection_area"]["xy"])
    table_x, table_y, _ = WORKBENCH["center"]
    half_x, half_y, _ = WORKBENCH["half_size"]
    margin = float(config["margin"])
    zone_half_x = rng.uniform(0.040, 0.050)
    zone_half_y = rng.uniform(0.055, 0.075)
    if facility_name in {"wire_strip_station", "busbar_mount"}:
        zone_half_x = 0.025
    if facility_name == "wire_strip_station":
        zone_half_y = 0.040
    # Bias the barrier towards the equipment side so the pickup remains easy,
    # while the carrying motion must make an explicit route decision.
    ratio = rng.uniform(0.45, 0.50)
    cx = sx0 + ratio * (tx - sx0) + rng.uniform(-0.012, 0.012)
    lateral_bias = 0.0
    cy = sy0 + ratio * (ty - sy0) + lateral_bias + rng.uniform(-0.018, 0.018)
    cx = min(max(cx, table_x - half_x + zone_half_x + margin + 0.025),
             table_x + half_x - zone_half_x - margin - 0.025)
    cy = min(max(cy, table_y - half_y + zone_half_y + margin + 0.025),
             table_y + half_y - zone_half_y - margin - 0.025)
    # Keep a small, explicit staging/approach pocket on both ends.  Without
    # this clamp some random seeds put the volume directly under the pickup or
    # the fixture even though the nominal centre was on the corridor.
    if tx >= sx0:
        lower = sx0 + zone_half_x + margin + 0.015
        upper = tx - zone_half_x - margin - 0.015
    else:
        lower = tx + zone_half_x + margin + 0.015
        upper = sx0 - zone_half_x - margin - 0.015
    if lower <= upper:
        cx = min(max(cx, lower), upper)
    # The pickup and interaction centres themselves must remain outside the
    # expanded obstacle for every seed.  Narrow only the Y half-size when a
    # random offset would swallow either endpoint; the box remains wide enough
    # to block the direct centreline and require a visible detour.
    for endpoint_x, endpoint_y in ((sx0, sy0), (tx, ty)):
        if (abs(endpoint_x - cx) <= zone_half_x + margin + 0.07 and
                abs(endpoint_y - cy) <= zone_half_y + margin + 0.07):
            zone_half_y = min(zone_half_y,
                              max(0.018, abs(endpoint_y - cy) - margin - 0.065))
    return [{
        "name": f"{facility_name}_corridor_hazard",
        "facility": facility_name,
        "shape": "box",
        "center": (round(cx, 4), round(cy, 4), 0.285),
        "half_size": (round(zone_half_x, 4), round(zone_half_y, 4), 0.205),
        "clearance_half_size": (round(zone_half_x, 4), round(zone_half_y, 4), 0.140),
        "safe_margin": margin,
        "risk_level": level,
        "rgba": config["rgba"],
        "start": (round(sx0, 4), round(sy0, 4)),
        "target": (round(tx, 4), round(ty, 4)),
    }]


def adjust_hazard_zones(zones: list[dict], offset_x: float = 0.0,
                        offset_y: float = 0.0, scale_x: float = 1.0,
                        scale_y: float = 1.0,
                        margin_delta: float = 0.0) -> list[dict]:
    """Apply bounded classroom adjustments without mutating seeded geometry."""
    adjusted = []
    for source in zones:
        zone = dict(source)
        cx, cy, cz = map(float, source["center"])
        hx, hy, hz = map(float, source["half_size"])
        chx, chy, chz = map(float, source.get("clearance_half_size", source["half_size"]))
        zone["center"] = (round(cx + float(offset_x), 4),
                          round(cy + float(offset_y), 4), cz)
        zone["half_size"] = (round(hx * float(scale_x), 4),
                             round(hy * float(scale_y), 4), hz)
        zone["clearance_half_size"] = (round(chx * float(scale_x), 4),
                                       round(chy * float(scale_y), 4), chz)
        zone["safe_margin"] = round(max(0.015, min(0.080,
            float(source["safe_margin"]) + float(margin_delta))), 4)
        adjusted.append(zone)
    return adjusted


ROUTE_LABELS = {
    "route_left": "从带电区正Y侧绕行",
    "route_right": "从带电区负Y侧绕行",
    "route_high": "提高至上方安全层绕行",
    "route_direct": "直接路线（仅无带电区时）",
}

ERROR_DEMOS = {
    "direct_hazard": {
        "title": "直线穿越带电区",
        "setup": "将 verify-safe-route 错误简化为 route_direct，忽略中间的带电区。",
        "failure": "末端/工具进入带电教学禁止区，预检拒绝执行。",
        "repair": "返回PDDL路线决策，使用与执行臂对应的侧向绕行。",
    },
    "overhead_line": {
        "title": "过度抬高触及高压线包络",
        "setup": "为避开桌面带电区而不断增大Z，把“越高越安全”当作规划规则。",
        "failure": "末端/工具进入上方高压线安全包络，预检拒绝执行。",
        "repair": "降低安全高度，优先改用侧向绕行，然后重新检查全轨迹裕度。",
    },
    "joint_collision": {
        "title": "不合理关节角导致穿模",
        "setup": "只关注末端目标，同时大幅改动q2/q3/q5，忽略连杆、共享基座和另一条机械臂。",
        "failure": "关节插值过程出现连杆与基座或双臂之间的MuJoCo碰撞。",
        "repair": "恢复推荐IK解，小范围逐关节调整，并对相邻两段轨迹做逐帧检查。",
    },
}


def recommended_route(zones: list[dict], start: tuple | list,
                      target: tuple | list) -> str:
    """Choose the global-Y lane on the opposite side of the obstacle."""
    if not zones:
        return "route_direct"
    cx, cy, _ = map(float, zones[0]["center"])
    sx, sy = float(start[0]), float(start[1])
    tx, ty = float(target[0]), float(target[1])
    ratio = 0.5 if abs(tx - sx) < 1e-9 else (cx - sx) / (tx - sx)
    direct_y = sy + ratio * (ty - sy)
    return "route_right" if cy >= direct_y else "route_left"


def route_waypoint(route_name: str, zones: list[dict], start: tuple | list,
                   target: tuple | list, safe_z: float) -> tuple[float, float, float]:
    """Return the visible teaching waypoint associated with a PDDL route."""
    midpoint = ((float(start[0]) + float(target[0])) / 2,
                (float(start[1]) + float(target[1])) / 2)
    if not zones or route_name == "route_direct":
        return midpoint[0], midpoint[1], safe_z
    zone = zones[0]
    cx, cy, cz = map(float, zone["center"])
    hx, hy, hz = map(float, zone.get("clearance_half_size", zone["half_size"]))
    clearance = float(zone.get("safe_margin", 0.0)) + 0.14
    if route_name == "route_left":
        return cx - 0.04, cy + hy + clearance, safe_z
    if route_name == "route_right":
        return cx - 0.04, cy - hy - clearance, safe_z
    # High route clears the expanded volume; the UI only offers it if the
    # required height remains inside the verified 0.52 m teaching limit.
    return cx - 0.04, cy, max(safe_z, cz + hz + float(zone.get("safe_margin", 0.0)) + 0.02)


def route_waypoints(route_name: str, zones: list[dict], start: tuple | list,
                    target: tuple | list, safe_z: float) -> list[tuple[float, float, float]]:
    """Return an entrance/exit corridor carried from PDDL into motion."""
    route_height = float(safe_z) if route_name == "route_high" else min(float(safe_z), 0.45)
    if not zones or route_name in {"route_direct", "route_high"}:
        return [route_waypoint(route_name, zones, start, target, route_height)]
    zone = zones[0]
    cx, cy, _ = map(float, zone["center"])
    hx, hy, _ = map(float, zone.get("clearance_half_size", zone["half_size"]))
    margin = float(zone.get("safe_margin", 0.0))
    side = 1.0 if route_name == "route_left" else -1.0
    lane_y = cy + side * (hy + margin + 0.14)
    # Two points are important: a single midpoint can clear the box and still
    # let the following diagonal segment cut back through it.
    x_pad = hx + margin + 0.10
    start_x, target_x = float(start[0]), float(target[0])
    if start_x <= target_x:
        x_values = (cx - x_pad, cx + x_pad)
    else:
        x_values = (cx + x_pad, cx - x_pad)
    # The compact teaching robot cannot fold its wrist behind x~=0.40.  The
    # start-side lane therefore begins beside the pickup zone, never behind it.
    x_values = (max(0.42, x_values[0]), max(0.42, x_values[1]))
    entry_x = max(0.42, min(float(start[0]), x_values[0]))
    entry_y = float(start[1])
    # Several short Cartesian moves keep joint-space interpolation from bowing
    # the end-effector through the obstacle on its way to the side lane.
    entries = [(entry_x, entry_y + (lane_y - entry_y) * fraction, route_height)
               for fraction in (1 / 3, 2 / 3, 1.0)]
    return entries + [(x_values[1], lane_y, route_height)]


def hazard_layout_is_valid(zones: list[dict]) -> bool:
    """Check table containment, base clearance and a usable central corridor."""
    table_x, table_y, _ = WORKBENCH["center"]
    table_sx, table_sy, _ = WORKBENCH["half_size"]
    for zone in zones:
        x, y, _ = zone["center"]
        sx, sy, _ = zone["half_size"]
        margin = float(zone["safe_margin"])
        if not (table_x - table_sx <= x - sx - margin and
                x + sx + margin <= table_x + table_sx):
            return False
        if not (table_y - table_sy <= y - sy - margin and
                y + sy + margin <= table_y + table_sy):
            return False
        # The shared base occupies the rear-centre portion of the table.
        if x - sx - margin < 0.18 and abs(y) - sy - margin < 0.28:
            return False
    return True

TARGETS = {
    "slot_1": (0.66, 0.20, 0.17),
    "slot_2": (0.66, 0.10, 0.17),
    "slot_3": (0.66, 0.00, 0.17),
    "fuse_slot": (0.68, 0.32, 0.115),
    "terminal_slot": (0.70, 0.30, 0.115),
    "breaker_bay": (0.73, 0.14, 0.135),
    "test_point": (0.68, -0.37, 0.15),
    "switch_point": (0.70, -0.37, 0.16),
    "cover_area": (0.68, 0.02, 0.075),
    "wire_strip_station": (0.64, -0.16, 0.15),
    "insulator_stand": (0.68, 0.14, 0.125),
    "busbar_mount": (0.62, 0.48, 0.105),
}

STATIONS = {
    "A": {"label": "拆装工位", "color": "蓝色", "center": (0.69, 0.40, 0.073), "size": (0.16, 0.15), "rgba": "0.24 0.52 0.68 0.24"},
    "B": {"label": "模块检修工位", "color": "灰色", "center": (0.73, 0.14, 0.073), "size": (0.10, 0.085), "rgba": "0.34 0.39 0.43 0.24"},
    "C": {"label": "检测操作工位", "color": "橙色", "center": (0.69, -0.37, 0.073), "size": (0.11, 0.09), "rgba": "0.78 0.40 0.20 0.24"},
    "D": {"label": "绝缘防护工位", "color": "黄色", "center": (0.68, 0.08, 0.073), "size": (0.11, 0.10), "rgba": "0.76 0.65 0.24 0.24"},
    "E": {"label": "剥线接线协作工位", "color": "紫蓝色", "center": (0.64, -0.16, 0.073), "size": (0.12, 0.075), "rgba": "0.42 0.36 0.72 0.24"},
}

# Recommended staging zones for objects before the robot starts a task.  These
# zones sit near the relevant station but stay clear of its fixed fixture.
PLACEMENT_ZONES = {
    "fuse": {"label": "机器人侧青色检修准备区", "station": "A", "x": (0.39, 0.45), "y": (-0.04, 0.04), "default": (0.42, 0.00)},
    "terminal": {"label": "左前侧紫色备件区", "station": "A", "x": (0.40, 0.48), "y": (-0.34, -0.26), "default": (0.44, -0.30)},
    "busbar": {"label": "机器人侧青色长件准备区", "station": "A", "x": (0.39, 0.45), "y": (-0.04, 0.04), "default": (0.42, 0.00)},
    "breaker": {"label": "左前侧紫色备件区", "station": "B", "x": (0.40, 0.48), "y": (-0.34, -0.26), "default": (0.44, -0.30)},
    "insulator": {"label": "左前侧紫色新绝缘件区", "station": "D", "x": (0.40, 0.48), "y": (-0.34, -0.26), "default": (0.44, -0.30)},
    "probe": {"label": "左后侧绿色工具区", "station": "C", "x": (0.40, 0.48), "y": (0.30, 0.38), "default": (0.44, 0.34)},
    "operating_rod": {"label": "左后侧绿色长工具区", "station": "C", "x": (0.40, 0.48), "y": (0.30, 0.38), "default": (0.44, 0.34)},
    "shield": {"label": "左前侧紫色绝缘用具准备区", "station": "D", "x": (0.40, 0.48), "y": (-0.34, -0.26), "default": (0.44, -0.30)},
    "wire": {"label": "导线准备区", "station": "E", "x": (0.41, 0.49), "y": (0.10, 0.18), "default": (0.45, 0.14)},
}

# Fixed, non-movable teaching fixtures.  They make semantic PDDL targets visible
# without turning the exercise into a full switchgear world model.
FACILITIES = {
    "fuse_slot": {"label": "熔断器安装槽", "station": "A", "position": (0.68, 0.32, 0.115), "kind": "slot", "rgba": "0.16 0.43 0.62 1"},
    "terminal_slot": {"label": "接线端子插槽", "station": "A", "position": (0.70, 0.30, 0.115), "kind": "slot", "rgba": "0.28 0.61 0.74 1"},
    "breaker_bay": {"label": "断路器安装位", "station": "B", "position": (0.73, 0.14, 0.135), "kind": "bay", "rgba": "0.25 0.29 0.32 1"},
    "test_point": {"label": "电气检测点", "station": "C", "position": (0.68, -0.37, 0.15), "kind": "point", "rgba": "0.88 0.28 0.18 1"},
    "switch_point": {"label": "隔离开关操作点", "station": "C", "position": (0.70, -0.37, 0.16), "kind": "switch", "rgba": "0.92 0.54 0.14 1"},
    "cover_area": {"label": "绝缘护罩覆盖区", "station": "D", "position": (0.68, 0.02, 0.075), "kind": "area", "rgba": "0.88 0.72 0.18 0.42"},
    "wire_strip_station": {"label": "剥线定位槽", "station": "E", "position": (0.64, -0.16, 0.15), "kind": "slot", "rgba": "0.48 0.35 0.78 1"},
    "insulator_stand": {"label": "绝缘子检修座", "station": "D", "position": (0.68, 0.14, 0.125), "kind": "bay", "rgba": "0.72 0.64 0.32 1"},
    "busbar_mount": {"label": "母排安装位", "station": "A", "position": (0.62, 0.48, 0.105), "kind": "slot", "rgba": "0.72 0.30 0.10 1"},
}

TASK_PROFILES = {
    "fuse": {"facility": "fuse_slot", "task": "将熔断器对准安装槽 fuse_slot 并完成轴向插装", "pddl": "pick → stage → insert-component → return-home", "focus": "安装轴线、插入距离、安全高度"},
    "terminal": {"facility": "terminal_slot", "task": "将备用接线端子对准端子插槽 terminal_slot 并精密插入", "pddl": "pick → stage → insert-component → return-home", "focus": "端子槽对准、插入距离、接近速度"},
    "breaker": {"facility": "breaker_bay", "task": "将断路器模块正面对准安装位 breaker_bay 并水平推入落座", "pddl": "pick → stage → seat-component → return-home", "focus": "安装导轨、正面接近、腕部姿态"},
    "probe": {"facility": "test_point", "task": "验电笔接近检测点、停留检测后撤回工具区", "pddl": "pick → test-component → return-tool → return-home", "focus": "探头方向、检测距离、停留时间"},
    "operating_rod": {"facility": "switch_point", "task": "绝缘操作杆对准开关、定向推动后回撤并归位", "pddl": "pick → operate-component → return-tool → return-home", "focus": "工具方向、推动行程、末端摆幅"},
    "shield": {"facility": "cover_area", "task": "保持绝缘护罩水平，对准覆盖区后垂直下降", "pddl": "pick → stage → stabilize-cover-area → assisted-cover", "focus": "覆盖区稳定、平面姿态、下降距离"},
    "insulator": {"facility": "insulator_stand", "task": "保持绝缘子竖直，正面接近检修座并稳定落座", "pddl": "pick → stage → stabilize-stand → assisted-seat", "focus": "检修座稳定、竖直姿态、落座高度"},
    "busbar": {"facility": "busbar_mount", "task": "水平搬运母排，完成双点对中后侧向就位", "pddl": "pick → stage → stabilize-mount → assisted-mount", "focus": "双点对中、中心夹持、水平姿态"},
    "wire": {"facility": "wire_strip_station", "task": "双臂协作固定导线、完成剥线并插入接线端子 terminal_slot", "pddl": "left-hold → right-strip → left-insert → release", "focus": "双臂同步、剥线长度、端子对准"},
}

# Five tasks are intentionally teachable with either arm.  The remaining four
# require coordinated use of both arms and must never expose a single-arm
# selector in the planning UI.
TASK_MODES = {
    "fuse": "single", "terminal": "single", "breaker": "single",
    "probe": "single", "operating_rod": "single",
    "shield": "dual", "insulator": "dual", "busbar": "dual", "wire": "dual",
}

ARM_ROLES = {
    "fuse": "单臂轴向插装；可选左臂或右臂，未选机械臂保持 Home 位",
    "terminal": "单臂精密插入；可选左臂或右臂，未选机械臂保持 Home 位",
    "breaker": "单臂正面推入；可选左臂或右臂，未选机械臂保持 Home 位",
    "probe": "单臂持验电笔检测并归位；可选左臂或右臂",
    "operating_rod": "单臂持操作杆推动开关并归位；可选左臂或右臂",
    "shield": "主臂搬运护罩；辅臂稳定覆盖区边界，保持期间主臂平稳下降",
    "insulator": "主臂保持绝缘子竖直；辅臂稳定检修座，保持期间主臂完成安装",
    "busbar": "主臂中心夹持母排；辅臂稳定母排安装位，保持期间主臂水平就位",
    "wire": "左臂固定并插入导线，右臂执行简化剥线动作",
}

REGIONS = {
    "inspection_area": {"label": "检修准备区", "xy": (0.42, 0.00), "x": (0.39, 0.45), "y": (-0.04, 0.04), "color": "青色", "rgba": "0.20 0.78 0.82", "help": "机器人侧的检修准备区，与设备工位之间保留运输和避障距离。"},
    "wire_area": {"label": "导线准备区", "xy": (0.45, 0.14), "x": (0.41, 0.49), "y": (0.10, 0.18), "color": "蓝绿色", "rgba": "0.20 0.64 0.70", "help": "剥线接线任务的导线准备位，与剥线工位分离。"},
    "replacement_area": {"label": "备件区", "xy": (0.44, -0.30), "x": (0.40, 0.48), "y": (-0.34, -0.26), "color": "紫色", "rgba": "0.55 0.42 0.76", "help": "新备件的存放区域。"},
    "tool_area": {"label": "工具区", "xy": (0.44, 0.34), "x": (0.40, 0.48), "y": (0.30, 0.38), "color": "绿色", "rgba": "0.30 0.68 0.48", "help": "绝缘工具和测试工具的存放区域。"},
    "safe_area": {"label": "安全区", "xy": (0.82, -0.08), "x": (0.78, 0.86), "y": (-0.12, -0.04), "color": "白色", "rgba": "0.82 0.87 0.89", "help": "临时放置已处理部件。"},
    "recycle_area": {"label": "回收区", "xy": (0.55, -0.50), "x": (0.48, 0.62), "y": (-0.54, -0.46), "color": "红色", "rgba": "0.78 0.28 0.25", "help": "故障或拆除部件的回收区域。"},
}

# Semantic PDDL locations and MuJoCo region centers share this single source.
# Keep facility targets above; derive every semantic-area target from REGIONS.
TARGETS.update({name: (region["xy"][0], region["xy"][1], 0.14)
                for name, region in REGIONS.items()})


def point_in_region(x: float, y: float, region_name: str) -> bool:
    region = REGIONS[region_name]
    return region["x"][0] <= x <= region["x"][1] and region["y"][0] <= y <= region["y"][1]


def region_for_point(x: float, y: float) -> str | None:
    return next((name for name in REGIONS if point_in_region(x, y, name)), None)

PRESETS = {
    "熔断器": {
        "kind": "fuse", "size": (0.025, 0.025, 0.065), "rgba": "0.88 0.25 0.16 1",
        "region": "inspection_area", "operation": "轴向拔出/插入",
        "guidance": "沿安装轴线对准；夹紧后直线拔出，避免侧向拉动。",
        "risk": "轴线偏差过大可能造成不合理的侧向受力。",
    },
    "绝缘子": {
        "kind": "insulator", "size": (0.035, 0.035, 0.060), "rgba": "0.92 0.92 0.88 1",
        "region": "replacement_area", "operation": "竖直搬运",
        "guidance": "从顶部或侧面稳定夹取，移动中保持竖直。",
        "risk": "倾斜过大可能与周围部件发生碰撞。",
    },
    "母排": {
        "kind": "busbar", "size": (0.080, 0.018, 0.012), "rgba": "0.80 0.34 0.08 1",
        "region": "inspection_area", "operation": "中心夹持低速搬运",
        "guidance": "从几何中心夹持，保持水平并降低速度。",
        "risk": "偏心夹持会增大姿态变化。",
    },
    "接线端子": {
        "kind": "terminal", "size": (0.045, 0.035, 0.025), "rgba": "0.18 0.55 0.80 1",
        "region": "replacement_area", "operation": "精确对准插入",
        "guidance": "降低接近速度，沿安装方向小距离直线插入。",
        "risk": "对准误差可能导致插入失败。",
    },
    "断路器模块": {
        "kind": "breaker", "size": (0.055, 0.045, 0.070), "rgba": "0.20 0.22 0.25 1",
        "region": "replacement_area", "operation": "正面推入/拔出",
        "guidance": "从模块正面接近，沿安装方向平移。",
        "risk": "避免在插入或拔出阶段进行大角度旋转。",
    },
    "绝缘护罩": {
        "kind": "shield", "size": (0.080, 0.065, 0.012), "rgba": "0.96 0.78 0.12 1",
        "region": "replacement_area", "operation": "平面姿态搬运",
        "guidance": "从边缘或顶部抓取，移动时保持护罩平面姿态。",
        "risk": "倾斜可能碰撞邻近电气部件。",
    },
    "验电笔": {
        "kind": "probe", "size": (0.014, 0.014, 0.085), "rgba": "0.90 0.18 0.12 1",
        "region": "tool_area", "operation": "探头接近与停留",
        "guidance": "夹持中部，将探头移动到检测点并短暂停留。",
        "risk": "抓取点过于靠近端部会增加姿态变化。",
    },
    "绝缘操作杆": {
        "kind": "operating_rod", "size": (0.018, 0.018, 0.120), "rgba": "0.96 0.72 0.12 1",
        "region": "tool_area", "operation": "中部夹持定向操作",
        "guidance": "从中部夹持并保持操作杆方向，限制腕部大角度旋转。",
        "risk": "细长物体末端摆动范围较大。",
    },
    "待接导线": {
        "kind": "wire", "size": (0.012, 0.012, 0.090), "rgba": "0.18 0.32 0.78 1",
        "region": "wire_area", "operation": "双臂固定、剥线与端接",
        "guidance": "左臂稳定夹持导线，右臂在剥线定位槽完成简化剥线，随后左臂将线端插入端子槽。",
        "risk": "两臂进入共享区时必须保持安全间距；本实验只表达状态与轨迹，不模拟真实切削。",
    },
}

DEFAULT_ITEMS = [
    {"name": "faulty_fuse_1", "label": "故障熔断器", "preset": "熔断器", "kind": "fuse",
     "size": (0.025, 0.025, 0.065), "rgba": "0.88 0.25 0.16 1",
     "position": (REGIONS["inspection_area"]["xy"][0], REGIONS["inspection_area"]["xy"][1], 0.137),
     "location": "inspection_area"},
    {"name": "new_fuse_1", "label": "新熔断器", "preset": "熔断器", "kind": "fuse",
     "size": (0.025, 0.025, 0.065), "rgba": "0.20 0.75 0.32 1",
     "position": (REGIONS["replacement_area"]["xy"][0], REGIONS["replacement_area"]["xy"][1], 0.137),
     "location": "replacement_area"},
]

