import streamlit as st

from lab_state import init_state, require_login, reset_experiment
from webgl_home import render_orientation_scene

st.set_page_config(page_title="强电检修机器人实验", page_icon="⚡", layout="wide")
require_login()
init_state()

st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"]{max-width:1500px;padding-top:1.8rem;padding-bottom:2rem}
    .home-head{display:flex;justify-content:space-between;align-items:end;margin:0 0 1rem}
    .home-kicker{font-size:.72rem;letter-spacing:.17em;font-weight:700;color:#55727c}
    .home-head h1{font-size:2rem;margin:.25rem 0 .2rem;color:#172f39;letter-spacing:-.02em}
    .home-head p{margin:0;color:#6c7e85;font-size:.92rem}
    .home-progress{text-align:right;color:#6c7e85;font-size:.78rem}.home-progress b{display:block;color:#173b49;font-size:1.1rem}
    div[data-testid="stButton"] button{border-radius:.75rem;font-weight:600}
    </style>
    """,
    unsafe_allow_html=True,
)

role_label = "教师" if st.session_state.get("user_role") == "teacher" else "学生"
completed = sum(bool(st.session_state.get(key)) for key in
                ("items", "problem", "waypoints", "run_result"))
st.markdown(
    f"""
    <div class="home-head">
      <div><div class="home-kicker">LIVE-WORK ROBOTICS LAB</div>
      <h1>认识实验场景，再开始规划</h1>
      <p>探索双臂机器人、教学工位和带电约束，建立从任务语义到安全运动的整体认识。</p></div>
      <div class="home-progress">当前身份 · {role_label}<b>实验进度 {completed}/4</b></div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_orientation_scene(role_label)

left, center, right = st.columns([1.6, 1, 1])
with left:
    st.caption("首页三维场景用于信息引导，与后续MuJoCo物理仿真相互独立。")
with center:
    if st.button("开始实验：配置场景 →", type="primary", width="stretch"):
        st.switch_page("pages/1_场景配置.py")
with right:
    if st.button("清空实验状态", width="stretch"):
        reset_experiment()
        st.rerun()

st.warning("本程序仅用于课程仿真，不构成真实带电检修的安全方案或控制系统。")
