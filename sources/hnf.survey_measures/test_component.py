"""Tests for the survey measures. Run: python -m pytest -q (from this folder)."""

import component as mod


def said(actor, step, value):
    return {"event_type": "action_applied", "step_id": step, "actor_id": actor,
            "payload": {"action_type": "questionnaire.answers", "value": value}}


def run(function, config, events):
    return function({"config": config, "authorized_events": events})


def test_self_test():
    assert mod.self_test()["ok"]


def test_contrast_uses_prefixes_and_latest_answers():
    events = [said("p1", "s", {"true_a": 1, "false_a": 1}), said("p1", "s", {"true_a": 4, "false_a": 2, "false_b": 1}),
              said("p1", "other", {"true_a": 1, "false_a": 4})]
    result = run(mod.item_contrast, {"step": "s", "group_a": ["true_"], "group_b": ["false_a", "false_b"]}, events)
    assert result["value"] == 2.5 and result["details"]["mean_b"] == 1.5


def test_contrast_missing_without_both_groups():
    assert run(mod.item_contrast, {"step": "", "group_a": ["x"], "group_b": ["y"]}, [said("p1", "s", {"x": 1})])["status"] == "missing"


def test_accuracy_compares_as_text():
    events = [said("p1", "s", {"q1": "8", "q2": 0}), said("p2", "s", {"q1": "7", "q2": 9})]
    result = run(mod.answer_key_accuracy, {"step": "s", "answer_key": [{"item": "q1", "answer": "8"}, {"item": "q2", "answer": "0"}]}, events)
    assert result["value"] == 0.5 and result["details"]["by_item"] == {"q1": 0.5, "q2": 0.5}


def test_weight_of_advice_truncates_and_skips_undefined():
    events = [said("p1", "a", {"w": 100, "v": 50}), said("p1", "b", {"w": 250, "v": 60})]
    config = {"first_step": "a", "final_step": "b", "advice": [{"item": "w", "value": 200}, {"item": "v", "value": 50}]}
    assert run(mod.weight_of_advice, {**config, "truncate": True}, events)["value"] == 1.0
    assert run(mod.weight_of_advice, {**config, "truncate": False}, events)["value"] == 1.5


def test_step_change_numeric_mean():
    events = [said("p1", "a", {"i": 2}), said("p1", "b", {"i": 5})]
    assert run(mod.step_change, {"item": "i", "target": "", "before_step": "a", "after_step": "b"}, events)["value"] == 3.0
