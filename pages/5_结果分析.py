import io
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

from lab_state import nav, page_header

st.set_page_config(page_title="5 结果分析", page_icon="⚡", layout="wide")
page_header(5, "5. 轨迹与实验结果分析")

result = st.session_state["run_result"]
if not result:
    st.warning("尚无执行结果，请先运行 MuJoCo 仿真。")
else:
    q, xyz = result["q"], result["xyz"]
    t = np.arange(len(q)) * float(result.get("dt", 0.05))
    m1, m2, m3 = st.columns(3)
    m1.metric("轨迹采样点", len(q))
    m2.metric("末端路径长度", f"{np.linalg.norm(np.diff(xyz, axis=0), axis=1).sum():.3f} m")
    m3.metric("最大关节变化", f"{np.max(np.ptp(q, axis=0)):.3f} rad")
    c1, c2 = st.columns(2)
    fig1, ax1 = plt.subplots(figsize=(7, 4))
    for i in range(6): ax1.plot(t, q[:, i], label=f"q{i + 1}")
    ax1.set(xlabel="Time / s", ylabel="Joint angle / rad", title="6DOF Joint Trajectory")
    ax1.grid(alpha=0.25); ax1.legend(ncol=3); c1.pyplot(fig1)
    fig2 = plt.figure(figsize=(7, 4)); ax2 = fig2.add_subplot(111, projection="3d")
    ax2.plot(xyz[:, 0], xyz[:, 1], xyz[:, 2], color="#d35400", linewidth=2)
    ax2.scatter(*xyz[0], color="green", label="Start"); ax2.scatter(*xyz[-1], color="red", label="End")
    ax2.set(xlabel="X / m", ylabel="Y / m", zlabel="Z / m", title="End-effector Path"); ax2.legend(); c2.pyplot(fig2)
    csv = "time," + ",".join([f"q{i+1}" for i in range(6)]) + ",x,y,z\n"
    csv += "\n".join(",".join(map(str, [t[i], *q[i], *xyz[i]])) for i in range(len(q)))
    st.download_button("下载轨迹 CSV", csv.encode("utf-8"), "trajectory.csv", "text/csv")
    if result.get("final_positions"):
        st.markdown("#### 任务结束时的物体位置")
        st.dataframe([
            {"物体": name, "X / m": round(float(pos[0]), 3), "Y / m": round(float(pos[1]), 3), "Z / m": round(float(pos[2]), 3)}
            for name, pos in result["final_positions"].items()
        ], hide_index=True, width="stretch")
    st.info("实验思考：修改安全高度、轴向接近距离或某个关节角后重新仿真，并比较路径长度与关节曲线。")

st.divider()
nav("pages/4_仿真执行.py", None)
