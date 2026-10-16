import streamlit as st

from lab_state import init_state, reset_experiment

st.set_page_config(page_title="强电检修机械臂实验", page_icon="⚡", layout="wide")
init_state()

st.title("⚡ 强电检修 6DOF 机械臂仿真实验")
st.caption("自然语言 → PDDL → 专用操作模板 → 6DOF 参数 → MuJoCo → 轨迹分析")
st.warning("本程序仅用于课程仿真，不构成真实带电检修的安全方案或控制系统。")

st.subheader("实验流程")
cols = st.columns(5)
steps = [
    ("① 场景配置", "添加电气部件，理解区域与坐标。"),
    ("② PDDL 规划", "生成、阅读并修改符号任务。"),
    ("③ 运动参数", "理解专用操作模板和 6DOF 参数。"),
    ("④ 仿真执行", "在 MuJoCo 中执行计划。"),
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
