"""Tests for the AI moderator. Run: python -m pytest -q (from this folder)."""

import pytest

import component as mod

PEOPLE = [{"id": "m", "display_name": "Moderator", "role": "moderator"},
          {"id": "p1", "display_name": "Ana", "role": "participant"},
          {"id": "p2", "display_name": "Ben", "role": "participant", "attributes": {"expertise": "astronomy"}},
          {"id": "p3", "display_name": "Cleo", "role": "participant"}]
CONFIG = {"model_ref": "default", "balance": True, "civility": True, "expertise": False, "balance_threshold": 0.3,
          "persona": "", "instructions": ""}
REQUEST = {"type": "turn.request", "prompt": "Speak next?", "schema": {"type": "boolean"}}
PASS = {"type": "turn.pass", "prompt": "Who next?", "schema": {"enum": ["p1", "p2", "p3", "anyone"]}}
MESSAGE = {"type": "discussion.message", "prompt": "Discuss.", "schema": {"type": "string"}}


def status(words, last="I think oxygen first."):
    return {"topic": "turn.status", "payload": {"speaker": "p1", "turn": 3, "words": words,
                                                "messages": {key: 1 for key in words}, "last_message": last}}


def said(actor, text):
    return {"topic": "action.accepted", "actor_id": actor, "action_type": "discussion.message", "payload": text}


def decide(action, memory, **config):
    return mod.moderator({"invocation_id": "a1", "seed": 1, "state": {}, "config": {**CONFIG, **config},
                          "observation": {"participant_id": "m", "participant_name": "Moderator", "role": "moderator",
                                          "participants": PEOPLE, "memory": memory, "allowed_actions": [action]}})


UNEVEN = [status({"p1": 40, "p2": 2, "p3": 30})]
EVEN = [status({"p1": 10, "p2": 10, "p3": 10})]


def test_gini():
    assert mod.gini([1, 1, 1]) == 0 and mod.gini([0, 0, 0]) == 0
    assert mod.gini([0, 0, 9]) == pytest.approx(2 / 3)


def test_bids_yes_without_model_when_unbalanced():
    reply = decide(REQUEST, UNEVEN)
    assert reply == {"invocation_id": "a1", "action_type": "turn.request", "payload": True}


def test_bid_asks_model_for_civility_when_balanced():
    reply = decide(REQUEST, EVEN)
    assert reply["request_model"] is True and "disrespectful" in reply["action_prompt"]


def test_bid_no_when_all_goals_off():
    reply = decide(REQUEST, UNEVEN, balance=False, civility=False)
    assert reply["payload"] is False and "request_model" not in reply


def test_pass_names_quietest():
    assert decide(PASS, UNEVEN)["payload"] == "p2"


def test_pass_asks_model_with_expertise():
    reply = decide(PASS, UNEVEN, expertise=True)
    assert reply["request_model"] is True and "astronomy" in reply["system"]


def test_message_prompt_names_quietest_when_unbalanced():
    reply = decide(MESSAGE, UNEVEN)
    assert reply["request_model"] is True and "Invite Ben" in reply["system"]


def test_message_without_trigger_facilitates():
    reply = decide(MESSAGE, EVEN, civility=False)
    assert "sum up" in reply["system"] and "Invite" not in reply["system"]


def test_falls_back_to_memory_counts():
    memory = [said("p1", "w " * 30), said("p3", "w " * 30), said("p2", "w")]
    assert decide(PASS, memory)["payload"] == "p2"
    assert "Invite Ben" in decide(MESSAGE, memory)["system"]


def test_moderator_messages_are_not_counted():
    memory = [said("m", "w " * 100), said("p1", "w " * 5), said("p2", "w " * 5), said("p3", "w " * 5)]
    assert decide(REQUEST, memory, civility=False)["payload"] is False


def test_unknown_action_goes_to_model():
    reply = decide({"type": "ranking.submit", "prompt": "Rank.", "schema": {"type": "array"}}, UNEVEN)
    assert reply["request_model"] is True and reply["system"].startswith("You are the moderator")


def test_self_test():
    assert mod.self_test() == {"ok": True}
