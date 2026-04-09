from state import TeachingFlowState, TeachingState, apply_transition


def test_state_transition_flow_sequence() -> None:
    state = TeachingState()

    apply_transition(state, "greeting")
    assert state.current_state == TeachingFlowState.OVERVIEW
    assert state.last_user_intent == "greeting"

    apply_transition(state, "overview")
    assert state.current_state == TeachingFlowState.OVERVIEW

    apply_transition(state, "example")
    assert state.current_state == TeachingFlowState.EXAMPLE_SELECTED

    apply_transition(state, "next_step")
    assert state.current_state == TeachingFlowState.STEP_BY_STEP
    assert state.current_step_index == 1

    apply_transition(state, "hint")
    assert state.current_state == TeachingFlowState.HINT
    assert state.hint_mode is True
    assert state.hint_level == 1

    apply_transition(state, "full_solution")
    assert state.current_state == TeachingFlowState.FULL_SOLUTION
    assert state.hint_mode is False


def test_hint_level_is_capped_at_three() -> None:
    state = TeachingState()
    for _ in range(10):
        apply_transition(state, "hint")
    assert state.hint_level == 3


def test_jump_to_problem_resets_step_index() -> None:
    state = TeachingState(current_step_index=4, current_problem_index=0)

    apply_transition(state, "jump_to_problem", target_problem_index=2)

    assert state.current_state == TeachingFlowState.EXAMPLE_SELECTED
    assert state.current_problem_index == 2
    assert state.current_step_index == 0

