import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

from lab_state import nav, page_header, require_login

st.set_page_config(page_title="5 结果分析", page_icon="⚡", layout="wide")
require_login()
page_header(5, "5. 单/双臂轨迹与实验结果分析")

result = st.session_state["run_result"]
if not result:
    st.warning("尚无执行结果，请先运行 MuJoCo 仿真。")
else:
    q_left, q_right = result["q_left"], result["q_right"]
    xyz_left, xyz_right = result["xyz_left"], result["xyz_right"]
    t = np.arange(len(q_left)) * float(result.get("dt", 0.05))
    left_length = np.linalg.norm(np.diff(xyz_left, axis=0), axis=1).sum()
    right_length = np.linalg.norm(np.diff(xyz_right, axis=0), axis=1).sum()
    ee_distance = np.linalg.norm(xyz_left - xyz_right, axis=1)
    hazard_clearance = np.asarray(result.get("hazard_clearance", []), dtype=float)
    finite_clearance = hazard_clearance[np.isfinite(hazard_clearance)]
    min_hazard_clearance = float(finite_clearance.min()) if finite_clearance.size else None
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("轨迹采样点", len(q_left))
    m2.metric("左臂末端路径", f"{left_length:.3f} m")
    m3.metric("右臂末端路径", f"{right_length:.3f} m")
    m4.metric("两末端最小距离", f"{ee_distance.min():.3f} m")
    m5.metric("带电区最小裕度", "未启用" if min_hazard_clearance is None
              else f"{min_hazard_clearance:.3f} m")

    path_total = left_length + right_length
    clearance_score = 100 if min_hazard_clearance is None else int(np.clip(
        60 + 400 * min_hazard_clearance, 0, 100))
    efficiency_score = int(np.clip(100 - max(0.0, path_total - 2.0) * 12, 55, 100))
    fill_result = result.get("pddl_fill_score") or {}
    pddl_score = (0 if not fill_result else
                  int(100 * fill_result.get("score", 0) / max(1, fill_result.get("total", 1))))
    decision_points = int(result.get("motion_quiz_score") or 0) + int(
        result.get("execution_quiz_score") or 0)
    learning_score = int(0.6 * pddl_score + 0.4 * (decision_points / 4 * 100))
    hint_penalty = min(20, int(result.get("pddl_hint_count", 0)) * 2)
    total_score = int(np.clip(0.55 * clearance_score + 0.25 * efficiency_score +
                              0.20 * learning_score - hint_penalty, 0, 100))
    st.markdown("#### 带电作业教学评价")
    score_cols = st.columns(4)
    score_cols[0].metric("综合得分", f"{total_score}/100")
    score_cols[1].metric("安全裕度", clearance_score)
    score_cols[2].metric("轨迹效率", efficiency_score)
    score_cols[3].metric("规划与安全决策", learning_score)
    st.caption(f"当前PDDL路线：{result.get('route_choice', '未记录')}｜"
               f"运动参数决策 {int(result.get('motion_quiz_score') or 0)}/2｜"
               f"执行前判断 {int(result.get('execution_quiz_score') or 0)}/2")
    if not fill_result:
        st.warning("PDDL填空未完成，学习项按0分计入；请返回规划页完成风险状态与路线补全。")
    if min_hazard_clearance is not None and min_hazard_clearance < 0.03:
        st.warning("轨迹虽未侵入禁止区，但距离安全边界不足3 cm，建议调整路点或提高安全高度。")
    elif min_hazard_clearance is not None:
        st.success("完整轨迹未侵入带电教学禁止区。")

    c1, c2 = st.columns(2)
    for column, q, name, color in ((c1, q_left, "左臂", "#176f91"),
                                    (c2, q_right, "右臂", "#2f7d57")):
        fig, ax = plt.subplots(figsize=(7, 4))
        for i in range(6):
            ax.plot(t, q[:, i], label=f"q{i + 1}")
        ax.set(xlabel="Time / s", ylabel="Joint angle / rad", title=f"{name} 6DOF Joint Trajectory")
        ax.grid(alpha=0.25); ax.legend(ncol=3); column.pyplot(fig)

    fig3 = plt.figure(figsize=(10, 5)); ax3 = fig3.add_subplot(111, projection="3d")
    ax3.plot(*xyz_left.T, color="#176f91", linewidth=2, label="Left arm")
    ax3.plot(*xyz_right.T, color="#2f7d57", linewidth=2, label="Right arm")
    ax3.set(xlabel="X / m", ylabel="Y / m", zlabel="Z / m", title="Dual End-effector Paths")
    ax3.legend(); st.pyplot(fig3)

    if finite_clearance.size:
        fig4, ax4 = plt.subplots(figsize=(10, 3.4))
        clearance_t = np.arange(len(hazard_clearance)) * float(result.get("dt", 0.05))
        ax4.plot(clearance_t, hazard_clearance, color="#d8672b", linewidth=2)
        ax4.axhline(0, color="#b42318", linestyle="--", label="Exclusion boundary")
        ax4.axhline(0.03, color="#e9a23b", linestyle=":", label="3 cm teaching warning")
        ax4.set(xlabel="Time / s", ylabel="Clearance / m", title="Live-work Hazard Clearance")
        ax4.grid(alpha=0.25); ax4.legend(); st.pyplot(fig4)

    header = ["time"] + [f"left_q{i+1}" for i in range(6)] + [f"right_q{i+1}" for i in range(6)]
    header += ["left_x", "left_y", "left_z", "right_x", "right_y", "right_z"]
    rows = [[t[i], *q_left[i], *q_right[i], *xyz_left[i], *xyz_right[i]] for i in range(len(t))]
    csv = ",".join(header) + "\n" + "\n".join(",".join(map(str, row)) for row in rows)
    st.download_button("下载机械臂轨迹 CSV", csv.encode("utf-8"), "robot_trajectory.csv", "text/csv")
    if result.get("final_positions"):
        st.markdown("#### 任务结束时的物体位置")
        st.dataframe([{"物体": name, "X / m": round(float(pos[0]), 3),
                       "Y / m": round(float(pos[1]), 3), "Z / m": round(float(pos[2]), 3)}
                      for name, pos in result["final_positions"].items()], hide_index=True, width="stretch")
    st.info("实验思考：比较左右臂路径长度、等待时间与最小末端距离，说明任务分配如何影响双臂协作效率。")

st.divider()
nav("pages/4_仿真执行.py", None)
