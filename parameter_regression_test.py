"""Regression coverage for every user-editable motion-geometry boundary.

Run with: ``python parameter_regression_test.py`` inside the pytorch environment.
"""

from __future__ import annotations

import itertools

import numpy as np

from lab_config import (PRESETS, REGIONS, TARGETS, TASK_MODES, TASK_PROFILES,
                        generate_hazard_zones)
from planner import Intent, make_plan
from robot_sim import HOME_QS, RobotSimulation, waypoints_from_plan


RELEASE_ACTIONS = ("place(", "insert-component(", "seat-component(",
                   "assisted-place(", "assisted-insert(", "assisted-seat(",
                   "assisted-cover(", "assisted-mount(")


def make_item(preset_name: str) -> dict:
    preset = PRESETS[preset_name]
    x, y = REGIONS[preset["region"]]["xy"]
    return {
        "name": f"regression_{preset['kind']}", "label": preset_name,
        "preset": preset_name, "kind": preset["kind"], "size": preset["size"],
        "rgba": preset["rgba"], "position": (x, y, 0.072 + preset["size"][2]),
        "location": preset["region"],
    }


def execute_case(preset_name: str, selected_arm: str | None, motion: dict,
                 hazard_level: str, hazard_seed: int, linear: bool) -> None:
    item = make_item(preset_name)
    target = TASK_PROFILES[item["kind"]]["facility"]
    plan = make_plan([item], Intent(item["name"], target), selected_arm)
    task_hazards = generate_hazard_zones(target, hazard_seed, hazard_level, item["position"])
    waypoints = waypoints_from_plan(plan, [item], TARGETS, motion, task_hazards)
    sim = RobotSimulation([item], active_facility=target,
                          hazards=task_hazards)
    current = {arm: q.copy() for arm, q in HOME_QS.items()}
    for index, waypoint in enumerate(waypoints):
        arm = waypoint.arm
        other = "right_arm" if arm == "left_arm" else "left_arm"
        try:
            target_q = (waypoint.joint_target.copy() if waypoint.joint_target is not None else
                        sim.solve_ik(waypoint.position, current[arm], arm, current[other]))
        except Exception as exc:
            raise AssertionError(
                f"{preset_name}/{selected_arm or 'dual'} step {index + 1}; "
                f"motion={motion}; level={hazard_level}; seed={hazard_seed}: {exc}"
            ) from exc
        path = (np.linspace(current[arm], target_q, 24) if linear else
                sim.interpolate(current[arm], target_q, 24))
        for frame, q in enumerate(path):
            issues = sim.validate_q(q, arm, current[other])
            assert not issues, (
                f"{preset_name}/{selected_arm or 'dual'} step {index + 1} frame {frame + 1}; "
                f"motion={motion}; level={hazard_level}; seed={hazard_seed}; "
                f"linear={linear}: {issues}"
            )
        sim.step_to(target_q, arm)
        if (waypoint.pddl_action.startswith(("pick(", "assisted-pick("))
                and waypoint.grip and sim.grabbed[arm] is None):
            sim.set_grab(item["name"], arm)
        if (waypoint.pddl_action.startswith(RELEASE_ACTIONS)
                and not waypoint.grip and sim.grabbed[arm] is not None):
            sim.set_grab(None, arm)
        current[arm] = target_q


def main() -> None:
    # Nominal settings plus all eight corners of the three geometry sliders.
    motions = [{"safe_z": 0.52, "grasp_offset": 0.08, "approach_distance": 0.10}]
    motions.extend({"safe_z": z, "grasp_offset": grasp, "approach_distance": approach}
                   for z, grasp, approach in itertools.product(
                       (0.48, 0.52), (0.075, 0.09), (0.08, 0.14)))
    modes = []
    for preset_name, preset in PRESETS.items():
        if TASK_MODES[preset["kind"]] == "single":
            modes.extend((preset_name, arm) for arm in HOME_QS)
        else:
            modes.append((preset_name, None))

    count = 0
    levels = ("低", "中", "高")
    for motion_index, motion in enumerate(motions):
        for mode_index, (preset_name, selected_arm) in enumerate(modes):
            level = levels[(motion_index + mode_index) % len(levels)]
            execute_case(preset_name, selected_arm, motion, level,
                         1200 + motion_index * 100 + mode_index,
                         linear=(motion_index + mode_index) % 2 == 0)
            count += 1
    print(f"parameter regression passed: {count} complete task executions")


if __name__ == "__main__":
    main()
