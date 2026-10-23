import streamlit as st

from lab_config import (ARM_ROLES, FACILITIES, PRESETS, REGIONS, STATIONS, TASK_PROFILES,
                        point_in_region, region_for_point)
from lab_state import (camera_controls, invalidate_after_scene_change, nav, page_header,
                       require_login, spotlight_tour)
from planner import safe_symbol
from robot_sim import RobotSimulation

st.set_page_config(page_title="1 场景配置", page_icon="⚡", layout="wide")
require_login()
page_header(1, "1. 场景与物体配置")
spotlight_tour([
    {"target": "tour-intro", "title": "先理解区域与工位",
     "body": "初始区域说明物体当前在哪里；检修工位说明机械臂在哪里操作。二者通过任务关联，并不是同一个概念。"},
    {"target": "tour-object", "title": "选择电力检修对象",
     "body": "九类任务按必要性分配：熔断器、端子、断路器、验电笔和操作杆可选左/右单臂；护罩、绝缘子、母排和导线锁定双臂协作。"},
    {"target": "tour-region", "title": "设置初始区域和坐标",
     "body": "检修区、备件区、工具区、安全区和回收区是PDDL语义位置；X、Y决定物体在该区域内的具体摆放点。"},
    {"target": "tour-add", "title": "把物体加入仿真",
     "body": "选择物体、区域和坐标后点击添加。只有完成这一步，物体才会出现在MuJoCo场景并进入后续PDDL。"},
    {"target": "tour-scene", "title": "观察工位、设施和双臂",
     "body": "彩色工位承载不同检修任务，固定设施是实际交互目标。共享机身固定，左右机械臂各有q1～q6六个关节，可打开关节标注查看。"},
    {"target": "tour-next", "title": "进入PDDL规划",
     "body": "场景确认后进入下一步，用自然语言描述任务并观察它如何转化为带左右臂分工的PDDL计划。"},
])
with st.container(key="tour-intro"):
    st.info("实验从空场景开始。“初始区域”是 PDDL 中的语义位置，XYZ 是 MuJoCo 中的连续坐标；只有点击“添加物体”后，部件才会进入仿真环境。")
    expander = st.expander("初始区域与检修工位如何对应？", expanded=False)
with expander:
    st.write("初始区域表示物体当前的存放位置；检修工位表示执行操作的位置。机械臂从初始区域夹取物体，移动到对应工位，并与固定设施完成交互。")
    relation_rows = []
    for object_name, object_preset in PRESETS.items():
        object_profile = TASK_PROFILES[object_preset["kind"]]
        object_facility = FACILITIES[object_profile["facility"]]
        object_station = STATIONS[object_facility["station"]]
        object_region = REGIONS[object_preset["region"]]
        relation_rows.append({
            "操作对象": object_name,
            "推荐初始区域": f"{object_region['color']}{object_region['label']}",
            "对应检修工位": f"{object_station['color']}{object_station['label']}",
            "固定设施": object_facility["label"],
            "双臂分工": ARM_ROLES[object_preset["kind"]],
        })
    st.dataframe(relation_rows, hide_index=True, width="stretch")
    st.caption("初始区域负责描述PDDL存放状态；检修工位负责描述机械臂执行的实际操作。二者通过操作对象和任务关联，而不是固定的一一对应关系。")

left, right = st.columns([1, 1.3])
with left:
    with st.container(key="tour-object"):
        preset_name = st.selectbox("电力物体", list(PRESETS))
        preset = PRESETS[preset_name]
        profile = TASK_PROFILES[preset["kind"]]
        facility = FACILITIES[profile["facility"]]
        with st.container(border=True):
            st.markdown(f"#### {preset_name}操作提示")
            recommended_region = REGIONS[preset["region"]]
            station = STATIONS[facility["station"]]
            st.info(f"任务路径：{recommended_region['color']}{recommended_region['label']} → "
                    f"{station['color']}{station['label']} → {facility['label']}")
            st.write(f"**固定交互设施：** {facility['label']}")
            st.write(f"**推荐检修任务：** {profile['task']}")
            st.write(f"**检修动作展开：** `{profile['pddl']}`")
            st.write(f"**双臂分工：** {ARM_ROLES[preset['kind']]}")
            st.write(f"**操作方式：** {preset['operation']}")
            st.write(f"**推荐方法：** {preset['guidance']}")
            st.write(f"**重点参数：** {profile['focus']}")
            st.warning(f"注意：{preset['risk']}")
    default_name = f"{preset['kind']}_{len(st.session_state['items']) + 1}"
    with st.container(key="tour-region"):
        name = st.text_input("物体英文名称", value=default_name)
        region = st.selectbox("初始区域", list(REGIONS), index=list(REGIONS).index(preset["region"]),
                              format_func=lambda key: f"{REGIONS[key]['label']}（{key}）")
        region_config = REGIONS[region]
        st.caption(region_config["help"])
        if region != preset["region"]:
            st.warning(f"该物体通常从{REGIONS[preset['region']]['label']}开始；当前选择仍可用于比较不同初始状态。")
        st.caption(f"当前选择：{region_config['color']}{region_config['label']}；推荐操作目的地："
                   f"{station['color']}{station['label']}中的{facility['label']}。X/Y只允许在当前初始区域内调节。")
        c1, c2 = st.columns(2)
        x = c1.slider("区域内 X / m", float(region_config["x"][0]), float(region_config["x"][1]),
                      float(region_config["xy"][0]), 0.01, key=f"region_x_{preset['kind']}_{region}",
                      help=f"{region_config['label']}在MuJoCo桌面上的X坐标范围。")
        y = c2.slider("区域内 Y / m", float(region_config["y"][0]), float(region_config["y"][1]),
                      float(region_config["xy"][1]), 0.01, key=f"region_y_{preset['kind']}_{region}",
                      help=f"{region_config['label']}在MuJoCo桌面上的Y坐标范围。")
        st.caption(f"区域边界：X={region_config['x'][0]:.2f}～{region_config['x'][1]:.2f} m，"
                   f"Y={region_config['y'][0]:.2f}～{region_config['y'][1]:.2f} m；当前坐标：({x:.2f}, {y:.2f}) m")
        coordinate_ok = point_in_region(x, y, region)
        st.code(f"PDDL 初始状态：(at {safe_symbol(name)} {region})\n"
                f"MuJoCo 坐标：({x:.2f}, {y:.2f}) m "
                f"{'✓ 位于该区域内' if coordinate_ok else '✗ 不在该区域内'}", language="text")
    with st.container(key="tour-add"):
        if st.button("➕ 添加物体", type="primary", width="stretch"):
            symbol = safe_symbol(name)
            if any(item["name"] == symbol for item in st.session_state["items"]):
                st.error("物体名称已经存在。")
            elif not coordinate_ok:
                st.error("当前坐标不属于所选初始区域，不能添加物体。")
            elif any(abs(x - other["position"][0]) < preset["size"][0] + other["size"][0] + 0.025
                     and abs(y - other["position"][1]) < preset["size"][1] + other["size"][1] + 0.025
                     for other in st.session_state["items"]):
                st.error("该坐标与已有物体过近，请在推荐范围内调整 X 或 Y。")
            else:
                z = 0.07 + preset["size"][2] + 0.002
                st.session_state["items"].append({"name": symbol, "label": preset_name, "preset": preset_name,
                    "kind": preset["kind"], "size": preset["size"], "rgba": preset["rgba"],
                    "position": (x, y, z), "location": region})
                invalidate_after_scene_change()
                st.success(f"已添加 {symbol}")

with right, st.container(key="tour-scene"):
    st.subheader("当前场景")
    with st.expander("固定检修设施（系统预置）"):
        st.dataframe([{"颜色区域": f"{STATIONS[x['station']]['color']}区域", "工位": STATIONS[x["station"]]["label"],
                       "设施": x["label"], "作用": x["kind"], "X": x["position"][0],
                       "Y": x["position"][1], "Z": x["position"][2]} for x in FACILITIES.values()],
                     hide_index=True, width="stretch")
        st.caption("　｜　".join(f"{station['color']}区域是{station['label']}" for station in STATIONS.values()))
    if not st.session_state["items"]:
        st.info("当前场景为空。请在左侧选择一种强电检修对象并点击“添加物体”。")
    st.dataframe([{"名称": x["name"], "类型": x["label"],
        "初始区域": REGIONS.get(x["location"], {}).get("label", x["location"]),
        "坐标识别区域": REGIONS.get(region_for_point(x["position"][0], x["position"][1]) or "", {}).get("label", "区域外"),
        "匹配": "✓" if region_for_point(x["position"][0], x["position"][1]) == x["location"] else "✗",
        "X": x["position"][0], "Y": x["position"][1], "Z": x["position"][2]}
        for x in st.session_state["items"]], width="stretch", hide_index=True)
    if st.session_state["items"]:
        selected = st.selectbox("选择要删除的物体", [x["name"] for x in st.session_state["items"]])
        if st.button("删除所选物体"):
            st.session_state["items"] = [x for x in st.session_state["items"] if x["name"] != selected]
            invalidate_after_scene_change()
            st.rerun()
    try:
        sim = RobotSimulation(st.session_state["items"], active_station=facility["station"],
                              active_region=region, active_facility=profile["facility"])
        with st.expander("观察视角", expanded=False):
            camera = camera_controls("scene_camera")
            show_joints = st.toggle("显示左右臂关节标注", key="scene_show_joints",
                                    help="共享机身固定；左右臂分别为6DOF。")
            st.caption("q1肩部水平旋转｜q2肩部俯仰｜q3肘部俯仰｜q4前臂滚转｜q5腕部俯仰｜q6工具轴旋转")
        st.image(sim.render(camera, show_joints), caption=f"当前高亮语义区域：{region_config['color']}{region_config['label']}", width="stretch")
        st.caption("工位：蓝色是拆装工位｜灰色是模块检修工位｜橙色是检测操作工位｜黄色是绝缘防护工位｜紫蓝色是剥线接线协作工位")
        st.caption("语义区域：青色检修区｜紫色备件区｜绿色工具区｜白色安全区｜红色回收区；当前选择的区域会加亮。")
    except Exception as exc:
        st.warning(f"当前会话无法创建图形预览：{exc}")

with st.container(key="tour-next"):
    st.divider()
    nav("app.py", "pages/2_PDDL规划.py")

