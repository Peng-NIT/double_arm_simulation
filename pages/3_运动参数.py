import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from html_explainer import render_explanation
from lab_config import FACILITIES, PRESETS, TARGETS, TASK_PROFILES
from lab_state import camera_controls, help_heading, nav, page_header
from llm_client import generate_deep_explanation
from robot_sim import HOME_Q, TEACHING_JOINT_LIMITS, RobotSimulation, waypoints_from_plan


def waypoint_key(index, waypoint):
    return f"{index}:{waypoint.pddl_action}:{waypoint.label}"


st.set_page_config(page_title="3 运动参数", page_icon="⚡", layout="wide")
page_header(3, "3. 专用操作模板与 6DOF 参数")

if not st.session_state["plan"]:
    st.warning("请先在 PDDL 页面生成动作计划。")
else:
    item_name = st.session_state["plan"][0]["args"][0]
    item = next(x for x in st.session_state["items"] if x["name"] == item_name)
    preset = PRESETS.get(item.get("preset", item.get("label")), PRESETS["熔断器"])
    with st.container(border=True):
        st.markdown(f"#### {item['label']}：{preset['operation']}")
        st.write(preset["guidance"])
        st.caption(f"采用专用模板的原因：{preset['risk']}")

    help_heading("A. 轨迹参数", "这些参数将 PDDL 离散动作展开为可连续执行的末端路点。")
    motion = st.session_state["motion"]
    c1, c2, c3 = st.columns(3)
    motion["safe_z"] = c1.slider("安全高度 Z / m", 0.48, 0.56, float(motion["safe_z"]), 0.01,
        help="搬运阶段的末端高度。过低可能碰到工作台或部件，过高会增加路径长度。")
    motion["grasp_offset"] = c2.slider("抓取高度偏移 / m", 0.075, 0.090, float(motion["grasp_offset"]), 0.005,
        help="末端中心相对物体中心的垂向偏移，用于让夹爪对准物体。")
    motion["approach_distance"] = c3.slider("轴向接近距离 / m", 0.08, 0.14, float(motion["approach_distance"]), 0.01,
        help="熔断器、端子和断路器沿安装方向进入或退出的直线距离。")
    c4, c5, c6 = st.columns(3)
    motion["trajectory_frames"] = c4.slider("每段插值点数", 24, 50, int(motion["trajectory_frames"]), 2,
        help="点数越多，轨迹更细密，但播放和安全检查时间也更长。")
    speed_options = [0.5, 0.75, 1.0, 1.25, 1.5]
    old_speed = float(motion.get("speed", 1.0))
    old_speed = min(speed_options, key=lambda x: abs(x - old_speed))
    motion["speed"] = c5.select_slider("仿真播放速度", speed_options, value=old_speed,
        format_func=lambda x: f"{x:g}×", help="真正控制每帧之间的等待时间，而不是简单跳帧。")
    motion["interpolation"] = c6.selectbox("插值方式", ["平滑插值", "线性插值"],
        index=0 if motion["interpolation"] == "平滑插值" else 1,
        help="平滑插值在起止位置减速；线性插值便于观察匀速的关节变化。")
    st.session_state["motion"] = motion

    geometry_signature = (motion["safe_z"], motion["grasp_offset"], motion["approach_distance"])
    if st.session_state.get("_motion_geometry_signature") not in (None, geometry_signature):
        st.session_state["waypoint_overrides"] = {}
        st.session_state["custom_q"] = {}
        st.session_state["run_result"] = None
        st.session_state["motion_explanation_html"] = ""
        st.session_state["motion_explanation_text"] = ""
    st.session_state["_motion_geometry_signature"] = geometry_signature

    warnings = []
    if motion["safe_z"] < 0.50:
        warnings.append("安全高度接近下限；场景物体较高时建议使用 0.52 m。")
    if item["kind"] in {"fuse", "terminal", "breaker"} and motion["approach_distance"] < 0.10:
        warnings.append("插装类部件建议使用至少 0.10 m 的轴向距离。")
    for warning in warnings:
        st.warning(warning)
    if not warnings:
        st.success("当前参数处于推荐教学范围。")

    waypoints = waypoints_from_plan(st.session_state["plan"], st.session_state["items"], TARGETS, motion)
    for index, waypoint in enumerate(waypoints):
        key = waypoint_key(index, waypoint)
        if key in st.session_state["waypoint_overrides"]:
            waypoint.position = np.array(st.session_state["waypoint_overrides"][key], dtype=float)
    st.session_state["waypoints"] = waypoints

    help_heading("B. 选择路点并修改末端位置", "XYZ 是连续工作空间坐标；保存后会重新求解 IK 并用于仿真。")
    selected_index = st.selectbox("运动子步骤", range(len(waypoints)),
        format_func=lambda i: f"{i + 1}. {waypoints[i].pddl_action} → {waypoints[i].label}")
    waypoint = waypoints[selected_index]
    stable_key = waypoint_key(selected_index, waypoint)
    px, py, pz = map(float, waypoint.position)
    p1, p2, p3 = st.columns(3)
    new_x = p1.number_input("目标 X / m", 0.24, 0.74, px, 0.01, help="机械臂前后方向；范围受教学工作空间限制。")
    new_y = p2.number_input("目标 Y / m", -0.32, 0.32, py, 0.01, help="机械臂左右方向。")
    new_z = p3.number_input("目标 Z / m", 0.15, 0.60, pz, 0.01, help="末端高度；过低可能与工作台碰撞。")
    candidate_position = np.array([new_x, new_y, new_z])
    save_pos, reset_pos = st.columns(2)
    if save_pos.button("保存当前路点", width="stretch"):
        st.session_state["waypoint_overrides"][stable_key] = candidate_position.tolist()
        st.session_state["custom_q"].pop(stable_key, None)
        st.session_state["run_result"] = None
        waypoint.position = candidate_position
        st.success("路点已保存，对应关节角需要重新确认。")
    if reset_pos.button("恢复该路点推荐值", width="stretch"):
        st.session_state["waypoint_overrides"].pop(stable_key, None)
        st.session_state["custom_q"].pop(stable_key, None)
        st.session_state["run_result"] = None
        st.rerun()

    active_facility = FACILITIES[TASK_PROFILES[item["kind"]]["facility"]]
    sim = RobotSimulation(st.session_state["items"], active_station=active_facility["station"],
                          active_region=item["location"])
    try:
        q_target = sim.solve_ik(candidate_position, HOME_Q)
        st.success("IK 求解成功。下面可进一步修改六个关节角。")
        custom_q = np.asarray(st.session_state["custom_q"].get(stable_key, q_target.tolist()))
        custom_q = np.clip(custom_q, TEACHING_JOINT_LIMITS[:, 0], TEACHING_JOINT_LIMITS[:, 1])
        joint_cols = st.columns(3)
        joint_names = ["q1 底座", "q2 肩", "q3 肘", "q4 腕旋转", "q5 腕俯仰", "q6 末端旋转"]
        joint_help = [
            "底座水平旋转；改变左右作业方向。过度侧转会使机械臂靠近工作台边缘。",
            "大臂俯仰；降低会让机械臂靠近桌面，是穿模风险最高的参数之一。",
            "小臂展开程度；与 q2 共同决定末端高度和伸展距离。",
            "腕部滚转；改变夹爪侧向姿态，过大会增加腕部自碰撞风险。",
            "腕部俯仰；影响夹爪朝向及物体是否保持竖直或水平。",
            "夹爪绕工具轴旋转；主要改变工具朝向，不应替代末端位置规划。",
        ]
        local_delta = np.array([0.28, 0.22, 0.24, 0.35, 0.28, 0.45])
        edited_q = []
        for i, label in enumerate(joint_names):
            lo = max(float(TEACHING_JOINT_LIMITS[i, 0]), float(q_target[i] - local_delta[i]))
            hi = min(float(TEACHING_JOINT_LIMITS[i, 1]), float(q_target[i] + local_delta[i]))
            custom_q[i] = np.clip(custom_q[i], lo, hi)
            edited_q.append(joint_cols[i % 3].slider(label, lo, hi, float(custom_q[i]), 0.01, help=joint_help[i]))
        edited_q_array = np.array(edited_q)
        sim.step_to(edited_q_array)
        ee = sim.ee_position()
        st.write(f"修改后的末端位置：X={ee[0]:.3f}，Y={ee[1]:.3f}，Z={ee[2]:.3f} m")
        safety_issues = sim.validate_q(edited_q_array)
        # Validate the incoming and outgoing segments, not only the endpoint.
        previous_q = HOME_Q.copy()
        for prior_index, prior_waypoint in enumerate(waypoints[:selected_index]):
            prior_key = waypoint_key(prior_index, prior_waypoint)
            previous_q = (np.asarray(st.session_state["custom_q"][prior_key], dtype=float)
                          if prior_key in st.session_state["custom_q"]
                          else sim.solve_ik(prior_waypoint.position, previous_q))
        safety_issues.extend(sim.validate_path(previous_q, edited_q_array, 24))
        if selected_index + 1 < len(waypoints):
            next_waypoint = waypoints[selected_index + 1]
            next_key = waypoint_key(selected_index + 1, next_waypoint)
            try:
                next_q = (np.asarray(st.session_state["custom_q"][next_key], dtype=float)
                          if next_key in st.session_state["custom_q"]
                          else sim.solve_ik(next_waypoint.position, edited_q_array))
                safety_issues.extend(sim.validate_path(edited_q_array, next_q, 24))
            except Exception as exc:
                safety_issues.append(f"下一段轨迹无法生成：{exc}")
        safety_issues = list(dict.fromkeys(safety_issues))
        # Path validation mutates MuJoCo state; restore the pose being previewed.
        sim.step_to(edited_q_array)
        for issue in safety_issues:
            st.error(issue)
        save_joint, restore_joint = st.columns(2)
        if save_joint.button("保存当前关节参数到该路点", disabled=bool(safety_issues), width="stretch"):
            st.session_state["custom_q"][stable_key] = edited_q
            st.session_state["run_result"] = None
            st.success("已保存，仿真页面将使用这组六关节角。")
        if restore_joint.button("恢复推荐关节姿态", width="stretch"):
            st.session_state["custom_q"].pop(stable_key, None)
            st.session_state["run_result"] = None
            st.rerun()
        try:
            with st.expander("观察视角", expanded=False):
                camera = camera_controls("motion_camera")
            st.image(sim.render(camera), caption="当前六关节姿态预览", width="stretch")
        except Exception:
            pass
    except Exception as exc:
        st.error(f"IK 无解：{exc}")

    st.divider()
    help_heading("AI 运动参数深度解读", "解释 PDDL 动作如何展开为路点和 q1–q6，以及参数变化的因果影响。", 3)
    explain_left, explain_right = st.columns([1, 1.7])
    with explain_left:
        motion_question = st.text_input("运动参数提问（可选）", placeholder="例如：安全高度降低会带来什么影响？")
        if st.button("✦ 生成运动参数深度解读", type="primary", width="stretch"):
            waypoint_rows = "\n".join(f"{i+1}. {w.pddl_action} -> {w.label}: {np.round(w.position, 3).tolist()}"
                                      for i, w in enumerate(waypoints))
            context = (f"对象：{item['label']} / {item['kind']}\n专用操作：{preset['operation']}\n"
                       f"参数：{motion}\n路点：\n{waypoint_rows}\n关节安全范围：{TEACHING_JOINT_LIMITS.tolist()}")
            try:
                with st.status("正在分析路点和 6DOF 参数…", expanded=True) as status:
                    draft = generate_deep_explanation("6DOF 运动规划与参数", context, motion_question)
                    st.session_state["motion_explanation_text"] = draft
                    st.write("正在组织参数因果与风险判读…")
                    st.session_state["motion_explanation_html"] = render_explanation(draft)
                    status.update(label="运动参数解读已生成", state="complete", expanded=False)
            except Exception as exc:
                st.error(f"可视化解读生成失败：{exc}")
    with explain_right:
        if st.session_state.get("motion_explanation_html"):
            components.html(st.session_state["motion_explanation_html"], height=720, scrolling=True)
        elif st.session_state.get("motion_explanation_text"):
            st.markdown(st.session_state["motion_explanation_text"])
        else:
            st.info("生成后，这里将显示路点、关节角和安全参数的结构化讲解。")

st.divider()
nav("pages/2_PDDL规划.py", "pages/4_仿真执行.py")
