"""Compact 6-DOF MuJoCo arm, numerical IK and teaching trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape
import numpy as np
import mujoco


# A visibly safe pose above the workbench rather than the model's zero pose.
HOME_Q = np.array([-0.2321, -1.1557, 1.8717, -0.4894, -1.75, 0.2970])
SAFE_Z = 0.52

# Student-facing limits are deliberately narrower than the mechanical limits.
# They keep the arm in the front/upper teaching workspace.
TEACHING_JOINT_LIMITS = np.array([
    [-1.20, 1.20], [-1.45, 0.70], [-0.25, 2.20],
    [-1.20, 1.20], [-1.75, 1.15], [-1.20, 1.20],
])
WORKSPACE_LIMITS = {"x": (0.24, 0.74), "y": (-0.32, 0.32), "z": (0.15, 0.60)}


@dataclass
class Waypoint:
    label: str
    position: np.ndarray
    grip: bool
    pddl_action: str


def _geom_for(item: dict) -> str:
    kind = item["kind"]
    size = item["size"]
    rgba = item["rgba"]
    if kind in {"fuse", "insulator", "probe", "operating_rod", "bolt"}:
        radius = float(size[0])
        half = float(size[2])
        return f'<geom type="cylinder" size="{radius} {half}" rgba="{rgba}" friction="1"/>'
    return f'<geom type="box" size="{size[0]} {size[1]} {size[2]}" rgba="{rgba}" friction="1"/>'


def build_xml(items: list[dict]) -> str:
    bodies = []
    for item in items:
        x, y, z = item["position"]
        bodies.append(
            f'<body name="obj_{escape(item["name"])}" pos="{x} {y} {z}">'
            f'<freejoint/>{_geom_for(item)}</body>'
        )
    return f"""<mujoco model="power_maintenance_lab">
<compiler angle="radian"/>
<option timestep="0.01" gravity="0 0 -9.81" integrator="implicitfast"/>
<visual><global offwidth="800" offheight="520"/><quality shadowsize="2048"/></visual>
<default>
  <joint damping="2" armature="0.05" limited="true"/>
  <geom density="600" friction="1 0.1 0.01" contype="1" conaffinity="1"/>
  <position kp="120" kv="18" ctrllimited="true" ctrlrange="-3.14 3.14"/>
</default>
<asset>
  <material name="metal" rgba="0.32 0.38 0.45 1"/>
  <material name="arm" rgba="0.15 0.42 0.72 1"/>
</asset>
<worldbody>
  <light pos="0 -1 2" dir="0 0 -1" diffuse="1 1 1"/>
  <camera name="overview" pos="1.25 -1.25 0.95" xyaxes="0.70 0.70 0 -0.35 0.35 0.87"/>
  <geom type="plane" size="2 2 0.1" rgba="0.88 0.9 0.92 1"/>
  <body name="table" pos="0.52 0 0.035"><geom type="box" size="0.40 0.38 0.035" rgba="0.48 0.50 0.52 1"/></body>
  <body name="panel" pos="0.83 0.32 0.31"><geom type="box" size="0.025 0.16 0.27" rgba="0.25 0.27 0.30 1"/></body>
  <body name="base" pos="0 0 0.07">
    <geom type="cylinder" size="0.075 0.07" material="metal"/>
    <joint name="j1" axis="0 0 1" range="-1.5 1.5"/>
    <geom type="cylinder" pos="0 0 0.16" size="0.055 0.16" material="metal"/>
    <body name="link1" pos="0 0 0.32">
      <joint name="j2" axis="0 1 0" range="-1.7 1.3"/>
      <geom type="capsule" fromto="0 0 0 0.28 0 0" size="0.040" material="arm"/>
      <body name="link2" pos="0.28 0 0">
        <joint name="j3" axis="0 1 0" range="-0.4 2.3"/>
        <geom type="capsule" fromto="0 0 0 0.25 0 0" size="0.034" material="arm"/>
        <body name="link3" pos="0.25 0 0">
          <joint name="j4" axis="1 0 0" range="-1.6 1.6"/>
          <geom type="capsule" fromto="0 0 0 0.14 0 0" size="0.029" material="arm"/>
          <body name="link4" pos="0.14 0 0">
            <joint name="j5" axis="0 1 0" range="-1.9 1.9"/>
            <geom type="capsule" fromto="0 0 0 0.14 0 0" size="0.027" material="arm"/>
            <body name="link5" pos="0.14 0 0">
              <joint name="j6" axis="1 0 0" range="-1.6 1.6"/>
              <geom type="cylinder" size="0.035 0.04" quat="0.7071 0 0.7071 0" material="metal"/>
              <body name="ee" pos="0.09 0 0">
                <geom type="box" size="0.025 0.055 0.018" rgba="0.1 0.1 0.12 1"/>
                <geom type="box" pos="0 -0.047 -0.035" size="0.012 0.009 0.04" rgba="0.85 0.55 0.12 1"/>
                <geom type="box" pos="0 0.047 -0.035" size="0.012 0.009 0.04" rgba="0.85 0.55 0.12 1"/>
                <site name="ee_site" pos="0 0 -0.08" size="0.012" rgba="1 0 0 1"/>
              </body>
            </body>
          </body>
        </body>
      </body>
    </body>
  </body>
  {''.join(bodies)}
</worldbody>
<contact>
  <exclude body1="base" body2="link1"/>
  <exclude body1="link1" body2="link2"/>
  <exclude body1="link2" body2="link3"/>
  <exclude body1="link3" body2="link4"/>
  <exclude body1="link4" body2="link5"/>
  <exclude body1="link5" body2="ee"/>
</contact>
<actuator>
  <position joint="j1"/><position joint="j2"/><position joint="j3"/>
  <position joint="j4"/><position joint="j5"/><position joint="j6"/>
</actuator>
</mujoco>"""


class RobotSimulation:
    def __init__(self, items: list[dict]):
        self.items = items
        self.model = mujoco.MjModel.from_xml_string(build_xml(items))
        self.data = mujoco.MjData(self.model)
        self.data.qpos[:6] = HOME_Q
        self.data.ctrl[:] = HOME_Q
        mujoco.mj_forward(self.model, self.data)
        self.site_id = self.model.site("ee_site").id
        # Create the OpenGL renderer lazily. This keeps planning/IK testable on
        # machines without an active graphical session.
        self.renderer = None
        self.grabbed: str | None = None
        self.object_qadr = {}
        for item in items:
            body_id = self.model.body(f"obj_{item['name']}").id
            joint_id = self.model.body_jntadr[body_id]
            self.object_qadr[item["name"]] = self.model.jnt_qposadr[joint_id]

    def render(self) -> np.ndarray:
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, height=520, width=800)
        self.renderer.update_scene(self.data, camera="overview")
        return self.renderer.render().copy()

    def ee_position(self) -> np.ndarray:
        return self.data.site_xpos[self.site_id].copy()

    def collision_report(self, q: np.ndarray) -> list[str]:
        """Return robot/environment penetrations for a teaching configuration."""
        self.data.qpos[:6] = q
        self.data.qvel[:6] = 0
        mujoco.mj_forward(self.model, self.data)
        robot_bodies = {"base", "link1", "link2", "link3", "link4", "link5", "ee"}
        collisions = set()
        for contact in self.data.contact:
            if contact.dist >= -0.001:
                continue
            body1 = self.model.body(self.model.geom_bodyid[contact.geom1]).name or "world"
            body2 = self.model.body(self.model.geom_bodyid[contact.geom2]).name or "world"
            if body1 in robot_bodies or body2 in robot_bodies:
                collisions.add(f"{body1} ↔ {body2}")
        return sorted(collisions)

    def validate_q(self, q: np.ndarray) -> list[str]:
        issues = []
        q = np.asarray(q, dtype=float)
        if np.any(q < TEACHING_JOINT_LIMITS[:, 0]) or np.any(q > TEACHING_JOINT_LIMITS[:, 1]):
            issues.append("关节角超出教学安全范围")
        collisions = self.collision_report(q)
        if collisions:
            issues.append("检测到穿模/碰撞：" + "、".join(collisions))
        ee = self.ee_position()
        for axis, value in zip(("x", "y", "z"), ee):
            lo, hi = WORKSPACE_LIMITS[axis]
            if not lo <= value <= hi:
                issues.append(f"末端 {axis.upper()}={value:.3f} m 超出安全工作区 [{lo:.2f}, {hi:.2f}]")
        return issues

    def solve_ik(self, target: np.ndarray, seed: np.ndarray) -> np.ndarray:
        lower = np.maximum(self.model.jnt_range[:6, 0], TEACHING_JOINT_LIMITS[:, 0])
        upper = np.minimum(self.model.jnt_range[:6, 1], TEACHING_JOINT_LIMITS[:, 1])
        rng = np.random.default_rng(7)
        seeds = [np.clip(seed, lower, upper), np.clip(HOME_Q, lower, upper), (lower + upper) / 2]
        seeds.extend(rng.uniform(lower, upper) for _ in range(10))
        best_q, best_error = None, float("inf")
        for initial in seeds:
            q = initial.copy()
            for _ in range(220):
                self.data.qpos[:6] = q
                mujoco.mj_forward(self.model, self.data)
                error = target - self.ee_position()
                error_norm = float(np.linalg.norm(error))
                if error_norm < best_error:
                    best_q, best_error = q.copy(), error_norm
                if error_norm < 0.008:
                    return q
                jacp = np.zeros((3, self.model.nv))
                jacr = np.zeros((3, self.model.nv))
                mujoco.mj_jacSite(self.model, self.data, jacp, jacr, self.site_id)
                jac = jacp[:, :6]
                dq = jac.T @ np.linalg.solve(jac @ jac.T + 0.003 * np.eye(3), error)
                q += np.clip(dq, -0.10, 0.10)
                q = np.clip(q, lower, upper)
        raise ValueError(f"目标位置不可达：{np.round(target, 3).tolist()}")

    def interpolate(self, q0: np.ndarray, q1: np.ndarray, frames: int = 35) -> np.ndarray:
        s = np.linspace(0, 1, frames)
        smooth = 3 * s**2 - 2 * s**3
        return q0[None, :] + smooth[:, None] * (q1 - q0)[None, :]

    def set_grab(self, item_name: str | None) -> None:
        self.grabbed = item_name

    def step_to(self, q: np.ndarray) -> None:
        # Position-level trajectory playback is deterministic and makes the
        # six commanded joint angles directly visible to students.
        self.data.qpos[:6] = q
        self.data.qvel[:6] = 0
        self.data.ctrl[:] = q
        mujoco.mj_forward(self.model, self.data)
        if self.grabbed:
            adr = self.object_qadr[self.grabbed]
            self.data.qpos[adr:adr + 3] = self.ee_position() + np.array([0, 0, -0.08])
            self.data.qpos[adr + 3:adr + 7] = np.array([1, 0, 0, 0])
            self.data.qvel[self.model.jnt_dofadr[self.model.body_jntadr[self.model.body(f"obj_{self.grabbed}").id]]:
                           self.model.jnt_dofadr[self.model.body_jntadr[self.model.body(f"obj_{self.grabbed}").id]] + 6] = 0
            mujoco.mj_forward(self.model, self.data)


def waypoints_from_plan(
    plan: list[dict], items: list[dict], targets: dict[str, tuple], motion: dict | None = None
) -> list[Waypoint]:
    motion = motion or {}
    safe_z = float(motion.get("safe_z", SAFE_Z))
    grasp_offset = float(motion.get("grasp_offset", 0.08))
    approach_distance = float(motion.get("approach_distance", 0.10))
    by_name = {item["name"]: item for item in items}
    result: list[Waypoint] = []
    held = None
    for step in plan:
        action = step["action"]
        if action == "pick":
            held = step["args"][0]
            pos = np.array(by_name[held]["position"], dtype=float)
            kind = by_name[held]["kind"]
            grasp = pos + np.array([0, 0, grasp_offset])
            if kind in {"fuse", "terminal", "breaker"}:
                # Prefer approaching away from the pedestal, but reverse near
                # the far workspace boundary so the pre-grasp remains safe.
                direction = 1.0 if grasp[0] <= 0.60 else -1.0
                pre = grasp + np.array([direction * approach_distance, 0, 0])
                result.extend([
                    Waypoint("沿安装轴线对准", pre, False, f"pick({held})"),
                    Waypoint("沿轴线低速接近", grasp, False, f"pick({held})"),
                    Waypoint("夹紧部件", grasp, True, f"pick({held})"),
                    Waypoint("沿轴线拔出", pre, True, f"pick({held})"),
                    Waypoint("提升至安全高度", np.array([pre[0], pre[1], safe_z]), True, f"pick({held})"),
                ])
            elif kind in {"probe", "operating_rod"}:
                result.extend([
                    Waypoint("移动到细长工具中部", np.array([pos[0], pos[1], safe_z]), False, f"pick({held})"),
                    Waypoint("保持方向下降", grasp, False, f"pick({held})"),
                    Waypoint("中部夹持", grasp, True, f"pick({held})"),
                    Waypoint("定向安全抬升", np.array([pos[0], pos[1], safe_z]), True, f"pick({held})"),
                ])
            else:
                result.extend([
                    Waypoint("移动到推荐抓取点上方", np.array([pos[0], pos[1], safe_z]), False, f"pick({held})"),
                    Waypoint("保持推荐姿态下降", grasp, False, f"pick({held})"),
                    Waypoint("稳定夹持", grasp, True, f"pick({held})"),
                    Waypoint("垂直安全抬升", np.array([pos[0], pos[1], safe_z]), True, f"pick({held})"),
                ])
        elif action == "place":
            held = step["args"][0]
            target = np.array(targets[step["args"][1]], dtype=float)
            # The target map supplies XY. Z is derived from the workbench,
            # object half-height and the gripper-to-object-center offset.
            target[2] = 0.07 + float(by_name[held]["size"][2]) + grasp_offset
            result.extend([
                Waypoint("移动至目标上方", np.array([target[0], target[1], safe_z]), True, f"place({held})"),
                Waypoint("下降放置", target, True, f"place({held})"),
                Waypoint("松开夹爪", target, False, f"place({held})"),
                Waypoint("安全撤离", np.array([target[0], target[1], safe_z]), False, f"place({held})"),
            ])
            held = None
    return result

