import numpy as np

from planner import Intent, make_plan
from robot_sim import HOME_Q, RobotSimulation, waypoints_from_plan


items = [
    {"name": "faulty_fuse_1", "label": "故障熔断器", "kind": "fuse", "size": (0.025, 0.025, 0.065),
     "rgba": "0.88 0.25 0.16 1", "position": (0.48, 0.02, 0.137), "location": "inspection_area"},
    {"name": "new_fuse_1", "label": "新熔断器", "kind": "fuse", "size": (0.025, 0.025, 0.065),
     "rgba": "0.20 0.75 0.32 1", "position": (0.58, -0.25, 0.137), "location": "replacement_area"},
]
targets = {"recycle_area": (0.38, -0.27, 0.14)}
plan = make_plan(items, Intent("faulty_fuse_1", "recycle_area"))
waypoints = waypoints_from_plan(plan, items, targets)
sim = RobotSimulation(items)
q = HOME_Q.copy()
print("initial ee", np.round(sim.ee_position(), 3))
for waypoint in waypoints:
    q = sim.solve_ik(waypoint.position, q)
    if waypoint.label == "闭合夹爪":
        sim.set_grab("faulty_fuse_1")
    if waypoint.label == "松开夹爪":
        sim.set_grab(None)
    start = sim.data.qpos[:6].copy()
    for q_step in sim.interpolate(start, q, frames=30):
        sim.step_to(q_step)
    print(waypoint.label, np.round(sim.ee_position(), 3), np.round(q, 3))
print("model and IK smoke test passed")
