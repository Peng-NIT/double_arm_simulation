"""Cross-page Streamlit state and navigation helpers."""

from __future__ import annotations

from html import escape
import hmac
import os
from textwrap import dedent
import streamlit as st


DEFAULT_APP_USERNAME = "admin"
DEFAULT_APP_PASSWORD = "admin_123qwe"


def _configured_credential(name: str, default: str) -> str:
    """Read deployment secrets first, then environment variables, then a local default."""
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        value = None
    return str(value or os.getenv(name) or default)


def credentials_are_valid(username: str, password: str) -> bool:
    """Compare credentials without leaking which field was incorrect."""
    expected_username = _configured_credential("APP_USERNAME", DEFAULT_APP_USERNAME)
    expected_password = _configured_credential("APP_PASSWORD", DEFAULT_APP_PASSWORD)
    return (
        hmac.compare_digest(str(username), expected_username)
        & hmac.compare_digest(str(password), expected_password)
    )


def require_login() -> None:
    """Protect every page in the multipage experiment and render the login screen."""
    st.session_state.setdefault("authenticated", False)

    if st.session_state["authenticated"]:
        # Explicitly restore navigation after the login-only CSS has been removed on rerun.
        # This also avoids a hidden sidebar during Streamlit hot reloads.
        st.markdown(
            dedent("""\
            <style>
            [data-testid="stSidebar"] {display:flex !important;}
            [data-testid="stSidebarNav"] {display:block !important;}
            </style>
            """).strip(),
            unsafe_allow_html=True,
        )
        with st.sidebar:
            st.caption(f"已登录：{st.session_state.get('authenticated_user', '实验用户')}")
            if st.button("退出登录", key="global_logout", width="stretch"):
                reset_experiment()
                st.session_state["authenticated"] = False
                st.session_state.pop("authenticated_user", None)
                st.session_state.pop("login_username", None)
                st.session_state.pop("login_password", None)
                st.switch_page("app.py")
        return

    st.markdown(
        dedent("""\
        <style>
        [data-testid="stSidebar"], [data-testid="stSidebarNav"] {display:none !important;}
        [data-testid="stAppViewContainer"] {
          background:
            radial-gradient(circle at 15% 12%, rgba(30,112,146,.10), transparent 30rem),
            linear-gradient(145deg, #f8fbfc 0%, #edf4f6 100%);
        }
        [data-testid="stMainBlockContainer"] {max-width:38rem;padding-top:8vh;}
        .login-brand {text-align:center;margin:0 auto 1.8rem;}
        .login-mark {display:inline-grid;place-items:center;width:3.4rem;height:3.4rem;
          border-radius:1rem;background:#176f91;color:#fff;font-size:1.55rem;
          box-shadow:0 12px 30px rgba(23,111,145,.22);}
        .login-brand h1 {font-size:1.75rem;letter-spacing:.01em;margin:.9rem 0 .3rem;color:#18333f;}
        .login-brand p {color:#637780;margin:0;font-size:.95rem;}
        [data-testid="stForm"] {background:rgba(255,255,255,.94);padding:1.7rem 1.8rem 1.4rem;
          border:1px solid #d8e3e7;border-radius:1rem;box-shadow:0 18px 48px rgba(25,53,64,.10);}
        </style>
        <div class="login-brand">
          <div class="login-mark">⚡</div>
          <h1>大语言模型驱动的电力系统维修机械臂虚拟仿真实验</h1>
          <p>双臂协作 · PDDL 规划 · MuJoCo 仿真</p>
        </div>
        """).strip(),
        unsafe_allow_html=True,
    )
    with st.form("login_form", clear_on_submit=False):
        st.markdown("### 用户登录")
        username = st.text_input(
            "用户名", placeholder="请输入用户名", autocomplete="username", key="login_username"
        )
        password = st.text_input(
            "密码", type="password", placeholder="请输入密码", autocomplete="current-password",
            key="login_password",
        )
        submitted = st.form_submit_button("登录并进入实验", type="primary", width="stretch")
    st.caption("本平台仅用于课程教学与虚拟仿真实验。")

    if submitted:
        if credentials_are_valid(username.strip(), password):
            st.session_state["authenticated"] = True
            st.session_state["authenticated_user"] = username.strip()
            st.rerun()
        else:
            st.error("用户名或密码错误，请重新输入。")
    st.stop()


def init_state() -> None:
    defaults = {
        "items": [],
        "intent": None,
        "problem": "",
        "plan": [],
        "execution_arm": None,
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
        "items", "intent", "problem", "plan", "execution_arm", "waypoints", "run_result", "motion",
        "learning_hint", "deep_explanation_html", "deep_explanation_text",
        "motion_explanation_html", "motion_explanation_text", "waypoint_overrides", "custom_q",
        "_motion_geometry_signature", "camera",
        "scene_tour_active", "scene_tour_step",
    ]:
        st.session_state.pop(key, None)
    init_state()


def invalidate_after_scene_change() -> None:
    """Discard outputs that no longer match the current scene."""
    for key, value in {
        "intent": None, "problem": "", "plan": [], "execution_arm": None,
        "waypoints": [], "run_result": None,
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


def spotlight_tour(steps: list[dict]) -> None:
    """Render a dependency-free spotlight tour for stable keyed containers."""
    st.session_state.setdefault("scene_tour_active", False)
    st.session_state.setdefault("scene_tour_step", 0)
    launch, note = st.columns([1, 4])
    if launch.button("◉ 打开新手引导", width="stretch"):
        st.session_state["scene_tour_active"] = True
        st.session_state["scene_tour_step"] = 0
        st.rerun()
    note.caption("仅在场景配置页显示；可逐项查看、跳过当前项或随时退出。")
    if not st.session_state["scene_tour_active"] or not steps:
        return
    index = min(int(st.session_state["scene_tour_step"]), len(steps) - 1)
    step = steps[index]
    target = step["target"]
    st.markdown(
        f"""<style>
        .st-key-{target}{{position:relative!important;z-index:1001!important;
          border-radius:.8rem;background:var(--background-color);
          box-shadow:0 0 0 4px #1f7898,0 0 0 9999px rgba(18,31,38,.66)!important;
          transition:box-shadow .25s ease}}
        .st-key-scene-tour-card{{position:fixed!important;right:2rem;bottom:1.6rem;
          width:min(28rem,calc(100vw - 2rem));z-index:1003!important;background:#fff;
          color:#1f3037;padding:1rem 1.1rem;border:1px solid #bfd0d7;border-radius:.9rem;
          box-shadow:0 18px 55px rgba(9,27,36,.28)}}
        @media(max-width:760px){{.st-key-scene-tour-card{{right:1rem;bottom:.8rem}}}}
        </style>""",
        unsafe_allow_html=True,
    )
    with st.container(key="scene-tour-card"):
        st.caption(f"新手引导　{index + 1}/{len(steps)}")
        st.markdown(f"#### {step['title']}")
        st.write(step["body"])
        previous, following, skip, close = st.columns(4)
        if previous.button("上一步", disabled=index == 0, key=f"tour_prev_{index}"):
            st.session_state["scene_tour_step"] = index - 1
            st.rerun()
        if following.button("下一步", key=f"tour_next_{index}"):
            if index + 1 >= len(steps):
                st.session_state["scene_tour_active"] = False
            else:
                st.session_state["scene_tour_step"] = index + 1
            st.rerun()
        if skip.button("跳过当前", key=f"tour_skip_{index}"):
            if index + 1 >= len(steps):
                st.session_state["scene_tour_active"] = False
            else:
                st.session_state["scene_tour_step"] = index + 1
            st.rerun()
        if close.button("退出引导", key=f"tour_close_{index}"):
            st.session_state["scene_tour_active"] = False
            st.rerun()


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
    focus_points = {"整体实验台": [0.49, 0.0, 0.22], "双臂机器人": [0.30, 0.0, 0.30],
                    "左臂": [0.30, 0.30, 0.30], "右臂": [0.30, -0.30, 0.30]}
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
