import time
import numpy as np
import streamlit as st

from lab_state import nav, page_header
from robot_sim import HOME_Q, RobotSimulation

st.set_page_config(page_title="4 仿真执行", page_icon="⚡", layout="wide")
page_header(4, "4. MuJoCo 仿真执行")

waypoints = st.session_state["waypoints"]
if not waypoints:
    st.warning("请先在运动参数页面生成并检查路点。")
else:
    st.dataframe([{"序号": i + 1, "PDDL动作": w.pddl_action, "运动子步骤": w.label,
        "X": round(w.position[0], 3), "Y": round(w.position[1], 3), "Z": round(w.position[2], 3),
        "夹爪": "闭合" if w.grip else "打开"} for i, w in enumerate(waypoints)], width="stretch", hide_index=True)
    run = st.button("▶ 执行完整计划", type="primary")
    frame_box = st.empty()
    status_box = st.empty()
    progress = st.progress(0)
    try:
        preview = RobotSimulation(st.session_state["items"])
        frame_box.image(preview.render(), caption="执行前预览", width="stretch")
    except Exception as exc:
        st.warning(f"图形预览不可用：{exc}")

    if run:
        try:
            sim = RobotSimulation(st.session_state["items"])
            q_current = HOME_Q.copy()
            q_log, xyz_log, labels = [], [], []
            held_name = st.session_state["plan"][0]["args"][0]
            motion = st.session_state["motion"]
            frames = int(motion["trajectory_frames"])
            custom_q = st.session_state.get("custom_q", {})
            # Validate every interpolated configuration before showing motion.
            validation_q = q_current.copy()
            for wi, waypoint in enumerate(waypoints):
                validation_target = np.array(custom_q[wi]) if wi in custom_q else sim.solve_ik(waypoint.position, validation_q)
                validation_path = sim.interpolate(validation_q, validation_target, frames)
                if motion["interpolation"] == "线性插值":
                    validation_path = np.linspace(validation_q, validation_target, frames)
                for q_check in validation_path:
                    issues = sim.validate_q(q_check)
                    if issues:
                        raise ValueError(f"第 {wi + 1} 个运动步骤未通过安全检查：{issues[0]}")
                validation_q = validation_target
            for q_check in sim.interpolate(validation_q, HOME_Q, frames):
                issues = sim.validate_q(q_check)
                if issues:
                    raise ValueError(f"返回 Home 的轨迹未通过安全检查：{issues[0]}")
            # Reset after preflight because validation moves the model state.
            sim = RobotSimulation(st.session_state["items"])
            for wi, waypoint in enumerate(waypoints):
                status_box.info(f"{waypoint.pddl_action} → {waypoint.label}")
                q_target = np.array(custom_q[wi]) if wi in custom_q else sim.solve_ik(waypoint.position, q_current)
                trajectory = sim.interpolate(q_current, q_target, frames)
                if motion["interpolation"] == "线性插值":
                    trajectory = np.linspace(q_current, q_target, frames)
                for fi, q in enumerate(trajectory):
                    sim.step_to(q)
                    q_log.append(sim.data.qpos[:6].copy())
                    xyz_log.append(sim.ee_position())
                    labels.append(waypoint.pddl_action)
                    if fi % max(1, 6 - int(motion["speed"])) == 0 or fi == len(trajectory) - 1:
                        frame_box.image(sim.render(), caption=f"{waypoint.pddl_action} / {waypoint.label}", width="stretch")
                if waypoint.grip and sim.grabbed is None:
                    sim.set_grab(held_name)
                if not waypoint.grip and sim.grabbed is not None and "松开" in waypoint.label:
                    sim.set_grab(None)
                q_current = q_target
                progress.progress((wi + 1) / len(waypoints))
                time.sleep(0.01)
            for q in sim.interpolate(q_current, HOME_Q, frames):
                sim.step_to(q); q_log.append(sim.data.qpos[:6].copy()); xyz_log.append(sim.ee_position()); labels.append("return-home")
            frame_box.image(sim.render(), caption="任务完成：已返回 Home", width="stretch")
            st.session_state["run_result"] = {"q": np.array(q_log), "xyz": np.array(xyz_log), "labels": labels}
            status_box.success("计划执行完成，可以进入结果分析页面。")
        except Exception as exc:
            status_box.error(f"执行停止：{exc}")

st.divider()
nav("pages/3_运动参数.py", "pages/5_结果分析.py")

