import numpy as np
import streamlit as st

from lab_config import PRESETS, TARGETS
from lab_state import nav, page_header
from robot_sim import HOME_Q, TEACHING_JOINT_LIMITS, RobotSimulation, waypoints_from_plan

st.set_page_config(page_title="3 运动参数", page_icon="⚡", layout="wide")
page_header(3, "3. 专用操作模板与 6DOF 参数")

if not st.session_state["plan"]:
    st.warning("请先在 PDDL 页面生成动作计划。")
else:
    item_name = st.session_state["plan"][0]["args"][0]
    item = next(x for x in st.session_state["items"] if x["name"] == item_name)
    preset = PRESETS.get(item.get("preset", item.get("label")), PRESETS.get("熔断器"))
    with st.container(border=True):
        st.markdown(f"#### {item['label']}：{preset['operation']}")
        st.write(preset["guidance"])
        st.caption(f"采用专用模板的原因：{preset['risk']}")

    st.markdown("#### A. 轨迹参数")
    c1, c2, c3 = st.columns(3)
    motion = st.session_state["motion"]
    motion["safe_z"] = c1.slider("安全高度 Z / m", 0.48, 0.56, float(motion["safe_z"]), 0.01)
    motion["grasp_offset"] = c2.slider("抓取高度偏移 / m", 0.075, 0.090, float(motion["grasp_offset"]), 0.005)
    motion["approach_distance"] = c3.slider("轴向接近距离 / m", 0.08, 0.14, float(motion["approach_distance"]), 0.01)
    c4, c5, c6 = st.columns(3)
    motion["trajectory_frames"] = c4.slider("每段插值点数", 24, 50, int(motion["trajectory_frames"]), 2)
    motion["speed"] = c5.slider("播放速度", 1, 4, int(motion["speed"]))
    motion["interpolation"] = c6.selectbox("插值方式", ["平滑插值", "线性插值"],
        index=0 if motion["interpolation"] == "平滑插值" else 1)
    st.session_state["motion"] = motion

    warnings = []
    if motion["safe_z"] < 0.50:
        warnings.append("安全高度接近下限；场景物体较高时建议使用 0.52 m。")
    if item["kind"] in {"fuse", "terminal", "breaker"} and motion["approach_distance"] < 0.10:
        warnings.append("插装类部件建议使用至少 0.10 m 的轴向距离。")
    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("当前参数处于推荐教学范围。")

    waypoints = waypoints_from_plan(st.session_state["plan"], st.session_state["items"], TARGETS, motion)
    st.session_state["waypoints"] = waypoints
    st.markdown("#### B. 选择路点并修改末端位置")
    selected_index = st.selectbox("运动子步骤", range(len(waypoints)),
        format_func=lambda i: f"{i + 1}. {waypoints[i].pddl_action} → {waypoints[i].label}")
    waypoint = waypoints[selected_index]
    px, py, pz = map(float, waypoint.position)
    p1, p2, p3 = st.columns(3)
    new_x = p1.number_input("目标 X / m", 0.24, 0.74, px, 0.01)
    new_y = p2.number_input("目标 Y / m", -0.32, 0.32, py, 0.01)
    new_z = p3.number_input("目标 Z / m", 0.15, 0.60, pz, 0.01)
    waypoint.position = np.array([new_x, new_y, new_z])

    sim = RobotSimulation(st.session_state["items"])
    try:
        q_target = sim.solve_ik(waypoint.position, HOME_Q)
        st.success("IK 求解成功。下面可进一步修改六个关节角。")
        custom_q = np.asarray(st.session_state.setdefault("custom_q", {}).get(selected_index, q_target.tolist()))
        custom_q = np.clip(custom_q, TEACHING_JOINT_LIMITS[:, 0], TEACHING_JOINT_LIMITS[:, 1])
        joint_cols = st.columns(3)
        edited_q = []
        joint_names = ["q1 底座", "q2 肩", "q3 肘", "q4 腕旋转", "q5 腕俯仰", "q6 末端旋转"]
        for i, label in enumerate(joint_names):
            lo, hi = map(float, TEACHING_JOINT_LIMITS[i])
            edited_q.append(joint_cols[i % 3].slider(label, lo, hi, float(custom_q[i]), 0.01))
        sim.step_to(np.array(edited_q))
        ee = sim.ee_position()
        st.write(f"修改后的末端位置：X={ee[0]:.3f}，Y={ee[1]:.3f}，Z={ee[2]:.3f} m")
        safety_issues = sim.validate_q(np.array(edited_q))
        for issue in safety_issues:
            st.error(issue)
        if st.button("保存当前关节参数到该路点", disabled=bool(safety_issues)):
            st.session_state.setdefault("custom_q", {})[selected_index] = edited_q
            st.success("已保存，仿真页面将使用这组六关节角。")
        try:
            st.image(sim.render(), caption="当前六关节姿态预览", width="stretch")
        except Exception:
            pass
    except Exception as exc:
        st.error(f"IK 无解：{exc}")

st.divider()
nav("pages/2_PDDL规划.py", "pages/4_仿真执行.py")

