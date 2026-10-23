import time
import numpy as np
import streamlit as st

from lab_config import FACILITIES, TASK_PROFILES
from lab_state import camera_controls, nav, page_header, require_login
from robot_sim import HOME_QS, RobotSimulation


def waypoint_key(index, waypoint):
    return f"{index}:{waypoint.arm}:{waypoint.pddl_action}:{waypoint.label}"


def arm_label(arm):
    return "左臂" if arm == "left_arm" else "右臂"


RELEASE_ACTIONS = ("place(", "insert-component(", "seat-component(",
                   "assisted-place(", "assisted-insert(", "assisted-seat(",
                   "assisted-cover(", "assisted-mount(")


st.set_page_config(page_title="4 仿真执行", page_icon="⚡", layout="wide")
require_login()
page_header(4, "4. 双6DOF MuJoCo仿真执行")

waypoints = st.session_state["waypoints"]
if not waypoints:
    st.warning("请先在运动参数页面生成并检查路点。")
else:
    active_item = next(x for x in st.session_state["items"]
                       if x["name"] == st.session_state["intent"].item)
    active_profile = TASK_PROFILES[active_item["kind"]]
    st.info(f"当前任务对象：{active_item['label']}　｜　协作设施："
            f"{FACILITIES[active_profile['facility']]['label']}　｜　"
            f"双臂动作展开：{active_profile['pddl']}")
    st.dataframe([{
        "序号": i + 1, "执行机械臂": arm_label(w.arm), "PDDL动作": w.pddl_action,
        "运动子步骤": w.label, "X": round(w.position[0], 3), "Y": round(w.position[1], 3),
        "Z": round(w.position[2], 3), "夹爪指令": "闭合" if w.grip else "打开",
    } for i, w in enumerate(waypoints)], width="stretch", hide_index=True)
    with st.expander("聚焦、缩放与视角", expanded=True):
        camera = camera_controls("run_camera")
        show_joints = st.toggle("显示左右臂关节标注", key="run_show_joints",
                                help="显示 L-q1～L-q6 与 R-q1～R-q6。共享机身固定，不计自由度。")
        st.caption("q1肩部水平旋转｜q2肩部俯仰｜q3肘部俯仰｜q4前臂滚转｜q5腕部俯仰｜q6工具轴旋转")
    run = st.button("▶ 执行双臂完整计划", type="primary")
    frame_box = st.empty()
    status_box = st.empty()
    progress = st.progress(0)

    def new_sim():
        return RobotSimulation(st.session_state["items"],
            active_station=FACILITIES[active_profile["facility"]]["station"],
            active_region=active_item["location"], active_facility=active_profile["facility"])

    try:
        preview = new_sim()
        frame_box.image(preview.render(camera, show_joints), caption="执行前双臂预览：共享机身，左、右机械臂采用镜像布置", width="stretch")
    except Exception as exc:
        st.warning(f"图形预览不可用：{exc}")

    if run:
        try:
            sim = new_sim()
            q_current = {arm: q.copy() for arm, q in HOME_QS.items()}
            motion = st.session_state["motion"]
            frames = int(motion["trajectory_frames"])
            frame_delay = 0.035 / max(0.5, float(motion.get("speed", 1.0)))
            custom_q = st.session_state.get("custom_q", {})

            # Validate the complete alternating dual-arm trajectory first.
            for wi, waypoint in enumerate(waypoints):
                arm = waypoint.arm
                other = "right_arm" if arm == "left_arm" else "left_arm"
                key = waypoint_key(wi, waypoint)
                target_q = (np.asarray(custom_q[key], dtype=float) if key in custom_q else
                            waypoint.joint_target.copy() if waypoint.joint_target is not None else
                            sim.solve_ik(waypoint.position, q_current[arm], arm, q_current[other]))
                path = sim.interpolate(q_current[arm], target_q, frames)
                if motion["interpolation"] == "线性插值":
                    path = np.linspace(q_current[arm], target_q, frames)
                for q_check in path:
                    issues = sim.validate_q(q_check, arm, q_current[other])
                    if issues:
                        raise ValueError(f"第 {wi + 1} 步 {arm_label(arm)} 未通过安全检查：{issues[0]}")
                sim.step_to(target_q, arm)
                if (waypoint.pddl_action.startswith(("pick(", "assisted-pick("))
                        and waypoint.grip and sim.grabbed[arm] is None):
                    sim.set_grab(active_item["name"], arm)
                if (waypoint.pddl_action.startswith(RELEASE_ACTIONS)
                        and not waypoint.grip and sim.grabbed[arm] is not None):
                    sim.set_grab(None, arm)
                q_current[arm] = target_q

            sim = new_sim()
            q_current = {arm: q.copy() for arm, q in HOME_QS.items()}
            q_log = {"left_arm": [], "right_arm": []}
            xyz_log = {"left_arm": [], "right_arm": []}
            labels = []
            held_name = active_item["name"]
            for wi, waypoint in enumerate(waypoints):
                arm = waypoint.arm
                other = "right_arm" if arm == "left_arm" else "left_arm"
                status_box.info(f"{arm_label(arm)}｜{waypoint.pddl_action} → {waypoint.label}")
                key = waypoint_key(wi, waypoint)
                q_target = (np.asarray(custom_q[key], dtype=float) if key in custom_q else
                            waypoint.joint_target.copy() if waypoint.joint_target is not None else
                            sim.solve_ik(waypoint.position, q_current[arm], arm, q_current[other]))
                trajectory = sim.interpolate(q_current[arm], q_target, frames)
                if motion["interpolation"] == "线性插值":
                    trajectory = np.linspace(q_current[arm], q_target, frames)
                for fi, q in enumerate(trajectory):
                    sim.step_to(q, arm)
                    for log_arm in HOME_QS:
                        q_log[log_arm].append(sim.arm_q(log_arm))
                        xyz_log[log_arm].append(sim.ee_position(log_arm))
                    labels.append(f"{arm}:{waypoint.pddl_action}")
                    if fi % 2 == 0 or fi == len(trajectory) - 1:
                        frame_box.image(sim.render(camera, show_joints),
                            caption=f"{arm_label(arm)}｜{waypoint.pddl_action} / {waypoint.label}", width="stretch")
                    time.sleep(frame_delay)
                if (waypoint.pddl_action.startswith(("pick(", "assisted-pick("))
                        and waypoint.grip and sim.grabbed[arm] is None):
                    sim.set_grab(held_name, arm)
                if (waypoint.pddl_action.startswith(RELEASE_ACTIONS)
                        and not waypoint.grip and sim.grabbed[arm] is not None):
                    sim.set_grab(None, arm)
                q_current[arm] = q_target
                progress.progress((wi + 1) / len(waypoints))

            for arm in HOME_QS:
                for fi, q in enumerate(sim.interpolate(q_current[arm], HOME_QS[arm], frames)):
                    sim.step_to(q, arm)
                    for log_arm in HOME_QS:
                        q_log[log_arm].append(sim.arm_q(log_arm))
                        xyz_log[log_arm].append(sim.ee_position(log_arm))
                    labels.append(f"{arm}:return-home")
                    if fi % 2 == 0:
                        frame_box.image(sim.render(camera, show_joints), caption=f"{arm_label(arm)}返回Home", width="stretch")
            final_positions = {item["name"]: sim.data.qpos[sim.object_qadr[item["name"]]:
                                                         sim.object_qadr[item["name"]] + 3].copy()
                               for item in st.session_state["items"]}
            st.session_state["run_result"] = {
                "q_left": np.asarray(q_log["left_arm"]), "q_right": np.asarray(q_log["right_arm"]),
                "xyz_left": np.asarray(xyz_log["left_arm"]), "xyz_right": np.asarray(xyz_log["right_arm"]),
                "labels": labels, "final_positions": final_positions, "dt": frame_delay,
            }
            frame_box.image(sim.render(camera, show_joints), caption="任务完成：双臂已返回Home", width="stretch")
            status_box.success("双臂计划执行完成，可以进入结果分析页面。")
        except Exception as exc:
            status_box.error(f"执行停止：{exc}")

st.divider()
nav("pages/3_运动参数.py", "pages/5_结果分析.py")
