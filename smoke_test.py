import numpy as np

from lab_config import (FACILITIES, PRESETS, REGIONS, TARGETS, TASK_PROFILES,
                        point_in_region, region_for_point)
from planner import Intent, build_problem, intent_from_problem, make_plan
from robot_sim import HOME_Q, RobotSimulation, waypoints_from_plan


items = [
    {"name": "faulty_fuse_1", "label": "故障熔断器", "kind": "fuse", "size": (0.025, 0.025, 0.065),
     "rgba": "0.88 0.25 0.16 1", "position": (0.48, 0.02, 0.137), "location": "inspection_area"},
    {"name": "new_fuse_1", "label": "新熔断器", "kind": "fuse", "size": (0.025, 0.025, 0.065),
     "rgba": "0.20 0.75 0.32 1", "position": (0.58, -0.25, 0.137), "location": "replacement_area"},
]
targets = {"recycle_area": (0.38, -0.27, 0.14)}
plan = make_plan(items, Intent("faulty_fuse_1", "recycle_area"))
problem = build_problem(items, Intent("faulty_fuse_1", "recycle_area"))
assert intent_from_problem(problem, items, targets) == Intent("faulty_fuse_1", "recycle_area")
waypoints = waypoints_from_plan(plan, items, targets)
sim = RobotSimulation(items)
assert len(FACILITIES) >= 6
assert sim.render({"azimuth": 90, "elevation": -45, "distance": 1.4,
                   "lookat": [0.45, 0.0, 0.2]}).shape == (520, 800, 3)
assert not sim.validate_path(HOME_Q, HOME_Q)
for region_name, region in REGIONS.items():
    x, y = region["xy"]
    assert point_in_region(x, y, region_name)
    assert region_for_point(x, y) == region_name
    assert TARGETS[region_name][:2] == region["xy"], f"stale target for {region_name}"
q = HOME_Q.copy()
was_gripping = False
print("initial ee", np.round(sim.ee_position(), 3))
for waypoint in waypoints:
    q = sim.solve_ik(waypoint.position, q)
    if waypoint.grip and not was_gripping:
        sim.set_grab("faulty_fuse_1")
    if not waypoint.grip and was_gripping:
        sim.set_grab(None)
    was_gripping = waypoint.grip
    start = sim.data.qpos[:6].copy()
    for q_step in sim.interpolate(start, q, frames=30):
        sim.step_to(q_step)
    print(waypoint.label, np.round(sim.ee_position(), 3), np.round(q, 3))
released_adr = sim.object_qadr["faulty_fuse_1"]
released_position = sim.data.qpos[released_adr:released_adr + 3].copy()
for q_step in sim.interpolate(q, HOME_Q, frames=20):
    sim.step_to(q_step)
assert np.allclose(sim.data.qpos[released_adr:released_adr + 3], released_position), "released object followed arm"
print("model and IK smoke test passed")

# Every fixed teaching facility must be reachable from its object's recommended
# starting region through the full differentiated waypoint template.
for preset_name, preset in PRESETS.items():
    profile = TASK_PROFILES[preset["kind"]]
    target_name = profile["facility"]
    source_xy = REGIONS[preset["region"]]["xy"]
    item = {"name": f"test_{preset['kind']}", "label": preset_name, "preset": preset_name,
            "kind": preset["kind"], "size": preset["size"], "rgba": preset["rgba"],
            "position": (source_xy[0], source_xy[1], 0.07 + preset["size"][2] + 0.002),
            "location": preset["region"]}
    facility_plan = make_plan([item], Intent(item["name"], target_name))
    facility_waypoints = waypoints_from_plan(facility_plan, [item], TARGETS)
    facility_sim = RobotSimulation([item])
    facility_q = HOME_Q.copy()
    for index, waypoint in enumerate(facility_waypoints):
        next_q = facility_sim.solve_ik(waypoint.position, facility_q)
        issues = facility_sim.validate_path(facility_q, next_q, frames=24)
        assert not issues, f"{preset_name} -> {target_name} step {index + 1}: {issues}"
        facility_q = next_q
print("all fixed-facility teaching paths passed")

semantic_item = {"name": "region_test_fuse", "label": "熔断器", "preset": "熔断器",
                 "kind": "fuse", "size": PRESETS["熔断器"]["size"],
                 "rgba": PRESETS["熔断器"]["rgba"],
                 "position": (*REGIONS["inspection_area"]["xy"], 0.137),
                 "location": "inspection_area"}
for region_name in REGIONS:
    if region_name == "inspection_area":
        continue
    region_plan = make_plan([semantic_item], Intent(semantic_item["name"], region_name))
    region_waypoints = waypoints_from_plan(region_plan, [semantic_item], TARGETS)
    region_sim = RobotSimulation([semantic_item], active_region=region_name)
    region_q = HOME_Q.copy()
    for index, waypoint in enumerate(region_waypoints):
        next_q = region_sim.solve_ik(waypoint.position, region_q)
        issues = region_sim.validate_path(region_q, next_q, frames=24)
        assert not issues, f"semantic target {region_name} step {index + 1}: {issues}"
        region_q = next_q
print("all semantic-region targets passed")
