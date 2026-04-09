from intent import classify_intent_hybrid
from state import TeachingFlowState, TeachingState, apply_transition


def _run_script(script):
    state = TeachingState()
    for turn in script:
        intent, problem_idx, _fallback = classify_intent_hybrid(
            turn["text"],
            enable_llm_fallback=False,
        )
        apply_transition(state, intent, problem_idx)
        assert intent == turn["expect_intent"]
        assert state.current_state == turn["expect_state"]
        if "expect_hint_level" in turn:
            assert state.hint_level == turn["expect_hint_level"]
        if "expect_step_index" in turn:
            assert state.current_step_index == turn["expect_step_index"]
    return state


def test_flow_a_main_learning_path() -> None:
    script = [
        {"text": "hi", "expect_intent": "greeting", "expect_state": TeachingFlowState.OVERVIEW},
        {"text": "what are we learning today", "expect_intent": "overview", "expect_state": TeachingFlowState.OVERVIEW},
        {"text": "go through an example", "expect_intent": "example", "expect_state": TeachingFlowState.EXAMPLE_SELECTED},
        {"text": "next step", "expect_intent": "next_step", "expect_state": TeachingFlowState.STEP_BY_STEP, "expect_step_index": 1},
        {"text": "hint please", "expect_intent": "hint", "expect_state": TeachingFlowState.HINT, "expect_hint_level": 1},
        {"text": "full solution", "expect_intent": "full_solution", "expect_state": TeachingFlowState.FULL_SOLUTION, "expect_hint_level": 1},
    ]
    _run_script(script)


def test_flow_b_jump_resets_step() -> None:
    script = [
        {"text": "go through an example", "expect_intent": "example", "expect_state": TeachingFlowState.EXAMPLE_SELECTED},
        {"text": "next step", "expect_intent": "next_step", "expect_state": TeachingFlowState.STEP_BY_STEP, "expect_step_index": 1},
        {"text": "jump to q3", "expect_intent": "jump_to_problem", "expect_state": TeachingFlowState.EXAMPLE_SELECTED, "expect_step_index": 0},
    ]
    state = _run_script(script)
    assert state.current_problem_index == 2


def test_flow_c_ambiguous_goes_unknown_without_fallback() -> None:
    intent, idx, fallback_used = classify_intent_hybrid(
        "something random and off-topic",
        enable_llm_fallback=False,
    )
    assert intent == "unknown"
    assert idx is None
    assert fallback_used is False

