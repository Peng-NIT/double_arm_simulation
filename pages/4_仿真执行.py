import time
import numpy as np
import streamlit as st

from lab_config import ERROR_DEMOS, FACILITIES, POWER_LINES, TARGETS, TASK_PROFILES
from lab_state import camera_controls, nav, page_header, require_login
from planner import make_plan
from robot_sim import HOME_QS, RobotSimulation, waypoints_from_plan


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
    demo_choices = {"不启用错误示范": None}
    demo_choices.update({demo["title"]: key for key, demo in ERROR_DEMOS.items()})
    current_demo_key = st.session_state.get("error_demo_type")
    current_demo_label = next(
        (label for label, key in demo_choices.items() if key == current_demo_key),
        "不启用错误示范")
    with st.container(border=True):
        st.markdown("#### 仿真执行模式")
        selected_demo_label = st.selectbox(
            "错误示范与配置", list(demo_choices),
            index=list(demo_choices).index(current_demo_label),
            help="正常模式执行学生方案；错误示范只播放到危险边界，不记入成绩。")
        selected_demo_key = demo_choices[selected_demo_label]
        if selected_demo_key != current_demo_key:
            st.session_state["error_demo_type"] = selected_demo_key
            st.session_state["error_demo_checked"] = False
            st.session_state["run_result"] = None
        active_demo_key = selected_demo_key
        active_demo = ERROR_DEMOS.get(active_demo_key)
        demo_warning_distance = 0.020
        selected_power_line = POWER_LINES[0]
        overhead_demo_height = 0.64
        collision_demo_arm = "left_arm"
        collision_severity = "中度"
        if active_demo_key == "direct_hazard":
            demo_warning_distance = st.slider(
                "带电区暂停预警距离 / m", 0.010, 0.040, 0.020, 0.005,
                help="末端/工具进入该预警距离后，画面停在上一个安全姿态。")
            if not st.session_state.get("hazards"):
                st.warning("当前未启用带电区，该示范无法播放。请先在第1页启用带电区。")
        elif active_demo_key == "overhead_line":
            line_names = [line["name"] for line in POWER_LINES]
            chosen_line_name = st.selectbox("目标高压线", line_names, index=0)
            selected_power_line = next(line for line in POWER_LINES
                                       if line["name"] == chosen_line_name)
            max_height = min(0.65, float(selected_power_line["start"][2]) - 0.04)
            overhead_demo_height = st.slider(
                "错误示范末端高度 Z / m", 0.58, max_height,
                min(0.64, max_height), 0.01)
            demo_warning_distance = st.slider(
                "高压线包络暂停裕度 / m", 0.010, 0.040, 0.025, 0.005)
        elif active_demo_key == "joint_collision":
            collision_demo_arm = st.selectbox(
                "错误关节轨迹执行臂", ["left_arm", "right_arm"],
                format_func=lambda arm: "左臂" if arm == "left_arm" else "右臂")
            collision_severity = st.selectbox("关节扰动程度", ["轻度", "中度", "明显"], index=1,
                                              help="仅改变接近危险边界的速度，仿真仍会在碰撞前停止。")
    with st.expander("聚焦、缩放与视角", expanded=True):
        camera = camera_controls("run_camera")
        show_joints = st.toggle("显示左右臂关节标注", key="run_show_joints",
                                help="显示 L-q1～L-q6 与 R-q1～R-q6。共享机身固定，不计自由度。")
        st.caption("q1肩部水平旋转｜q2肩部俯仰｜q3肘部俯仰｜q4前臂滚转｜q5腕部俯仰｜q6工具轴旋转")
    demo_run = False
    compare_run = False
    if active_demo:
        with st.container(border=True):
            st.markdown("#### 错误示范：先预测，再观察仿真")
            st.warning(f"临时示范：{active_demo['title']}。正式路点和学生参数保持不变。")
            st.write(f"**错误设置：** {active_demo['setup']}")
            risk_options = ["会进入带电教学区", "会接近上方高压线",
                            "会发生机械碰撞/穿模", "可以安全完成"]
            expected_risk = {
                "direct_hazard": risk_options[0], "overhead_line": risk_options[1],
                "joint_collision": risk_options[2],
            }[active_demo_key]
            repair_options = ["更换为侧向绕行", "继续提高Z",
                              "恢复推荐IK并逐段检查", "关闭安全检查"]
            expected_repair = (repair_options[0] if active_demo_key == "direct_hazard"
                               else repair_options[0] if active_demo_key == "overhead_line"
                               else repair_options[2])
            prediction = st.radio("你预测会发生什么？", risk_options, index=None,
                                  key=f"demo_risk_{active_demo_key}")
            repair_prediction = st.radio("你会先采用哪种修改？", repair_options,
                                         index=None, key=f"demo_repair_{active_demo_key}")
            demo_run = st.button("▶ 在MuJoCo中播放至危险边界",
                                 type="primary", width="stretch",
                                 disabled=prediction is None or repair_prediction is None)
            if st.session_state.get("error_demo_checked"):
                compare_run = st.button("▶ 使用同一机位播放正确方案",
                                        width="stretch")
            st.caption("如需退出，在上方下拉框选择“不启用错误示范”。")
        run = False
    else:
        with st.container(border=True):
            st.markdown("#### 执行前风险判断")
            execution_options = ["继续执行，由MuJoCo自行处理",
                                 "停止执行，指出危险源和对应路点",
                                 "隐藏风险区后重新执行"]
            eq1 = st.radio("填空1：预检发现路径侵入带电区或高压线包络时，系统应 ____。",
                           execution_options, index=None, key="execution_quiz_action")
            eq2_options = ["只看最终位置", "检查每个插值点的最小安全裕度",
                           "只检查q1"]
            eq2 = st.radio("填空2：判断一条路线是否安全，需要 ____。",
                           eq2_options, index=None, key="execution_quiz_method")
            if st.session_state.get("user_role") == "teacher":
                def fill_execution_answers():
                    st.session_state["execution_quiz_action"] = execution_options[1]
                    st.session_state["execution_quiz_method"] = eq2_options[1]
                st.button("教师调试：生成本页答案", on_click=fill_execution_answers,
                          key="teacher_execution_answers")
            if st.button("提交执行前判断", key="submit_execution_quiz"):
                st.session_state["execution_quiz_score"] = (
                    int(eq1 == execution_options[1]) + int(eq2 == eq2_options[1]))
            execution_score = st.session_state.get("execution_quiz_score")
            if execution_score is not None:
                (st.success if execution_score == 2 else st.warning)(
                    f"执行前判断得分：{execution_score}/2。")
        quiz_ready = (st.session_state.get("motion_quiz_score") == 2 and
                      st.session_state.get("execution_quiz_score") == 2)
        if not quiz_ready:
            st.info("完成运动参数页和本页的选择填空后，才能启动完整计划。")
        run = st.button("▶ 执行双臂完整计划", type="primary", disabled=not quiz_ready)
    frame_box = st.empty()
    status_box = st.empty()
    progress = st.progress(0)

    def new_sim():
        return RobotSimulation(st.session_state["items"],
            active_station=FACILITIES[active_profile["facility"]]["station"],
            active_region=active_item["location"], active_facility=active_profile["facility"],
            hazards=st.session_state.get("hazards", []))

    try:
        preview = new_sim()
        frame_box.image(preview.render(camera, show_joints), caption="执行前双臂预览：共享机身，左、右机械臂采用镜像布置", width="stretch")
    except Exception as exc:
        st.warning(f"图形预览不可用：{exc}")

    if active_demo:
        st.markdown("#### 仿真画面对应的错误配置诊断")
        config_col, diagnosis_col = st.columns([1.05, 1])
        with config_col:
            if active_demo_key == "direct_hazard":
                execution_arm = st.session_state.get("execution_arm") or "left_arm"
                wrong_config = (
                    f"; 错误PDDL动作\n"
                    f"(verify-safe-route {execution_arm} "
                    f"{active_profile['facility']} route_direct)\n\n"
                    f"; 后续动作依赖了错误批准的直行路线\n"
                    f"(stage-component {execution_arm} {active_item['name']} "
                    f"{active_profile['facility']})")
                st.code(wrong_config, language="lisp")
            elif active_demo_key == "overhead_line":
                wrong_config = (
                    "; 错误运动层配置（非Domain PDDL动作）\n"
                    f"route = route_high\n"
                    f"target-line = {selected_power_line['name']}\n"
                    f"target-z = {overhead_demo_height:.3f} m\n"
                    f"pause-clearance = {demo_warning_distance:.3f} m\n"
                    "; 错误假设：Z越高越安全")
                st.code(wrong_config, language="text")
            else:
                severity_factor = {"轻度": 0.75, "中度": 0.90, "明显": 1.0}[collision_severity]
                wrong_config = (
                    "; 错误关节操作（非PDDL，属于运动控制层）\n"
                    f"arm = {collision_demo_arm}\n"
                    f"joint-disturbance = {collision_severity}\n"
                    f"disturbance-factor = {severity_factor:.2f}\n"
                    "affected-joints = q2, q3, q5\n"
                    "; 错误：同时大幅改变多关节，未检查相邻轨迹")
                st.code(wrong_config, language="text")
        with diagnosis_col:
            if active_demo_key == "direct_hazard":
                st.error("错在 `route_direct`：当前场景存在位于初始区与工位之间的带电区，直行路线不应获得批准。")
                st.success("应改为与执行臂及危险区位置匹配的 `route_left` 或 `route_right`，然后重新生成入口/出口路点。")
            elif active_demo_key == "overhead_line":
                st.error(f"错在 `target-z={overhead_demo_height:.3f}`：该高度使末端向 `{selected_power_line['name']}` 的安全包络靠近，说明“向上绕”也有上界。")
                st.success("应降低Z，或返回PDDL改用侧向绕行；不能通过缩小高压线安全包络规避报警。")
            else:
                st.error(f"错在 `{collision_demo_arm}` 的q2/q3/q5联合扰动：末端可能仍靠近目标，但连杆会撞向共享基座或另一条机械臂。")
                st.success("应恢复推荐IK解，每次只在教学范围内小幅修改一个关节，并检查修改点前后两段插值轨迹。")
            st.caption("上方配置与MuJoCo中的错误播放一一对应；更改下拉框或参数后会立即更新。")

    def play_teaching_waypoints(teaching_waypoints, stop_on_hazard=False,
                                warning_distance=0.020):
        """Animate safe frames and freeze at the last safe configuration."""
        sim = new_sim()
        current = {arm: q.copy() for arm, q in HOME_QS.items()}
        for wi, waypoint in enumerate(teaching_waypoints):
            arm = waypoint.arm
            other = "right_arm" if arm == "left_arm" else "left_arm"
            target_q = (waypoint.joint_target.copy() if waypoint.joint_target is not None else
                        sim.solve_ik(waypoint.position, current[arm], arm, current[other]))
            last_safe = current[arm].copy()
            for fi, candidate in enumerate(sim.interpolate(current[arm], target_q, 24)):
                issues = sim.validate_q(candidate, arm, current[other])
                near_hazard = (stop_on_hazard and any(sim.grabbed.values()) and
                               sim.hazard_clearance(arm) <= warning_distance)
                if issues or near_hazard:
                    sim.step_to(last_safe, arm)
                    frame_box.image(sim.render(camera, show_joints),
                        caption=f"已暂停在危险边界前｜第 {wi + 1} 步 {waypoint.label}",
                        width="stretch")
                    return issues[0] if issues else "末端/工具距带电区安全边界已小于2 cm"
                sim.step_to(candidate, arm)
                last_safe = candidate.copy()
                if fi % 3 == 0:
                    frame_box.image(sim.render(camera, show_joints),
                        caption=f"错误路径安全段｜{waypoint.label}", width="stretch")
                time.sleep(0.015)
            if (waypoint.pddl_action.startswith(("pick(", "assisted-pick("))
                    and waypoint.grip and sim.grabbed[arm] is None):
                sim.set_grab(active_item["name"], arm)
            if (waypoint.pddl_action.startswith(RELEASE_ACTIONS)
                    and not waypoint.grip and sim.grabbed[arm] is not None):
                sim.set_grab(None, arm)
            current[arm] = target_q
        return None

    def play_single_arm_demo(target_q, danger_test, caption, arm="left_arm"):
        sim = new_sim()
        other = "right_arm" if arm == "left_arm" else "left_arm"
        last_safe = HOME_QS[arm].copy()
        for fi, candidate in enumerate(sim.interpolate(last_safe, target_q, 36)):
            issues = sim.validate_q(candidate, arm, HOME_QS[other])
            danger = danger_test(sim, issues)
            if danger:
                sim.step_to(last_safe, arm)
                frame_box.image(sim.render(camera, show_joints),
                                caption=f"已暂停在危险边界前｜{caption}", width="stretch")
                return issues[0] if issues else caption
            sim.step_to(candidate, arm)
            last_safe = candidate.copy()
            if fi % 2 == 0:
                frame_box.image(sim.render(camera, show_joints), caption=caption, width="stretch")
            time.sleep(0.018)
        return None

    if demo_run and active_demo:
        detected = None
        try:
            if active_demo_key == "direct_hazard":
                if not st.session_state.get("hazards"):
                    detected = "当前未启用带电区，无法构造直线穿越示范"
                else:
                    demo_plan = make_plan(
                        st.session_state["items"], st.session_state["intent"],
                        st.session_state.get("execution_arm"), "route_direct")
                    demo_waypoints = waypoints_from_plan(
                        demo_plan, st.session_state["items"], TARGETS,
                        st.session_state["motion"], st.session_state.get("hazards", []))
                    detected = play_teaching_waypoints(
                        demo_waypoints, stop_on_hazard=True,
                        warning_distance=demo_warning_distance)
            elif active_demo_key == "overhead_line":
                demo_sim = new_sim()
                target_q = demo_sim.solve_ik(
                    np.array([selected_power_line["start"][0], 0.55, overhead_demo_height]),
                    HOME_QS["left_arm"],
                    "left_arm", HOME_QS["right_arm"])
                detected = play_single_arm_demo(
                    target_q, lambda sim, issues: bool(issues) or
                    sim.power_line_clearance("left_arm") <= demo_warning_distance,
                    "错误高位路径正在接近上方高压线")
            else:
                left_collision_q = np.array(
                    [1.4775, -0.5796, 2.4572, -1.1045, -1.1068, -0.0223])
                full_collision_q = (left_collision_q if collision_demo_arm == "left_arm" else
                    np.array([-left_collision_q[0], left_collision_q[1], left_collision_q[2],
                              -left_collision_q[3], left_collision_q[4], -left_collision_q[5]]))
                severity_factor = {"轻度": 0.75, "中度": 0.90, "明显": 1.0}[collision_severity]
                collision_q = (HOME_QS[collision_demo_arm] + severity_factor *
                               (full_collision_q - HOME_QS[collision_demo_arm]))
                detected = play_single_arm_demo(
                    collision_q, lambda _sim, issues: bool(issues),
                    "错误关节轨迹正在接近机械碰撞",
                    collision_demo_arm)
        except Exception as exc:
            detected = str(exc)
        st.session_state["error_demo_checked"] = True
        prediction_ok = prediction == expected_risk
        repair_ok = repair_prediction == expected_repair
        status_box.error(f"仿真已在危险边界前暂停：{detected or active_demo['failure']}")
        (st.success if prediction_ok else st.warning)(
            f"危险源预测：{'正确' if prediction_ok else '需要重新判断'}。")
        (st.success if repair_ok else st.warning)(
            f"修改方法：{'正确' if repair_ok else '与当前危险不匹配'}。")
        st.success(f"**正确修改：** {active_demo['repair']}")
        st.info("示范已完成。再次交互时可点击“播放正确方案”进行同机位对比。")

    if compare_run and active_demo:
        try:
            correct_waypoints = waypoints_from_plan(
                st.session_state["plan"], st.session_state["items"], TARGETS,
                st.session_state["motion"], st.session_state.get("hazards", []))
            comparison_issue = play_teaching_waypoints(correct_waypoints, stop_on_hazard=False)
            if comparison_issue:
                status_box.warning(f"正确方案对比被安全检查暂停：{comparison_issue}")
            else:
                status_box.success("正确方案对比完成：全程未进入教学危险边界。")
        except Exception as exc:
            status_box.error(f"正确方案对比无法播放：{exc}")

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
            hazard_clearance_log = []
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
                    hazard_clearance_log.append(sim.live_work_clearance())
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
                    hazard_clearance_log.append(sim.live_work_clearance())
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
                "hazard_clearance": np.asarray(hazard_clearance_log),
                "hazard_count": len(st.session_state.get("hazards", [])),
                "pddl_hint_count": int(st.session_state.get("pddl_hint_count", 0)),
                "pddl_fill_score": st.session_state.get("pddl_fill_score"),
                "route_choice": st.session_state.get("route_choice", "route_left"),
                "motion_quiz_score": st.session_state.get("motion_quiz_score"),
                "execution_quiz_score": st.session_state.get("execution_quiz_score"),
            }
            frame_box.image(sim.render(camera, show_joints), caption="任务完成：双臂已返回Home", width="stretch")
            status_box.success("双臂计划执行完成，可以进入结果分析页面。")
        except Exception as exc:
            status_box.error(f"执行停止：{exc}")
            message = str(exc)
            if "高压线" in message:
                st.error("错误路径提示：当前Z高度或高位绕行使末端进入上方高压线安全包络。"
                         "请降低高度，或返回PDDL页选择侧向绕行。")
            elif "带电教学禁止区" in message:
                st.error("错误路径提示：当前路线触及随机带电区。"
                         "请修改 verify-safe-route 的route选择，不要通过关闭检查规避问题。")

st.divider()
nav("pages/3_运动参数.py", "pages/5_结果分析.py")
