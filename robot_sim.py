"""Compact 6-DOF MuJoCo arm, numerical IK and teaching trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape
import numpy as np
import mujoco

from lab_config import FACILITIES, REGIONS, STATIONS


# A visibly safe pose above the workbench rather than the model's zero pose.
HOME_Q = np.array([-0.2321, -1.1557, 1.8717, -0.4894, -1.75, 0.2970])
SAFE_Z = 0.52

# Student-facing limits are deliberately narrower than the mechanical limits.
# They keep the arm in the front/upper teaching workspace.
TEACHING_JOINT_LIMITS = np.array([
    [-1.20, 1.20], [-1.45, 0.70], [-0.25, 2.20],
    [-1.20, 1.20], [-1.75, 1.15], [-1.20, 1.20],
])
WORKSPACE_LIMITS = {"x": (0.22, 0.78), "y": (-0.36, 0.36), "z": (0.15, 0.60)}


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


def build_xml(items: list[dict], active_station: str | None = None,
              active_region: str | None = None) -> str:
    bodies = []
    for item in items:
        x, y, z = item["position"]
        bodies.append(
            f'<body name="obj_{escape(item["name"])}" pos="{x} {y} {z}">'
            f'<freejoint/>{_geom_for(item)}</body>'
        )
    fixtures = []
    station_pads = []
    region_pads = []
    for name, region in REGIONS.items():
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
    for name, facility in FACILITIES.items():
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
        fixtures.append(f'<body name="fixture_{name}" pos="{x} {y} {z}">{geom}</body>')
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
  <material name="arm" rgba="0.08 0.36 0.50 1" specular="0.35" shininess="0.25"/>
</asset>
<worldbody>
  <light pos="0.25 -0.7 1.7" dir="0.2 0.25 -1" diffuse="0.95 0.92 0.86" castshadow="true"/>
  <light pos="1.1 0.6 1.2" dir="-0.5 -0.2 -0.8" diffuse="0.40 0.52 0.62" castshadow="false"/>
  <camera name="overview" pos="1.30 -1.42 1.02" xyaxes="0.74 0.67 0 -0.36 0.40 0.84" fovy="42"/>
  <geom type="plane" size="2 2 0.1" material="floor"/>
  <body name="table" pos="0.62 0 0.035"><geom type="box" size="0.53 0.45 0.035" rgba="0.38 0.43 0.45 1"/></body>
  <body name="panel" pos="0.83 0.32 0.31"><geom type="box" size="0.025 0.16 0.27" rgba="0.18 0.22 0.24 1"/></body>
  {''.join(station_pads)}
  {''.join(region_pads)}
  {''.join(fixtures)}
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
    def __init__(self, items: list[dict], active_station: str | None = None,
                 active_region: str | None = None):
        self.items = items
        self.model = mujoco.MjModel.from_xml_string(build_xml(items, active_station, active_region))
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

    def render(self, camera: dict | None = None) -> np.ndarray:
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, height=520, width=800)
        if camera:
            view = mujoco.MjvCamera()
            mujoco.mjv_defaultCamera(view)
            view.type = mujoco.mjtCamera.mjCAMERA_FREE
            view.azimuth = float(camera.get("azimuth", 132.0))
            view.elevation = float(camera.get("elevation", -28.0))
            view.distance = float(camera.get("distance", 1.55))
            view.lookat[:] = np.asarray(camera.get("lookat", [0.45, 0.0, 0.24]), dtype=float)
            self.renderer.update_scene(self.data, camera=view)
        else:
            self.renderer.update_scene(self.data, camera="overview")
        return self.renderer.render().copy()

    def validate_path(self, q0: np.ndarray, q1: np.ndarray, frames: int = 24) -> list[str]:
        """Return the first unsafe interpolated configuration, with its location."""
        for index, q in enumerate(self.interpolate(q0, q1, frames)):
            issues = self.validate_q(q)
            if issues:
                progress = round(index * 100 / max(1, frames - 1))
                return [f"轨迹 {progress}% 处：{issue}" for issue in issues]
        return []

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
            # Contact between the gripper body and the task object is expected
            # at a grasp waypoint; other robot/object penetrations remain unsafe.
            if (body1 == "ee" and body2.startswith("obj_")) or (body2 == "ee" and body1.startswith("obj_")):
                continue
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
                labels = {
                    "fuse": ("对准熔断器轴线", "低速接近夹持位", "夹紧熔断器", "轴向直线拔出"),
                    "terminal": ("对准端子安装方向", "精确低速接近", "轻夹接线端子", "小距离直线退出"),
                    "breaker": ("对准断路器正面", "水平接近模块", "稳定夹持模块", "正面水平退出"),
                }[kind]
                result.extend([
                    Waypoint(labels[0], pre, False, f"pick({held})"),
                    Waypoint(labels[1], grasp, False, f"pick({held})"),
                    Waypoint(labels[2], grasp, True, f"pick({held})"),
                    Waypoint(labels[3], pre, True, f"pick({held})"),
                    Waypoint("提升至安全高度", np.array([pre[0], pre[1], safe_z]), True, f"pick({held})"),
                ])
            elif kind == "probe":
                result.extend([
                    Waypoint("移动到验电笔中部上方", np.array([pos[0], pos[1], safe_z]), False, f"pick({held})"),
                    Waypoint("保持探头方向下降", grasp, False, f"pick({held})"),
                    Waypoint("中部夹持验电笔", grasp, True, f"pick({held})"),
                    Waypoint("探头定向安全抬升", np.array([pos[0], pos[1], safe_z]), True, f"pick({held})"),
                ])
            elif kind == "operating_rod":
                result.extend([
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
        elif action == "place":
            held = step["args"][0]
            target = np.array(targets[step["args"][1]], dtype=float)
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
            result.extend([
                Waypoint(place_labels[0], np.array([target[0], target[1], safe_z]), True, f"place({held})"),
                Waypoint(place_labels[1], target, True, f"place({held})"),
                Waypoint(place_labels[2], target, False, f"place({held})"),
                Waypoint("安全撤离", np.array([target[0], target[1], safe_z]), False, f"place({held})"),
            ])
            held = None
    return result

