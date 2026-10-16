import streamlit as st

from lab_config import PRESETS, REGIONS
from lab_state import nav, page_header
from planner import safe_symbol
from robot_sim import RobotSimulation

st.set_page_config(page_title="1 场景配置", page_icon="⚡", layout="wide")
page_header(1, "1. 场景与物体配置")
st.info("初始区域是 PDDL 使用的语义位置；XYZ 是 MuJoCo 使用的连续坐标。选择区域后，系统自动采用该区域的推荐坐标。")

left, right = st.columns([1, 1.3])
with left:
    preset_name = st.selectbox("电力物体", list(PRESETS))
    preset = PRESETS[preset_name]
    with st.container(border=True):
        st.markdown(f"#### {preset_name}操作提示")
        st.write(f"**操作方式：** {preset['operation']}")
        st.write(f"**推荐方法：** {preset['guidance']}")
        st.warning(f"注意：{preset['risk']}")
    default_name = f"{preset['kind']}_{len(st.session_state['items']) + 1}"
    name = st.text_input("物体英文名称", value=default_name)
    region = st.selectbox("初始区域", list(REGIONS), index=list(REGIONS).index(preset["region"]),
                          format_func=lambda key: f"{REGIONS[key]['label']}（{key}）")
    st.caption(REGIONS[region]["help"])
    base_x, base_y = REGIONS[region]["xy"]
    c1, c2 = st.columns(2)
    dx = c1.slider("区域内 X 微调 / m", -0.06, 0.06, 0.0, 0.01)
    dy = c2.slider("区域内 Y 微调 / m", -0.06, 0.06, 0.0, 0.01)
    x, y = base_x + dx, base_y + dy
    st.write(f"实际坐标：X={x:.2f} m，Y={y:.2f} m")
    if st.button("➕ 添加物体", type="primary", width="stretch"):
        symbol = safe_symbol(name)
        if any(item["name"] == symbol for item in st.session_state["items"]):
            st.error("物体名称已经存在。")
        else:
            z = 0.07 + preset["size"][2] + 0.002
            st.session_state["items"].append({"name": symbol, "label": preset_name, "preset": preset_name,
                "kind": preset["kind"], "size": preset["size"], "rgba": preset["rgba"],
                "position": (x, y, z), "location": region})
            st.session_state["plan"] = []
            st.success(f"已添加 {symbol}")

with right:
    st.subheader("当前场景")
    st.dataframe([{"名称": x["name"], "类型": x["label"],
        "初始区域": REGIONS.get(x["location"], {}).get("label", x["location"]),
        "X": x["position"][0], "Y": x["position"][1], "Z": x["position"][2]}
        for x in st.session_state["items"]], width="stretch", hide_index=True)
    if st.session_state["items"]:
        selected = st.selectbox("选择要删除的物体", [x["name"] for x in st.session_state["items"]])
        if st.button("删除所选物体"):
            st.session_state["items"] = [x for x in st.session_state["items"] if x["name"] != selected]
            st.session_state["plan"] = []
            st.rerun()
    try:
        sim = RobotSimulation(st.session_state["items"])
        st.image(sim.render(), caption="MuJoCo 场景预览", width="stretch")
    except Exception as exc:
        st.warning(f"当前会话无法创建图形预览：{exc}")

st.divider()
nav("app.py", "pages/2_PDDL规划.py")

