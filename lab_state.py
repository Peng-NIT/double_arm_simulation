"""Cross-page Streamlit state and navigation helpers."""

from __future__ import annotations

from html import escape
import streamlit as st


def init_state() -> None:
    defaults = {
        "items": [],
        "intent": None,
        "problem": "",
        "plan": [],
        "waypoints": [],
        "run_result": None,
        "learning_hint": "",
        "deep_explanation_html": "",
        "deep_explanation_text": "",
        "motion_explanation_html": "",
        "motion_explanation_text": "",
        "waypoint_overrides": {},
        "custom_q": {},
        "_motion_geometry_signature": None,
        "camera": {"preset": "默认全景", "azimuth": 132.0, "elevation": -30.0,
                   "distance": 1.72, "lookat": [0.49, 0.0, 0.22]},
        "motion": {
            "safe_z": 0.52,
            "grasp_offset": 0.08,
            "approach_distance": 0.10,
            "trajectory_frames": 28,
            "speed": 1.0,
            "interpolation": "平滑插值",
        },
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_experiment() -> None:
    for key in [
        "items", "intent", "problem", "plan", "waypoints", "run_result", "motion",
        "learning_hint", "deep_explanation_html", "deep_explanation_text",
        "motion_explanation_html", "motion_explanation_text", "waypoint_overrides", "custom_q",
        "_motion_geometry_signature", "camera",
    ]:
        st.session_state.pop(key, None)
    init_state()


def invalidate_after_scene_change() -> None:
    """Discard outputs that no longer match the current scene."""
    for key, value in {
        "intent": None, "problem": "", "plan": [], "waypoints": [], "run_result": None,
        "learning_hint": "", "deep_explanation_html": "", "deep_explanation_text": "",
        "motion_explanation_html": "", "motion_explanation_text": "",
        "waypoint_overrides": {}, "custom_q": {}, "_motion_geometry_signature": None,
    }.items():
        st.session_state[key] = value


def invalidate_after_plan_change() -> None:
    """Discard motion products when PDDL or its plan changes."""
    for key, value in {
        "waypoints": [], "run_result": None, "deep_explanation_html": "",
        "deep_explanation_text": "", "motion_explanation_html": "",
        "motion_explanation_text": "", "waypoint_overrides": {}, "custom_q": {},
        "_motion_geometry_signature": None,
    }.items():
        st.session_state[key] = value


def help_heading(title: str, help_text: str, level: int = 4) -> None:
    """Render a heading with an accessible circular hover hint."""
    level = min(6, max(1, int(level)))
    help_text = (help_text or "该内容用于解释本实验中的参数或规划概念。").strip()
    st.markdown(
        f'<h{level} class="lab-help-heading">{escape(title)}'
        f'<span class="lab-help" data-help="{escape(help_text, quote=True)}" '
        f'aria-label="{escape(help_text, quote=True)}">?</span></h{level}>',
        unsafe_allow_html=True,
    )


def page_header(step: int, title: str) -> None:
    init_state()
    st.markdown(
        """<style>
        .lab-help-heading{display:flex;align-items:center;gap:.5rem}
        .lab-help{display:inline-grid;place-items:center;width:1.15rem;height:1.15rem;
          border:1px solid #73828a;border-radius:50%;color:#586a73;font-size:.72rem;
          font-weight:700;cursor:help;line-height:1;background:#f7fafb}
        .lab-help:hover{border-color:#176f91;color:#176f91;background:#eaf3f7}
        .lab-help{position:relative}
        .lab-help:hover:after,.lab-help:focus:after{content:attr(data-help);position:absolute;
          left:1.5rem;top:-.45rem;z-index:9999;width:18rem;padding:.65rem .75rem;
          border:1px solid #cbd6db;border-radius:.55rem;background:#fff;color:#26363d;
          font-size:.78rem;font-weight:400;line-height:1.5;box-shadow:0 8px 24px #19313d22}
        </style>""",
        unsafe_allow_html=True,
    )
    st.caption(f"实验进度：{step}/5　场景配置 → PDDL 规划 → 运动参数 → 仿真执行 → 结果分析")
    st.progress(step / 5)
    st.title(title)


def camera_controls(key_prefix: str = "camera") -> dict:
    """Shared MuJoCo free-camera controls; changing them never resets the experiment."""
    camera = st.session_state["camera"]
    presets = {
        "默认全景": (132.0, -30.0, 1.72, [0.49, 0.0, 0.22]),
        "俯视": (90.0, -82.0, 1.60, [0.49, 0.0, 0.16]),
        "正视": (180.0, -12.0, 1.35, [0.46, 0.0, 0.25]),
        "侧视": (90.0, -18.0, 1.35, [0.46, 0.0, 0.25]),
        "末端特写": (135.0, -24.0, 0.72, [0.55, 0.0, 0.28]),
    }
    preset_key = f"{key_prefix}_preset"
    st.session_state.setdefault(preset_key, camera.get("preset", "默认全景"))
    def apply_preset() -> None:
        chosen = st.session_state[preset_key]
        azimuth, elevation, distance, lookat = presets[chosen]
        camera.update({"preset": chosen, "azimuth": azimuth, "elevation": elevation,
                       "distance": distance, "lookat": lookat})
        st.session_state[f"{key_prefix}_az"] = azimuth
        st.session_state[f"{key_prefix}_el"] = elevation
        st.session_state[f"{key_prefix}_dist"] = distance
    st.selectbox("预设视角", list(presets), key=preset_key, on_change=apply_preset,
                 help="选择常用机位；仍可继续调整方位角、俯仰角和缩放。")
    focus_points = {"整体实验台": [0.49, 0.0, 0.22], "机械臂": [0.30, 0.0, 0.30]}
    for item in st.session_state.get("items", []):
        focus_points[f"操作物体：{item['name']}"] = list(item["position"])
    from lab_config import FACILITIES
    for facility in FACILITIES.values():
        focus_points[f"固定设施：{facility['label']}"] = list(facility["position"])
    focus = st.selectbox("聚焦对象", list(focus_points), key=f"{key_prefix}_focus",
                         help="改变相机观察中心，不会改变机械臂或物体状态。")
    camera["lookat"] = focus_points[focus]
    for suffix, value in (("az", camera["azimuth"]), ("el", camera["elevation"]), ("dist", camera["distance"])):
        st.session_state.setdefault(f"{key_prefix}_{suffix}", value)
    c1, c2, c3 = st.columns(3)
    camera["azimuth"] = c1.slider("方位角 / °", min_value=0.0, max_value=360.0, step=5.0,
                                   key=f"{key_prefix}_az", help="绕实验台水平旋转观察方向。")
    camera["elevation"] = c2.slider("俯仰角 / °", min_value=-85.0, max_value=10.0, step=2.0,
                                     key=f"{key_prefix}_el", help="负值越大越接近俯视。")
    camera["distance"] = c3.slider("缩放距离 / m", min_value=0.55, max_value=2.40, step=0.05,
                                    key=f"{key_prefix}_dist", help="数值越小，画面越聚焦。")
    st.session_state["camera"] = camera
    return camera


def nav(previous: str | None, following: str | None) -> None:
    left, middle, right = st.columns([1, 3, 1])
    if previous and left.button("← 上一步", width="stretch"):
        st.switch_page(previous)
    if middle.button("重新开始实验", width="stretch"):
        reset_experiment()
        st.switch_page("app.py")
    if following and right.button("下一步 →", width="stretch"):
        st.switch_page(following)
