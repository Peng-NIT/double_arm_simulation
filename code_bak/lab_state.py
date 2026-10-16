"""Cross-page Streamlit state and navigation helpers."""

from __future__ import annotations

import streamlit as st

from lab_config import DEFAULT_ITEMS


def init_state() -> None:
    defaults = {
        "items": [dict(item) for item in DEFAULT_ITEMS],
        "intent": None,
        "problem": "",
        "plan": [],
        "waypoints": [],
        "run_result": None,
        "motion": {
            "safe_z": 0.52,
            "grasp_offset": 0.08,
            "approach_distance": 0.10,
            "trajectory_frames": 28,
            "speed": 3,
            "interpolation": "平滑插值",
        },
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_experiment() -> None:
    for key in ["items", "intent", "problem", "plan", "waypoints", "run_result", "motion"]:
        st.session_state.pop(key, None)
    init_state()


def page_header(step: int, title: str) -> None:
    init_state()
    st.caption(f"实验进度：{step}/5　场景配置 → PDDL 规划 → 运动参数 → 仿真执行 → 结果分析")
    st.progress(step / 5)
    st.title(title)


def nav(previous: str | None, following: str | None) -> None:
    left, middle, right = st.columns([1, 3, 1])
    if previous and left.button("← 上一步", width="stretch"):
        st.switch_page(previous)
    if middle.button("重新开始实验", width="stretch"):
        reset_experiment()
        st.switch_page("app.py")
    if following and right.button("下一步 →", width="stretch"):
        st.switch_page(following)
