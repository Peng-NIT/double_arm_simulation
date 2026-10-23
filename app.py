import streamlit as st

from lab_state import init_state, require_login, reset_experiment

st.set_page_config(page_title="强电检修机器人实验", page_icon="⚡", layout="wide")
require_login()
init_state()

st.title("⚡ 大语言模型驱动的电力系统维修机器人虚拟仿真实验")
st.caption("自然语言 → PDDL任务分配 → 单/双臂6DOF规划 → MuJoCo仿真 → 轨迹分析")
st.warning("本程序仅用于课程仿真，不构成真实带电检修的安全方案或控制系统。")

st.subheader("实验流程")
cols = st.columns(5)
steps = [
    ("① 场景配置", "添加电气部件，理解区域与坐标。"),
    ("② PDDL 规划", "生成、阅读并修改符号任务。"),
    ("③ 运动参数", "理解左右臂分工和各自6DOF参数。"),
    ("④ 仿真执行", "在 MuJoCo 中执行单臂或双臂协作计划。"),
    ("⑤ 结果分析", "比较关节和末端轨迹。"),
]
for col, (name, description) in zip(cols, steps):
    col.markdown(f"**{name}**")
    col.caption(description)

st.divider()
left, right = st.columns([2, 1])
with left:
    st.info("实验从空场景开始。推荐先添加一个熔断器，再输入“将熔断器放入回收区”。")
    if st.button("开始实验 →", type="primary", width="stretch"):
        st.switch_page("pages/1_场景配置.py")
with right:
    if st.button("清空并重新开始", width="stretch"):
        reset_experiment()
        st.rerun()
