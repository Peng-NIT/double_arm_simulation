import streamlit as st
import streamlit.components.v1 as components

from html_explainer import render_explanation
from lab_config import (ARM_ROLES, FACILITIES, REGIONS, STATIONS, TARGETS, TASK_MODES,
                        TASK_PROFILES)
from lab_state import help_heading, invalidate_after_plan_change, nav, page_header, require_login
from llm_client import generate_deep_explanation, generate_learning_hint, parse_intent_with_chatgpt
from planner import DOMAIN_PDDL, build_problem, heuristic_intent, intent_from_problem, make_plan, plan_as_text

st.set_page_config(page_title="2 PDDL规划", page_icon="⚡", layout="wide")
require_login()
page_header(2, "2. 自然语言与 PDDL 规划")

if not st.session_state["items"]:
    st.error("场景中还没有物体，请先返回场景配置页面。")
else:
    task_rows = []
    for item in st.session_state["items"]:
        profile = TASK_PROFILES[item["kind"]]
        facility = FACILITIES[profile["facility"]]
        station = STATIONS[facility["station"]]
        region = REGIONS[item["location"]]
        task_rows.append({"操作对象": item["name"],
                          "初始区域": f"{region['color']}{region['label']}",
                          "目标工位": f"{station['color']}{station['label']}",
                          "固定设施": facility["label"],
                          "推荐任务": profile["task"],
                          "执行模式": "双臂必须" if TASK_MODES[item["kind"]] == "dual" else "单臂可选",
                          "机械臂分工": ARM_ROLES[item["kind"]],
                          "检修动作展开": profile["pddl"], "重点参数": profile["focus"]})
    st.dataframe(task_rows, hide_index=True, width="stretch")
    selected_name = st.selectbox("当前规划对象", [item["name"] for item in st.session_state["items"]],
        format_func=lambda name: next(f"{item['label']}（{name}）" for item in st.session_state["items"] if item["name"] == name),
        help="先选择本次要规划的物体，执行模式由该物体的任务类型决定。")
    selected_item = next(item for item in st.session_state["items"] if item["name"] == selected_name)
    selected_profile = TASK_PROFILES[selected_item["kind"]]
    selected_mode = TASK_MODES[selected_item["kind"]]
    if selected_mode == "single":
        recommended_arm = ("left_arm" if TARGETS[selected_profile["facility"]][1] >= 0
                           else "right_arm")
        selected_arm = st.radio(
            "单臂执行选择", ["left_arm", "right_arm"], horizontal=True,
            index=0 if recommended_arm == "left_arm" else 1,
            format_func=lambda arm: "左臂" if arm == "left_arm" else "右臂",
            help="选择后会重新进行IK、轨迹和碰撞检查；另一条机械臂保持Home位。",
            key=f"execution_arm_{selected_name}",
        )
        st.caption(f"该任务可单臂完成；根据工位位置推荐{'左臂' if recommended_arm == 'left_arm' else '右臂'}。")
    else:
        selected_arm = None
        lock_left, lock_right = st.columns(2)
        lock_left.button("左臂（不可单选）", disabled=True, width="stretch")
        lock_right.button("右臂（不可单选）", disabled=True, width="stretch")
        st.info("该任务必须双臂协作，左臂/右臂单选已锁定。PDDL规划必须包含两臂的有效动作。")
    instruction = st.text_area(
        "自然语言检修任务", selected_profile["task"], height=90,
        help="请明确写出场景中的物体和目标区域。大语言模型只会从当前场景允许的对象中选择。",
    )
    use_llm = st.checkbox("使用大语言模型解析", value=True, help="关闭后使用本地关键词解析。")
    if st.button("生成 PDDL 与计划", type="primary"):
        try:
            intent = (parse_intent_with_chatgpt(instruction, st.session_state["items"], TARGETS)
                      if use_llm else heuristic_intent(instruction, st.session_state["items"], TARGETS))
            if intent.item != selected_name:
                raise ValueError(f"识别到的物体 {intent.item} 与当前规划对象 {selected_name} 不一致，请修改指令或切换对象。")
            invalidate_after_plan_change()
            st.session_state["intent"] = intent
            st.session_state["execution_arm"] = selected_arm
            st.session_state["problem"] = build_problem(st.session_state["items"], intent)
            st.session_state["plan"] = make_plan(st.session_state["items"], intent, selected_arm)
            st.success("PDDL 与动作计划已生成。")
        except Exception as exc:
            st.error(str(exc))

    with st.expander("Domain、Problem 与 Plan 是什么关系？"):
        st.markdown(
            "**Domain PDDL** 定义左右机械臂能做什么，例如 `pick`、`stabilize-fixture`、`assisted-insert`、`assisted-test` 和 `strip-wire`。  \n"
            "**Problem PDDL** 定义“本次实验有什么、从哪里开始、要到哪里”。  \n"
            "**Plan** 同时说明哪条机械臂执行动作，是从符号任务到双臂连续运动的接口。"
        )

    col1, col2 = st.columns(2)
    with col1:
        help_heading("Problem PDDL", "定义本次实验的物体、初始区域和目标；修改 goal 会改变规划结果。")
        edited = st.text_area(
            "可修改 PDDL", st.session_state["problem"] or "; 请先生成 PDDL", height=350,
            help="支持修改 (:goal (at 物体 目标区域))；保存时会检查括号、物体和区域。",
        )
        if st.button("保存并重新规划"):
            try:
                intent = intent_from_problem(edited, st.session_state["items"], TARGETS)
                invalidate_after_plan_change()
                st.session_state["problem"] = edited
                st.session_state["intent"] = intent
                planned_item = next(item for item in st.session_state["items"] if item["name"] == intent.item)
                arm = st.session_state.get("execution_arm") if TASK_MODES[planned_item["kind"]] == "single" else None
                st.session_state["plan"] = make_plan(st.session_state["items"], intent, arm)
                st.success("修改已通过检查，计划与后续运动状态已更新。")
            except Exception as exc:
                st.error(f"PDDL 未保存：{exc}")
    with col2:
        tabs = st.tabs(["Domain PDDL", "动作计划", "AI 学习提示"])
        with tabs[0]:
            help_heading("Domain PDDL", "定义共用的谓词、动作、前置条件和效果；本页只读。", 5)
            st.code(DOMAIN_PDDL, language="lisp")
        with tabs[1]:
            help_heading("Plan", "离散动作序列，下一页会把它展开为连续路点。", 5)
            st.code(plan_as_text(st.session_state["plan"]) or "; 尚未生成计划", language="text")
        with tabs[2]:
            level = st.selectbox("提示难度", ["基础", "进阶", "挑战"])
            if st.button("生成学习提示", disabled=not bool(st.session_state["problem"])):
                try:
                    st.session_state["learning_hint"] = generate_learning_hint(
                        st.session_state["problem"], st.session_state["items"], list(TARGETS), level)
                except Exception as exc:
                    st.error(str(exc))
            if st.session_state.get("learning_hint"):
                st.info(st.session_state["learning_hint"])

    st.divider()
    help_heading("AI 可视化深度解读", "仅根据当前 Domain、Problem 和 Plan 生成课程范围内的结构化讲解。", 3)
    explain_left, explain_right = st.columns([1, 1.7])
    with explain_left:
        question = st.text_input(
            "想重点了解什么？（可选）",
            placeholder="例如：修改 goal 后为什么计划会改变？",
            help="只回答本实验的 PDDL、6DOF、轨迹、MuJoCo 和强电检修对象问题。",
        )
        if st.button("✦ 生成可视化深度解读", type="primary", width="stretch",
                     disabled=not bool(st.session_state["problem"] and st.session_state["plan"])):
            context = (f"Domain PDDL:\n{DOMAIN_PDDL}\n\nProblem PDDL:\n{st.session_state['problem']}"
                       f"\n\nPlan:\n{plan_as_text(st.session_state['plan'])}")
            try:
                with st.status("正在生成教学解读…", expanded=True) as status:
                    st.write("1/3 解析 Domain 与 Problem 关系")
                    draft = generate_deep_explanation("PDDL 规划", context, question)
                    st.write("2/3 检查课程边界与内容结构")
                    st.session_state["deep_explanation_text"] = draft
                    st.write("3/3 生成可视化讲解页")
                    st.session_state["deep_explanation_html"] = render_explanation(draft)
                    status.update(label="深度解读已生成", state="complete", expanded=False)
            except Exception as exc:
                st.error(f"可视化解读生成失败：{exc}")
    with explain_right:
        if st.session_state.get("deep_explanation_html"):
            components.html(st.session_state["deep_explanation_html"], height=720, scrolling=True)
        elif st.session_state.get("deep_explanation_text"):
            st.markdown(st.session_state["deep_explanation_text"])
        else:
            st.info("生成后，这里将显示可独立滚动的结构化教学页面。")

st.divider()
nav("pages/1_场景配置.py", "pages/3_运动参数.py")
