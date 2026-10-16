"""Shared teaching configuration for the power-maintenance lab."""

TARGETS = {
    "slot_1": (0.66, 0.20, 0.17),
    "slot_2": (0.66, 0.10, 0.17),
    "slot_3": (0.66, 0.00, 0.17),
    "fuse_slot": (0.54, 0.27, 0.115),
    "terminal_slot": (0.70, 0.27, 0.115),
    "breaker_bay": (0.70, 0.04, 0.135),
    "test_point": (0.52, -0.24, 0.15),
    "switch_point": (0.70, -0.24, 0.16),
    "cover_area": (0.50, 0.06, 0.075),
}

STATIONS = {
    "A": {"label": "拆装工位", "color": "蓝色", "center": (0.62, 0.27, 0.073), "size": (0.18, 0.085), "rgba": "0.24 0.52 0.68 0.24"},
    "B": {"label": "模块检修工位", "color": "灰色", "center": (0.70, 0.04, 0.073), "size": (0.095, 0.085), "rgba": "0.34 0.39 0.43 0.24"},
    "C": {"label": "检测操作工位", "color": "橙色", "center": (0.61, -0.24, 0.073), "size": (0.19, 0.085), "rgba": "0.78 0.40 0.20 0.24"},
    "D": {"label": "绝缘防护工位", "color": "黄色", "center": (0.50, 0.06, 0.073), "size": (0.105, 0.09), "rgba": "0.76 0.65 0.24 0.24"},
}

# Recommended staging zones for objects before the robot starts a task.  These
# zones sit near the relevant station but stay clear of its fixed fixture.
PLACEMENT_ZONES = {
    "fuse": {"label": "蓝色拆装区左侧暂存区", "station": "A", "x": (0.38, 0.46), "y": (0.22, 0.32), "default": (0.43, 0.27)},
    "terminal": {"label": "蓝色拆装区前侧备件区", "station": "A", "x": (0.56, 0.66), "y": (0.14, 0.20), "default": (0.61, 0.17)},
    "busbar": {"label": "蓝色拆装区长件暂存区", "station": "A", "x": (0.36, 0.44), "y": (0.20, 0.32), "default": (0.40, 0.26)},
    "breaker": {"label": "灰色模块区正面暂存区", "station": "B", "x": (0.52, 0.60), "y": (-0.04, 0.04), "default": (0.56, 0.00)},
    "insulator": {"label": "灰色模块区侧面暂存区", "station": "B", "x": (0.50, 0.58), "y": (0.10, 0.18), "default": (0.54, 0.14)},
    "probe": {"label": "橙色检测区工具暂存区", "station": "C", "x": (0.34, 0.42), "y": (-0.30, -0.20), "default": (0.38, -0.25)},
    "operating_rod": {"label": "橙色检测区长工具暂存区", "station": "C", "x": (0.34, 0.42), "y": (-0.30, -0.20), "default": (0.38, -0.25)},
    "shield": {"label": "黄色防护区前侧暂存区", "station": "D", "x": (0.46, 0.54), "y": (-0.08, -0.02), "default": (0.50, -0.05)},
}

# Fixed, non-movable teaching fixtures.  They make semantic PDDL targets visible
# without turning the exercise into a full switchgear world model.
FACILITIES = {
    "fuse_slot": {"label": "熔断器安装槽", "station": "A", "position": (0.54, 0.27, 0.115), "kind": "slot", "rgba": "0.16 0.43 0.62 1"},
    "terminal_slot": {"label": "接线端子插槽", "station": "A", "position": (0.70, 0.27, 0.115), "kind": "slot", "rgba": "0.28 0.61 0.74 1"},
    "breaker_bay": {"label": "断路器安装位", "station": "B", "position": (0.70, 0.04, 0.135), "kind": "bay", "rgba": "0.25 0.29 0.32 1"},
    "test_point": {"label": "电气检测点", "station": "C", "position": (0.52, -0.24, 0.15), "kind": "point", "rgba": "0.88 0.28 0.18 1"},
    "switch_point": {"label": "隔离开关操作点", "station": "C", "position": (0.70, -0.24, 0.16), "kind": "switch", "rgba": "0.92 0.54 0.14 1"},
    "cover_area": {"label": "绝缘护罩覆盖区", "station": "D", "position": (0.50, 0.06, 0.075), "kind": "area", "rgba": "0.88 0.72 0.18 0.42"},
}

TASK_PROFILES = {
    "fuse": {"facility": "fuse_slot", "task": "将故障熔断器沿轴向拔出并移至回收区 recycle_area", "pddl": "align → grasp → extract → move → release", "focus": "轴向距离、安全高度"},
    "terminal": {"facility": "terminal_slot", "task": "将备用接线端子对准端子插槽 terminal_slot 并低速插入", "pddl": "grasp → align → insert → verify → release", "focus": "对准位置、接近距离"},
    "breaker": {"facility": "breaker_bay", "task": "将断路器模块正面对准安装位 breaker_bay 并低速就位", "pddl": "align-front → grasp → move → place-upright", "focus": "正面接近、腕部姿态"},
    "probe": {"facility": "test_point", "task": "使用验电笔接近检测点 test_point 并保持检测姿态", "pddl": "grasp-middle → approach → hold-test → retract → return-tool", "focus": "探头方向、检测距离"},
    "operating_rod": {"facility": "switch_point", "task": "使用绝缘操作杆接近开关操作点 switch_point 并定向推动", "pddl": "grasp-middle → orient → push → retract → return-tool", "focus": "工具方向、末端摆幅"},
    "shield": {"facility": "cover_area", "task": "将绝缘护罩对准覆盖区 cover_area 并垂直下降", "pddl": "grasp-edge → lift-flat → align-cover → lower-cover", "focus": "平面姿态、下降距离"},
    "insulator": {"facility": "breaker_bay", "task": "保持绝缘子竖直并转移至安全区", "pddl": "grasp → lift-upright → move → release", "focus": "竖直姿态、安全高度"},
    "busbar": {"facility": "terminal_slot", "task": "从中心夹持母排并保持水平转移至安全区", "pddl": "grasp-center → lift-flat → move → release", "focus": "中心夹持、水平姿态"},
}

REGIONS = {
    "inspection_area": {"label": "检修区", "xy": (0.45, 0.14), "x": (0.40, 0.50), "y": (0.10, 0.18), "color": "青色", "rgba": "0.20 0.78 0.82", "help": "正在检修或等待操作的部件。"},
    "replacement_area": {"label": "备件区", "xy": (0.44, -0.31), "x": (0.40, 0.48), "y": (-0.35, -0.27), "color": "紫色", "rgba": "0.55 0.42 0.76", "help": "新备件的存放区域。"},
    "tool_area": {"label": "工具区", "xy": (0.44, 0.34), "x": (0.40, 0.48), "y": (0.30, 0.38), "color": "绿色", "rgba": "0.30 0.68 0.48", "help": "绝缘工具和测试工具的存放区域。"},
    "safe_area": {"label": "安全区", "xy": (0.74, 0.14), "x": (0.70, 0.78), "y": (0.10, 0.18), "color": "白色", "rgba": "0.82 0.87 0.89", "help": "临时放置已处理部件。"},
    "recycle_area": {"label": "回收区", "xy": (0.58, -0.31), "x": (0.52, 0.64), "y": (-0.35, -0.27), "color": "红色", "rgba": "0.78 0.28 0.25", "help": "故障或拆除部件的回收区域。"},
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
        "region": "inspection_area", "operation": "竖直搬运",
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
        "region": "safe_area", "operation": "平面姿态搬运",
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

