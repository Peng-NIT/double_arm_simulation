import streamlit as st

from lab_config import TARGETS
from lab_state import nav, page_header
from llm_client import generate_learning_hint, parse_intent_with_chatgpt
from planner import DOMAIN_PDDL, build_problem, heuristic_intent, make_plan, plan_as_text

st.set_page_config(page_title="2 PDDL规划", page_icon="⚡", layout="wide")
page_header(2, "2. 自然语言与 PDDL 规划")

if not st.session_state["items"]:
    st.error("场景中还没有物体，请先返回场景配置页面。")
else:
    instruction = st.text_area("自然语言检修任务", "将故障熔断器放入回收区", height=90)
    use_llm = st.checkbox("使用 ChatGPT 解析", value=True)
    if st.button("生成 PDDL 与计划", type="primary"):
        try:
            intent = (parse_intent_with_chatgpt(instruction, st.session_state["items"], TARGETS)
                      if use_llm else heuristic_intent(instruction, st.session_state["items"], TARGETS))
            st.session_state["intent"] = intent
            st.session_state["problem"] = build_problem(st.session_state["items"], intent)
            st.session_state["plan"] = make_plan(st.session_state["items"], intent)
            st.session_state["waypoints"] = []
            st.session_state["run_result"] = None
            st.success("PDDL 与动作计划已生成。")
        except Exception as exc:
            st.error(str(exc))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Problem PDDL")
        edited = st.text_area("可修改 PDDL", st.session_state["problem"] or "; 请先生成 PDDL", height=350)
        if st.button("保存 PDDL 修改"):
            st.session_state["problem"] = edited
            st.success("已保存。教学版规划器仍使用当前结构化目标生成动作。")
    with col2:
        tabs = st.tabs(["Domain PDDL", "动作计划", "AI 学习提示"])
        with tabs[0]:
            st.code(DOMAIN_PDDL, language="lisp")
        with tabs[1]:
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
nav("pages/1_场景配置.py", "pages/3_运动参数.py")
