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
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("轨迹采样点", len(q_left))
    m2.metric("左臂末端路径", f"{left_length:.3f} m")
    m3.metric("右臂末端路径", f"{right_length:.3f} m")
    m4.metric("两末端最小距离", f"{ee_distance.min():.3f} m")

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
