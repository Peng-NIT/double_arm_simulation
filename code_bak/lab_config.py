"""Shared teaching configuration for the power-maintenance lab."""

TARGETS = {
    "recycle_area": (0.38, -0.27, 0.14),
    "replacement_area": (0.58, -0.27, 0.14),
    "safe_area": (0.70, 0.00, 0.14),
    "tool_area": (0.38, 0.27, 0.14),
    "slot_1": (0.66, 0.20, 0.17),
    "slot_2": (0.66, 0.10, 0.17),
    "slot_3": (0.66, 0.00, 0.17),
}

REGIONS = {
    "inspection_area": {"label": "检修区", "xy": (0.48, 0.04), "help": "正在检修或等待操作的部件。"},
    "replacement_area": {"label": "备件区", "xy": (0.58, -0.27), "help": "新备件的存放区域。"},
    "tool_area": {"label": "工具区", "xy": (0.38, 0.27), "help": "绝缘工具和测试工具的存放区域。"},
    "safe_area": {"label": "安全区", "xy": (0.70, 0.00), "help": "临时放置已处理部件。"},
    "recycle_area": {"label": "回收区", "xy": (0.38, -0.27), "help": "故障或拆除部件的回收区域。"},
}

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
     "position": (0.48, 0.04, 0.137), "location": "inspection_area"},
    {"name": "new_fuse_1", "label": "新熔断器", "preset": "熔断器", "kind": "fuse",
     "size": (0.025, 0.025, 0.065), "rgba": "0.20 0.75 0.32 1",
     "position": (0.58, -0.27, 0.137), "location": "replacement_area"},
]

