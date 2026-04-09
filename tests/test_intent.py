from intent import _match_problem_index, classify_intent_hybrid


def test_empty_input_returns_unknown() -> None:
    intent, idx, fallback_used = classify_intent_hybrid("")
    assert intent == "unknown"
    assert idx is None
    assert fallback_used is False


def test_problem_index_extraction_problem_3() -> None:
    assert _match_problem_index("problem 3") == 2


def test_problem_index_extraction_q2() -> None:
    assert _match_problem_index("q2") == 1


def test_jump_to_problem_intent_detected() -> None:
    intent, idx, fallback_used = classify_intent_hybrid("jump to q3")
    assert intent == "jump_to_problem"
    assert idx == 2
    assert fallback_used is False


def test_llm_fallback_is_monkeypatched(monkeypatch) -> None:
    def _fake_fallback(_text: str) -> str:
        return "concept"

    monkeypatch.setattr("intent.classify_intent_fallback", _fake_fallback)

    intent, idx, fallback_used = classify_intent_hybrid("this message has no direct rule")
    assert intent == "concept"
    assert idx is None
    assert fallback_used is True

