"""Compact dual 6-DOF MuJoCo arms, numerical IK and teaching trajectories."""

from __future__ import annotations

from dataclasses import dataclass
import os
import sys
from xml.sax.saxutils import escape

# Streamlit Community Cloud runs on Linux without a usable desktop display.
# Force OSMesa before importing MuJoCo: the hosting environment may already
# define MUJOCO_GL=glfw, so setdefault() is not sufficient.  This application
# only needs offscreen image rendering.  macOS and Windows remain unchanged.
if sys.platform.startswith("linux"):
    os.environ["MUJOCO_GL"] = "osmesa"
    os.environ.setdefault("PYOPENGL_PLATFORM", "osmesa")
    print("[robot_sim] MuJoCo offscreen backend: OSMesa")

import numpy as np
import mujoco

from lab_config import FACILITIES, REGIONS, STATIONS, TASK_MODES, TASK_PROFILES, WORKBENCH


# A visibly safe pose above the workbench rather than the model's zero pose.
HOME_QS = {
    # Mirrored, inward-facing teaching pose inspired by a shared-torso
    # collaborative robot.  The wrists remain separated by a safe gap.
    "left_arm": np.array([0.68, -0.60, 1.60, -0.35, -1.30, 0.20]),
    "right_arm": np.array([-0.68, -0.60, 1.60, 0.35, -1.30, -0.20]),
}
# Backward-compatible teaching default; new code should use HOME_QS.
HOME_Q = HOME_QS["left_arm"]
SAFE_Z = 0.52

# Student-facing limits are deliberately narrower than the mechanical limits.
# They keep the arm in the front/upper teaching workspace.
TEACHING_JOINT_LIMITS = np.array([
    [-1.20, 1.20], [-1.45, 0.70], [-0.25, 2.20],
    [-1.20, 1.20], [-1.75, 1.15], [-1.20, 1.20],
])
WORKSPACE_LIMITS = {"x": (0.18, 0.86), "y": (-0.78, 0.78), "z": (0.14, 0.64)}


@dataclass
class Waypoint:
    label: str
    position: np.ndarray
    grip: bool
    pddl_action: str
    arm: str = "left_arm"
    joint_target: np.ndarray | None = None


def _geom_for(item: dict) -> str:
    kind = item["kind"]
    size = item["size"]
    rgba = item["rgba"]
    if kind in {"fuse", "insulator", "probe", "operating_rod", "bolt", "wire"}:
        radius = float(size[0])
        half = float(size[2])
        return f'<geom type="cylinder" size="{radius} {half}" rgba="{rgba}" friction="1"/>'
    return f'<geom type="box" size="{size[0]} {size[1]} {size[2]}" rgba="{rgba}" friction="1"/>'


def _arm_xml(arm: str, y: float, rgba: str) -> str:
    p = arm.replace("_arm", "")
    j = "L-q" if arm == "left_arm" else "R-q"
    return f"""<body name="{p}_shoulder" pos="0.015 {y} 0.34">
    <joint name="{j}1" axis="0 0 1" range="-1.5 1.5"/>
    <geom type="sphere" size="0.078" rgba="0.84 0.86 0.87 1"/>
    <geom type="cylinder" size="0.061 0.080" quat="0.7071 0.7071 0 0" material="joint-dark"/>
    <body name="{p}_link1" pos="0 0 0">
      <joint name="{j}2" axis="0 1 0" range="-1.7 1.3"/>
      <geom type="capsule" fromto="0 0 0 0.28 0 0" size="0.046" rgba="{rgba}"/>
      <body name="{p}_link2" pos="0.28 0 0">
        <joint name="{j}3" axis="0 1 0" range="-0.4 2.3"/>
        <geom type="cylinder" size="0.060 0.048" quat="0.7071 0.7071 0 0" material="joint-dark"/>
        <geom type="capsule" fromto="0.035 0 0 0.25 0 0" size="0.040" rgba="{rgba}"/>
        <body name="{p}_link3" pos="0.25 0 0">
          <joint name="{j}4" axis="1 0 0" range="-1.6 1.6"/>
          <geom type="sphere" size="0.050" rgba="0.82 0.84 0.85 1"/>
          <geom type="capsule" fromto="0.025 0 0 0.14 0 0" size="0.033" rgba="{rgba}"/>
          <body name="{p}_link4" pos="0.14 0 0">
            <joint name="{j}5" axis="0 1 0" range="-1.9 1.9"/>
            <geom type="cylinder" size="0.045 0.040" quat="0.7071 0.7071 0 0" material="joint-dark"/>
            <geom type="capsule" fromto="0.025 0 0 0.14 0 0" size="0.030" rgba="{rgba}"/>
            <body name="{p}_link5" pos="0.14 0 0">
              <joint name="{j}6" axis="1 0 0" range="-1.6 1.6"/>
              <geom type="cylinder" size="0.038 0.035" quat="0.7071 0 0.7071 0" material="joint-dark"/>
              <body name="{p}_ee" pos="0.090 0 0">
                <geom type="box" size="0.026 0.050 0.018" rgba="0.16 0.17 0.18 1"/>
                <geom type="box" pos="0 -0.043 -0.035" size="0.011 0.008 0.040" rgba="0.72 0.74 0.75 1"/>
                <geom type="box" pos="0 0.043 -0.035" size="0.011 0.008 0.040" rgba="0.72 0.74 0.75 1"/>
                <site name="{p}_ee_site" pos="0 0 -0.08" size="0.012" rgba="1 0 0 1"/>
              </body>
            </body>
          </body>
        </body>
      </body>
    </body>
  </body>"""


def _arm_contacts(arm: str) -> str:
    p = arm.replace("_arm", "")
    chain = [f"{p}_shoulder", *[f"{p}_link{i}" for i in range(1, 6)], f"{p}_ee"]
    return "".join(f'<exclude body1="{a}" body2="{b}"/>' for a, b in zip(chain, chain[1:]))


def _arm_actuators(arm: str) -> str:
    p = arm.replace("_arm", "")
    j = "L-q" if arm == "left_arm" else "R-q"
    return "".join(f'<position name="{p}_a{i}" joint="{j}{i}"/>' for i in range(1, 7))


def _fixture_support_position(target: np.ndarray, assistant_arm: str) -> np.ndarray:
    """Return the reachable outer-frame point braced by the assistant arm."""
    side = -1.0 if assistant_arm == "right_arm" else 1.0
    return np.array([max(0.50, target[0] - 0.08), target[1] + side * 0.32,
                     max(0.24, target[2] + 0.11)])


def build_xml(items: list[dict], active_station: str | None = None,
              active_region: str | None = None,
              active_facility: str | None = None) -> str:
    bodies = []
    table_x, table_y, table_z = WORKBENCH["center"]
    table_sx, table_sy, table_sz = WORKBENCH["half_size"]
    for item in items:
        x, y, z = item["position"]
        bodies.append(
            f'<body name="obj_{escape(item["name"])}" pos="{x} {y} {z}">'
            # Movable objects need a free joint for playback, but it is not a
            # robot DOF.  Put it in hidden visualization group 3 so MuJoCo
            # does not expose an autogenerated label such as "joint12".
            f'<freejoint name="obj_{escape(item["name"])}_free" group="3"/>'
            f'{_geom_for(item)}</body>'
        )
    fixtures = []
    station_pads = []
    region_pads = []
    for name, region in REGIONS.items():
        if active_region is not None and name != active_region:
            continue
        xmin, xmax = region["x"]
        ymin, ymax = region["y"]
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        sx, sy = (xmax - xmin) / 2, (ymax - ymin) / 2
        rgb = region["rgba"]
        active = name == active_region
        fill_alpha = "0.34" if active else "0.035"
        border_alpha = "1" if active else "0.28"
        border = 0.004
        region_pads.append(
            f'<body name="region_{name}" pos="{cx} {cy} 0.081">'
            f'<geom type="box" size="{sx} {sy} 0.0015" rgba="{rgb} {fill_alpha}" contype="0" conaffinity="0"/>'
            f'<geom type="box" pos="0 {sy-border} 0.003" size="{sx} {border} 0.002" rgba="{rgb} {border_alpha}" contype="0" conaffinity="0"/>'
            f'<geom type="box" pos="0 {-sy+border} 0.003" size="{sx} {border} 0.002" rgba="{rgb} {border_alpha}" contype="0" conaffinity="0"/>'
            f'<geom type="box" pos="{sx-border} 0 0.003" size="{border} {sy} 0.002" rgba="{rgb} {border_alpha}" contype="0" conaffinity="0"/>'
            f'<geom type="box" pos="{-sx+border} 0 0.003" size="{border} {sy} 0.002" rgba="{rgb} {border_alpha}" contype="0" conaffinity="0"/>'
            f'</body>'
        )
    for code, station in STATIONS.items():
        if active_station is not None and code != active_station:
            continue
        x, y, z = station["center"]
        sx, sy = station["size"]
        rgb = station["rgba"].rsplit(" ", 1)[0]
        pad_alpha = "0.46" if code == active_station else "0.22"
        border_alpha = "1" if code == active_station else "0.72"
        border = 0.0045
        station_pads.append(
            f'<body name="station_{code}" pos="{x} {y} {z}">'
            f'<geom type="box" size="{sx} {sy} 0.003" rgba="{rgb} {pad_alpha}" contype="0" conaffinity="0"/>'
            f'<geom type="box" pos="0 {sy-border} 0.006" size="{sx} {border} 0.004" rgba="{rgb} {border_alpha}" contype="0" conaffinity="0"/>'
            f'<geom type="box" pos="0 {-sy+border} 0.006" size="{sx} {border} 0.004" rgba="{rgb} {border_alpha}" contype="0" conaffinity="0"/>'
            f'<geom type="box" pos="{sx-border} 0 0.006" size="{border} {sy} 0.004" rgba="{rgb} {border_alpha}" contype="0" conaffinity="0"/>'
            f'<geom type="box" pos="{-sx+border} 0 0.006" size="{border} {sy} 0.004" rgba="{rgb} {border_alpha}" contype="0" conaffinity="0"/>'
            f'</body>'
        )
    brace_facilities = {TASK_PROFILES[kind]["facility"] for kind, mode in TASK_MODES.items()
                        if mode == "dual" and kind != "wire"}
    for name, facility in FACILITIES.items():
        # A task-focused scene only needs its current interaction facility.
        # Keeping every fixture visible made the initial workbench look as if
        # it was already filled with unrelated objects.
        if active_facility is not None and name != active_facility:
            continue
        x, y, z = facility["position"]
        rgba = facility["rgba"]
        kind = facility["kind"]
        if kind == "slot":
            geom = f'<geom type="box" size="0.035 0.045 0.012" rgba="{rgba}" contype="0" conaffinity="0"/>'
        elif kind == "bay":
            geom = f'<geom type="box" size="0.050 0.055 0.035" rgba="{rgba}" contype="0" conaffinity="0"/>'
        elif kind == "area":
            geom = f'<geom type="box" size="0.075 0.060 0.004" rgba="{rgba}" contype="0" conaffinity="0"/>'
        elif kind == "switch":
            geom = f'<geom type="capsule" fromto="0 0 0 0 0 0.08" size="0.012" rgba="{rgba}" contype="0" conaffinity="0"/>'
        else:
            geom = f'<geom type="sphere" size="0.018" rgba="{rgba}" contype="0" conaffinity="0"/>'
        # Draw the structural brace used by the assistant.  It links the
        # gripper's support point to the visible facility, so the collaboration
        # is not represented as a hand hovering in empty space.
        brace = ""
        if name == active_facility and name in brace_facilities:
            assistant = "right_arm" if y >= 0 else "left_arm"
            support = _fixture_support_position(np.array([x, y, z]), assistant)
            dx, dy, dz = support - np.array([x, y, z])
            brace = (
                f'<geom type="capsule" fromto="0 0 0 {dx} {dy} {dz}" size="0.009" '
                f'rgba="0.30 0.33 0.35 0.82" contype="0" conaffinity="0"/>'
                f'<geom type="sphere" pos="{dx} {dy} {dz}" size="0.022" '
                f'rgba="0.24 0.27 0.29 1" contype="0" conaffinity="0"/>'
            )
        fixtures.append(f'<body name="fixture_{name}" pos="{x} {y} {z}">{geom}{brace}</body>')
    return f"""<mujoco model="power_maintenance_lab">
<compiler angle="radian"/>
<option timestep="0.01" gravity="0 0 -9.81" integrator="implicitfast"/>
<visual>
  <global offwidth="800" offheight="520"/>
  <quality shadowsize="2048" offsamples="4"/>
  <headlight ambient="0.35 0.38 0.42" diffuse="0.75 0.78 0.82" specular="0.18 0.18 0.18"/>
  <rgba haze="0.78 0.84 0.88 1"/>
</visual>
<default>
  <joint damping="2" armature="0.05" limited="true"/>
  <geom density="600" friction="1 0.1 0.01" contype="1" conaffinity="1"/>
  <position kp="120" kv="18" ctrllimited="true" ctrlrange="-3.14 3.14"/>
</default>
<asset>
  <texture type="skybox" builtin="gradient" rgb1="0.72 0.82 0.88" rgb2="0.95 0.97 0.98" width="512" height="3072"/>
  <texture name="floor-grid" type="2d" builtin="checker" rgb1="0.76 0.79 0.80" rgb2="0.88 0.90 0.91" width="512" height="512"/>
  <material name="floor" texture="floor-grid" texrepeat="4 4" reflectance="0.08"/>
  <material name="metal" rgba="0.24 0.29 0.33 1" specular="0.45" shininess="0.35"/>
  <material name="joint-dark" rgba="0.24 0.26 0.28 1" specular="0.55" shininess="0.45"/>
  <material name="robot-shell" rgba="0.82 0.84 0.85 1" specular="0.42" shininess="0.38"/>
  <material name="arm" rgba="0.08 0.36 0.50 1" specular="0.35" shininess="0.25"/>
</asset>
<worldbody>
  <light pos="0.25 -0.7 1.7" dir="0.2 0.25 -1" diffuse="0.95 0.92 0.86" castshadow="true"/>
  <light pos="1.1 0.6 1.2" dir="-0.5 -0.2 -0.8" diffuse="0.40 0.52 0.62" castshadow="false"/>
  <camera name="overview" pos="1.58 -1.72 1.20" xyaxes="0.74 0.67 0 -0.36 0.40 0.84" fovy="43"/>
  <geom type="plane" size="2 2 0.1" material="floor"/>
  <body name="table" pos="{table_x} {table_y} {table_z}"><geom type="box" size="{table_sx} {table_sy} {table_sz}" rgba="0.38 0.43 0.45 1"/></body>
  <body name="panel" pos="1.08 0.43 0.31"><geom type="box" size="0.025 0.11 0.27" rgba="0.18 0.22 0.24 1"/></body>
  {''.join(station_pads)}
  {''.join(region_pads)}
  {''.join(fixtures)}
  <body name="dual_base" pos="0 0 0.07">
    <geom type="box" pos="0 0 0.035" size="0.13 0.21 0.035" material="joint-dark"/>
    <geom type="box" pos="0 0 0.17" size="0.10 0.15 0.11" material="robot-shell"/>
    <geom type="capsule" fromto="0 0 0.20 0 0 0.34" size="0.095" material="robot-shell"/>
    <geom type="box" pos="0.018 0 0.34" size="0.075 0.225 0.055" material="robot-shell"/>
    {_arm_xml('left_arm', 0.205, '0.76 0.79 0.80 1')}
    {_arm_xml('right_arm', -0.205, '0.76 0.79 0.80 1')}
  </body>
  {''.join(bodies)}
</worldbody>
<contact>
  {_arm_contacts('left_arm')}
  {_arm_contacts('right_arm')}
  <exclude body1="dual_base" body2="left_shoulder"/>
  <exclude body1="dual_base" body2="right_shoulder"/>
  <exclude body1="dual_base" body2="left_link1"/>
  <exclude body1="dual_base" body2="right_link1"/>
</contact>
<actuator>
  {_arm_actuators('left_arm')}
  {_arm_actuators('right_arm')}
</actuator>
</mujoco>"""


class RobotSimulation:
    def __init__(self, items: list[dict], active_station: str | None = None,
                 active_region: str | None = None,
                 active_facility: str | None = None):
        self.items = items
        self.model = mujoco.MjModel.from_xml_string(
            build_xml(items, active_station, active_region, active_facility))
        self.data = mujoco.MjData(self.model)
        self.arms = ("left_arm", "right_arm")
        self.joint_qadr = {}
        self.joint_dadr = {}
        self.actuator_adr = {}
        self.site_ids = {}
        for arm in self.arms:
            p = arm.replace("_arm", "")
            j = "L-q" if arm == "left_arm" else "R-q"
            self.joint_qadr[arm] = np.array([self.model.jnt_qposadr[self.model.joint(f"{j}{i}").id]
                                             for i in range(1, 7)])
            self.joint_dadr[arm] = np.array([self.model.jnt_dofadr[self.model.joint(f"{j}{i}").id]
                                             for i in range(1, 7)])
            self.actuator_adr[arm] = np.array([self.model.actuator(f"{p}_a{i}").id for i in range(1, 7)])
            self.site_ids[arm] = self.model.site(f"{p}_ee_site").id
            self.data.qpos[self.joint_qadr[arm]] = HOME_QS[arm]
            self.data.ctrl[self.actuator_adr[arm]] = HOME_QS[arm]
        mujoco.mj_forward(self.model, self.data)
        # Create the OpenGL renderer lazily. This keeps planning/IK testable on
        # machines without an active graphical session.
        self.renderer = None
        self.grabbed: dict[str, str | None] = {arm: None for arm in self.arms}
        self.object_qadr = {}
        for item in items:
            body_id = self.model.body(f"obj_{item['name']}").id
            joint_id = self.model.body_jntadr[body_id]
            self.object_qadr[item["name"]] = self.model.jnt_qposadr[joint_id]

    def render(self, camera: dict | None = None, show_joints: bool = False) -> np.ndarray:
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, height=520, width=800)
        scene_option = None
        if show_joints:
            scene_option = mujoco.MjvOption()
            mujoco.mjv_defaultOption(scene_option)
            scene_option.label = mujoco.mjtLabel.mjLABEL_JOINT
            scene_option.flags[mujoco.mjtVisFlag.mjVIS_JOINT] = True
        if camera:
            view = mujoco.MjvCamera()
            mujoco.mjv_defaultCamera(view)
            view.type = mujoco.mjtCamera.mjCAMERA_FREE
            view.azimuth = float(camera.get("azimuth", 132.0))
            view.elevation = float(camera.get("elevation", -28.0))
            view.distance = float(camera.get("distance", 1.55))
            view.lookat[:] = np.asarray(camera.get("lookat", [0.45, 0.0, 0.24]), dtype=float)
            self.renderer.update_scene(self.data, camera=view, scene_option=scene_option)
        else:
            self.renderer.update_scene(self.data, camera="overview", scene_option=scene_option)
        return self.renderer.render().copy()

    def arm_q(self, arm: str) -> np.ndarray:
        return self.data.qpos[self.joint_qadr[arm]].copy()

    def validate_path(self, q0: np.ndarray, q1: np.ndarray, frames: int = 24,
                      arm: str = "left_arm", other_q: np.ndarray | None = None) -> list[str]:
        """Return the first unsafe interpolated configuration, with its location."""
        for index, q in enumerate(self.interpolate(q0, q1, frames)):
            issues = self.validate_q(q, arm, other_q)
            if issues:
                progress = round(index * 100 / max(1, frames - 1))
                return [f"轨迹 {progress}% 处：{issue}" for issue in issues]
        return []

    def ee_position(self, arm: str = "left_arm") -> np.ndarray:
        return self.data.site_xpos[self.site_ids[arm]].copy()

    def collision_report(self, q: np.ndarray, arm: str = "left_arm",
                         other_q: np.ndarray | None = None) -> list[str]:
        """Return robot/environment penetrations for a teaching configuration."""
        other = "right_arm" if arm == "left_arm" else "left_arm"
        self.data.qpos[self.joint_qadr[arm]] = q
        self.data.qpos[self.joint_qadr[other]] = HOME_QS[other] if other_q is None else other_q
        self.data.qvel[self.joint_dadr[arm]] = 0
        mujoco.mj_forward(self.model, self.data)
        # During path validation, a grasped object must follow its holder just
        # as it does during playback.  Leaving it at the previous frame creates
        # false link/object collisions and hides the real carried geometry.
        for holder, item_name in self.grabbed.items():
            if item_name:
                adr = self.object_qadr[item_name]
                self.data.qpos[adr:adr + 3] = self.ee_position(holder) + np.array([0, 0, -0.08])
                self.data.qpos[adr + 3:adr + 7] = np.array([1, 0, 0, 0])
        if any(self.grabbed.values()):
            mujoco.mj_forward(self.model, self.data)
        robot_bodies = {"dual_base"} | {f"{p}_{part}" for p in ("left", "right")
                        for part in ("shoulder", "link1", "link2", "link3", "link4", "link5", "ee")}
        collisions = set()
        for contact in self.data.contact:
            if contact.dist >= -0.001:
                continue
            body1 = self.model.body(self.model.geom_bodyid[contact.geom1]).name or "world"
            body2 = self.model.body(self.model.geom_bodyid[contact.geom2]).name or "world"
            expected_grasp_contact = False
            for holder, item_name in self.grabbed.items():
                if not item_name:
                    continue
                prefix = holder.replace("_arm", "")
                pair = {body1, body2}
                if f"obj_{item_name}" in pair and pair & {f"{prefix}_link5", f"{prefix}_ee"}:
                    expected_grasp_contact = True
                    break
            if expected_grasp_contact:
                continue
            # Contact between the gripper body and the task object is expected
            # at a grasp waypoint; other robot/object penetrations remain unsafe.
            if (body1.endswith("_ee") and body2.startswith("obj_")) or (body2.endswith("_ee") and body1.startswith("obj_")):
                continue
            if body1 in robot_bodies or body2 in robot_bodies:
                collisions.add(f"{body1} ↔ {body2}")
        return sorted(collisions)

    def validate_q(self, q: np.ndarray, arm: str = "left_arm",
                   other_q: np.ndarray | None = None) -> list[str]:
        issues = []
        q = np.asarray(q, dtype=float)
        if np.any(q < TEACHING_JOINT_LIMITS[:, 0]) or np.any(q > TEACHING_JOINT_LIMITS[:, 1]):
            issues.append("关节角超出教学安全范围")
        collisions = self.collision_report(q, arm, other_q)
        if collisions:
            issues.append("检测到穿模/碰撞：" + "、".join(collisions))
        ee = self.ee_position(arm)
        for axis, value in zip(("x", "y", "z"), ee):
            lo, hi = WORKSPACE_LIMITS[axis]
            if not lo <= value <= hi:
                issues.append(f"末端 {axis.upper()}={value:.3f} m 超出安全工作区 [{lo:.2f}, {hi:.2f}]")
        return issues

    def solve_ik(self, target: np.ndarray, seed: np.ndarray, arm: str = "left_arm",
                 other_q: np.ndarray | None = None) -> np.ndarray:
        joint_prefix = "L-q" if arm == "left_arm" else "R-q"
        joint_ids = np.array([self.model.joint(f"{joint_prefix}{i}").id for i in range(1, 7)])
        lower = np.maximum(self.model.jnt_range[joint_ids, 0], TEACHING_JOINT_LIMITS[:, 0])
        upper = np.minimum(self.model.jnt_range[joint_ids, 1], TEACHING_JOINT_LIMITS[:, 1])
        rng = np.random.default_rng(7)
        seeds = [np.clip(seed, lower, upper), np.clip(HOME_QS[arm], lower, upper), (lower + upper) / 2]
        seeds.extend(rng.uniform(lower, upper) for _ in range(10))
        best_q, best_error = None, float("inf")
        for initial in seeds:
            q = initial.copy()
            for _ in range(220):
                self.data.qpos[self.joint_qadr[arm]] = q
                other = "right_arm" if arm == "left_arm" else "left_arm"
                self.data.qpos[self.joint_qadr[other]] = HOME_QS[other] if other_q is None else other_q
                mujoco.mj_forward(self.model, self.data)
                error = target - self.ee_position(arm)
                error_norm = float(np.linalg.norm(error))
                if error_norm < best_error:
                    best_q, best_error = q.copy(), error_norm
                if error_norm < 0.008:
                    return q
                jacp = np.zeros((3, self.model.nv))
                jacr = np.zeros((3, self.model.nv))
                mujoco.mj_jacSite(self.model, self.data, jacp, jacr, self.site_ids[arm])
                jac = jacp[:, self.joint_dadr[arm]]
                dq = jac.T @ np.linalg.solve(jac @ jac.T + 0.003 * np.eye(3), error)
                q += np.clip(dq, -0.10, 0.10)
                q = np.clip(q, lower, upper)
        raise ValueError(f"目标位置不可达：{np.round(target, 3).tolist()}")

    def interpolate(self, q0: np.ndarray, q1: np.ndarray, frames: int = 35) -> np.ndarray:
        s = np.linspace(0, 1, frames)
        smooth = 3 * s**2 - 2 * s**3
        return q0[None, :] + smooth[:, None] * (q1 - q0)[None, :]

    def set_grab(self, item_name: str | None, arm: str = "left_arm") -> None:
        self.grabbed[arm] = item_name

    def step_to(self, q: np.ndarray, arm: str = "left_arm") -> None:
        # Position-level trajectory playback is deterministic and makes the
        # six commanded joint angles directly visible to students.
        self.data.qpos[self.joint_qadr[arm]] = q
        self.data.qvel[self.joint_dadr[arm]] = 0
        self.data.ctrl[self.actuator_adr[arm]] = q
        mujoco.mj_forward(self.model, self.data)
        for holder, item_name in self.grabbed.items():
            if item_name:
                adr = self.object_qadr[item_name]
                self.data.qpos[adr:adr + 3] = self.ee_position(holder) + np.array([0, 0, -0.08])
                self.data.qpos[adr + 3:adr + 7] = np.array([1, 0, 0, 0])
                body_id = self.model.body(f"obj_{item_name}").id
                dof = self.model.jnt_dofadr[self.model.body_jntadr[body_id]]
                self.data.qvel[dof:dof + 6] = 0
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
        start_index = len(result)
        action = step["action"]
        arm = step["args"][0] if step.get("args") and step["args"][0] in HOME_QS else "left_arm"
        if action in {"pick", "assisted-pick"}:
            held = step["args"][1] if action == "pick" else step["args"][2]
            pick_action = f"{action}({held})"
            pos = np.array(by_name[held]["position"], dtype=float)
            kind = by_name[held]["kind"]
            grasp = pos + np.array([0, 0, grasp_offset])
            if kind == "fuse":
                result.extend([
                    Waypoint("沿熔断器竖直轴线对准", np.array([pos[0], pos[1], safe_z]), False, pick_action),
                    Waypoint("沿轴线低速下降至夹持位", grasp, False, pick_action),
                    Waypoint("夹紧熔断器", grasp, True, pick_action),
                    Waypoint("辅臂保持稳定，主臂轴向拔出", np.array([pos[0], pos[1], safe_z]), True, pick_action),
                ])
            elif kind in {"terminal", "breaker"}:
                # Prefer approaching away from the pedestal, but reverse near
                # the far workspace boundary so the pre-grasp remains safe.
                direction = 1.0 if grasp[0] <= 0.60 else -1.0
                pre = grasp + np.array([direction * approach_distance, 0, 0])
                labels = {
                    "fuse": ("对准熔断器轴线", "低速接近夹持位", "夹紧熔断器", "轴向直线拔出"),
                    "terminal": ("对准端子安装方向", "精确低速接近", "轻夹接线端子", "小距离直线退出"),
                    "breaker": ("对准断路器正面", "水平接近模块", "稳定夹持模块", "正面水平退出"),
                }[kind]
                result.extend([
                    Waypoint("先移动到模块安全高度", np.array([pre[0], pre[1], safe_z]), False, pick_action),
                    Waypoint(labels[0], pre, False, pick_action),
                    Waypoint(labels[1], grasp, False, pick_action),
                    Waypoint(labels[2], grasp, True, pick_action),
                    Waypoint(labels[3], pre, True, pick_action),
                    Waypoint("提升至安全高度", np.array([pre[0], pre[1], safe_z]), True, pick_action),
                ])
            elif kind == "probe":
                side = 1.0 if arm == "left_arm" else -1.0
                result.extend([
                    Waypoint("从所选机械臂外侧接近工具区",
                             np.array([pos[0], pos[1] + side * 0.16, safe_z]), False, pick_action),
                    Waypoint("移动到验电笔中部上方", np.array([pos[0], pos[1], safe_z]), False, pick_action),
                    Waypoint("保持探头方向下降", grasp, False, pick_action),
                    Waypoint("中部夹持验电笔", grasp, True, pick_action),
                    Waypoint("辅臂保持检测区稳定，主臂安全抬升", np.array([pos[0], pos[1], safe_z]), True, pick_action),
                ])
            elif kind == "operating_rod":
                side = 1.0 if arm == "left_arm" else -1.0
                result.extend([
                    Waypoint("从所选机械臂外侧接近长工具",
                             np.array([pos[0], pos[1] + side * 0.18, safe_z]), False, f"pick({held})"),
                    Waypoint("对准绝缘操作杆重心", np.array([pos[0], pos[1], safe_z]), False, f"pick({held})"),
                    Waypoint("限制腕部旋转并下降", grasp, False, f"pick({held})"),
                    Waypoint("中部对称夹持", grasp, True, f"pick({held})"),
                    Waypoint("保持长杆方向抬升", np.array([pos[0], pos[1], safe_z]), True, f"pick({held})"),
                ])
            elif kind == "insulator":
                result.extend([
                    Waypoint("移动到绝缘子顶部", np.array([pos[0], pos[1], safe_z]), False, f"pick({held})"),
                    Waypoint("保持竖直姿态下降", grasp, False, f"pick({held})"),
                    Waypoint("稳定夹持绝缘子", grasp, True, f"pick({held})"),
                    Waypoint("竖直抬升至安全高度", np.array([pos[0], pos[1], safe_z]), True, f"pick({held})"),
                ])
            elif kind == "busbar":
                result.extend([
                    Waypoint("对准母排几何中心", np.array([pos[0], pos[1], safe_z]), False, f"pick({held})"),
                    Waypoint("保持水平姿态下降", grasp, False, f"pick({held})"),
                    Waypoint("中心低速夹持母排", grasp, True, f"pick({held})"),
                    Waypoint("水平抬升母排", np.array([pos[0], pos[1], safe_z]), True, f"pick({held})"),
                ])
            elif kind == "shield":
                result.extend([
                    Waypoint("移动到绝缘护罩上方", np.array([pos[0], pos[1], safe_z]), False, f"pick({held})"),
                    Waypoint("保持护罩平面姿态下降", grasp, False, f"pick({held})"),
                    Waypoint("夹持护罩稳定区域", grasp, True, f"pick({held})"),
                    Waypoint("保持平面姿态抬升", np.array([pos[0], pos[1], safe_z]), True, f"pick({held})"),
                ])
            else:
                result.extend([
                    Waypoint("移动到推荐抓取点上方", np.array([pos[0], pos[1], safe_z]), False, f"pick({held})"),
                    Waypoint("保持推荐姿态下降", grasp, False, f"pick({held})"),
                    Waypoint("稳定夹持", grasp, True, f"pick({held})"),
                    Waypoint("垂直安全抬升", np.array([pos[0], pos[1], safe_z]), True, f"pick({held})"),
                ])
        elif action in {"place", "insert-component", "seat-component", "assisted-place",
                        "assisted-insert", "assisted-seat", "assisted-cover", "assisted-mount"}:
            assisted = action.startswith("assisted-")
            held = step["args"][2] if assisted else step["args"][1]
            target_name = step["args"][3] if assisted else step["args"][2]
            place_action = f"{action}({held})"
            target = np.array(targets[target_name], dtype=float)
            # The target map supplies XY. Z is derived from the workbench,
            # object half-height and the gripper-to-object-center offset.
            target[2] = 0.07 + float(by_name[held]["size"][2]) + grasp_offset
            kind = by_name[held]["kind"]
            place_labels = {
                "fuse": ("移动熔断器至目标上方", "沿轴向低速就位", "松开熔断器"),
                "terminal": ("移动端子至目标上方", "精确对准目标位", "松开接线端子"),
                "breaker": ("移动断路器模块至目标", "正面低速就位", "稳定释放模块"),
                "insulator": ("竖直搬运至目标上方", "保持竖直下降", "稳定释放绝缘子"),
                "busbar": ("水平搬运母排至目标", "保持水平低速下降", "中心释放母排"),
                "shield": ("保持平面姿态移动", "平稳下降护罩", "释放绝缘护罩"),
                "probe": ("保持探头方向移动", "探头接近并短暂停留", "释放验电笔"),
                "operating_rod": ("保持长杆方向移动", "定向低速就位", "释放绝缘操作杆"),
            }.get(kind, ("移动至目标上方", "下降放置", "松开夹爪"))
            if action == "place" and kind in {"probe", "operating_rod"}:
                result.append(Waypoint("携带工具先退回该臂安全过渡位",
                                       np.array([0.52, 0.38 if arm == "left_arm" else -0.38, 0.35]),
                                       True, place_action, arm, HOME_QS[arm].copy()))
            if action in {"insert-component", "assisted-insert"}:
                support_prefix = "辅臂稳定插槽，" if assisted else ""
                pre = target + np.array([-min(0.10, approach_distance), 0, 0.025])
                result.extend([
                    Waypoint(place_labels[0], np.array([target[0], target[1], safe_z]), True, place_action),
                    Waypoint(support_prefix + "执行臂对准安装轴线", pre, True, place_action),
                    Waypoint("沿安装轴线小距离插入", target, True, place_action),
                    Waypoint(place_labels[2], target, False, place_action),
                    Waypoint("主臂沿轴线撤离", pre, False, place_action),
                ])
            elif action in {"seat-component", "assisted-seat"}:
                if kind == "insulator":
                    pre = target + np.array([0, 0, min(0.12, approach_distance + 0.02)])
                    align_label = "辅臂稳定检修座，主臂保持绝缘子竖直"
                    seat_label = "沿检修座中心线垂直落座"
                    retreat_label = "主臂垂直上升撤离"
                else:
                    pre = target + np.array([-min(0.12, approach_distance + 0.02), 0, 0.04])
                    align_label = (("辅臂稳定安装位，" if assisted else "") +
                                   "执行臂保持断路器正面姿态")
                    seat_label = "沿安装导轨正面低速推入"
                    retreat_label = "主臂沿导轨方向退出"
                result.extend([
                    Waypoint(place_labels[0], np.array([target[0], target[1], safe_z]), True, place_action),
                    Waypoint(align_label, pre, True, place_action),
                    Waypoint(seat_label, target, True, place_action),
                    Waypoint(place_labels[2], target, False, place_action),
                    Waypoint(retreat_label, pre, False, place_action),
                ])
            elif action == "assisted-mount":
                side = 1.0 if arm == "left_arm" else -1.0
                align = target + np.array([0, side * min(0.12, approach_distance + 0.02), 0.05])
                result.extend([
                    Waypoint("水平搬运母排至安装位外侧", np.array([target[0], target[1], safe_z]), True, place_action),
                    Waypoint("辅臂稳定安装架，主臂进行双点对中", align, True, place_action),
                    Waypoint("保持水平姿态侧向就位", target, True, place_action),
                    Waypoint(place_labels[2], target, False, place_action),
                    Waypoint("主臂沿母排法向撤离", align, False, place_action),
                ])
            else:
                stability_prefix = "辅臂保持目标设施稳定，" if assisted else ""
                result.extend([
                    Waypoint(place_labels[0], np.array([target[0], target[1], safe_z]), True, place_action),
                    Waypoint(stability_prefix + place_labels[1], target, True, place_action),
                    Waypoint(place_labels[2], target, False, place_action),
                    Waypoint("主臂从目标设施安全撤离", np.array([target[0], target[1], safe_z]), False, place_action),
                ])
            if action == "place" and kind in {"probe", "operating_rod"}:
                side = 1.0 if arm == "left_arm" else -1.0
                result.append(Waypoint("从工具区外侧撤离，避免回程碰到已归位工具",
                                       np.array([target[0], target[1] + side * 0.18, safe_z]),
                                       False, place_action))
            held = None
        elif action in {"test-component", "operate-component", "assisted-test", "assisted-operate"}:
            assisted = action.startswith("assisted-")
            item_name = step["args"][2] if assisted else step["args"][1]
            target_name = step["args"][3] if assisted else step["args"][2]
            target = np.array(targets[target_name], dtype=float)
            item_half_height = float(by_name[item_name]["size"][2])
            tool_tip_z = target[2] + grasp_offset + item_half_height
            if action in {"test-component", "assisted-test"}:
                support_prefix = "辅臂稳定检测座，" if assisted else ""
                contact = np.array([target[0], target[1], tool_tip_z])
                result.extend([
                    Waypoint("主臂保持验电笔探头朝向检测点",
                             contact + np.array([0, 0, 0.10]), True, f"{action}({item_name})"),
                    Waypoint(support_prefix + "探头低速接近",
                             contact + np.array([0, 0, 0.025]), True, f"{action}({item_name})"),
                    Waypoint("到达检测距离并短暂保持", contact, True,
                             f"{action}({item_name})"),
                    Waypoint("检测完成，探头竖直撤回",
                             contact + np.array([0, 0, 0.10]), True, f"{action}({item_name})"),
                ])
            else:
                support_prefix = "辅臂稳定开关座，" if assisted else ""
                contact = np.array([target[0], target[1], tool_tip_z])
                pre = contact + np.array([-min(0.10, approach_distance), 0, 0.03])
                pushed = contact + np.array([min(0.035, approach_distance / 2), 0, 0])
                result.extend([
                    Waypoint("主臂调整操作杆与开关方向一致", pre, True,
                             f"{action}({item_name})"),
                    Waypoint(support_prefix + "杆端接触操作点", contact, True,
                             f"{action}({item_name})"),
                    Waypoint("沿开关行程定向推动", pushed, True, f"{action}({item_name})"),
                    Waypoint("操作完成，沿原路回撤", pre, True, f"{action}({item_name})"),
                ])
        elif action == "stage-component":
            item_name = step["args"][1]
            target_name = step["args"][2]
            target = np.array(targets[target_name], dtype=float)
            primary_side = 1.0 if arm == "left_arm" else -1.0
            result.append(Waypoint("主臂携带部件进入目标工位上方等待位",
                                   np.array([max(0.50, target[0] - 0.04),
                                             target[1] + primary_side * 0.18,
                                             safe_z]), True,
                                   f"stage-component({item_name})"))
        elif action == "stabilize-fixture":
            target_name = step["args"][1]
            target = np.array(targets[target_name], dtype=float)
            # Approach from the assistant arm's own side, but keep the point
            # relative to the fixture.  The former absolute +/-0.20 clamp sent
            # an assistant to the wrong half of the table for several tasks.
            # The second hand braces the same station's outer frame, not the
            # insertion centre occupied by the primary gripper.  A 32 cm
            # lateral separation is needed by this compact shared-torso model
            # to prevent the two elbow/wrist chains from intersecting.
            support = _fixture_support_position(target, arm)
            facility_labels = {
                "fuse_slot": "熔断器安装槽",
                "terminal_slot": "接线端子插槽",
                "breaker_bay": "断路器安装位",
                "test_point": "电气检测点",
                "switch_point": "隔离开关操作点",
                "cover_area": "绝缘护罩覆盖区",
                "wire_strip_station": "剥线定位槽",
                "safe_area": "安全区承载面",
                "recycle_area": "回收区承载面",
                "insulator_stand": "绝缘子检修座",
                "busbar_mount": "母排安装位",
                "replacement_area": "备件区承载面",
                "inspection_area": "检修区承载面",
                "tool_area": "工具区承载面",
            }
            label = facility_labels.get(target_name, target_name)
            result.extend([
                Waypoint(f"辅臂接近{label}的稳定侧", np.array([support[0], support[1], safe_z]), False,
                         f"stabilize-fixture({target_name})"),
                Waypoint(f"辅臂闭合夹爪并保持{label}", support, True,
                         f"stabilize-fixture({target_name})"),
            ])
        elif action == "release-fixture":
            target_name = step["args"][1]
            target = np.array(targets[target_name], dtype=float)
            support = _fixture_support_position(target, arm)
            result.extend([
                Waypoint("主操作完成，辅臂释放工位支撑框", support, False,
                         f"release-fixture({target_name})"),
                Waypoint("辅臂撤回外侧安全位",
                         np.array([0.52, 0.38 if arm == "left_arm" else -0.38, 0.35]),
                         False, f"release-fixture({target_name})", arm, HOME_QS[arm].copy()),
            ])
        elif action == "hold-wire":
            item_name = step["args"][1]
            kind = by_name[item_name]["kind"]
            if kind == "wire":
                fixture = np.array(targets["wire_strip_station"], dtype=float)
                support = np.array([fixture[0] - 0.04, fixture[1], fixture[2] + grasp_offset])
                result.extend([
                    Waypoint("左臂将导线送入剥线协作区", np.array([support[0], support[1], safe_z]), True,
                             f"{action}({item_name})"),
                    Waypoint("左臂稳定导线并保持露出长度", support, True, f"{action}({item_name})"),
                ])
        elif action == "strip-wire":
            item_name = step["args"][1]
            fixture = np.array(targets["wire_strip_station"], dtype=float)
            # The left gripper holds the wire at fixture + (-0.04, 0, 0.08).
            # Put the right gripper beside its exposed end: close enough to
            # communicate stripping, with a visible safety gap between wrists.
            strip = np.array([fixture[0] + 0.040, fixture[1] - 0.145,
                              fixture[2] + grasp_offset + 0.015])
            result.extend([
                Waypoint("右臂对准导线端部", np.array([strip[0], strip[1], safe_z]), False,
                         f"strip-wire({item_name})"),
                Waypoint("闭合剥线定位槽", strip, True, f"strip-wire({item_name})"),
                Waypoint("沿导线轴向完成简化剥离", strip + np.array([0, -min(0.035, approach_distance), 0]), True,
                         f"strip-wire({item_name})"),
                Waypoint("右臂撤离剥线工位", np.array([strip[0], strip[1], safe_z]), False,
                         f"strip-wire({item_name})"),
            ])
        elif action == "insert-wire":
            item_name = step["args"][1]
            target = np.array(targets["terminal_slot"], dtype=float)
            target[2] = 0.07 + float(by_name[item_name]["size"][2]) + grasp_offset
            result.extend([
                Waypoint("左臂携带已剥线导线至端子上方", np.array([target[0], target[1], safe_z]), True,
                         f"insert-wire({item_name})"),
                Waypoint("沿端子轴线低速插入", target, True, f"insert-wire({item_name})"),
            ])
        elif action == "return-home":
            # Store the exact mirrored joint target.  Solving Home through
            # position-only IK can choose a different elbow branch and make a
            # previously safe waiting pose collide with the working arm.
            side = 1.0 if arm == "left_arm" else -1.0
            result.append(Waypoint("返回外侧安全 Home 位",
                                   np.array([0.52, side * 0.38, 0.35]), False,
                                   f"return-home({arm})", arm, HOME_QS[arm].copy()))
        for waypoint in result[start_index:]:
            waypoint.arm = arm
    return result

