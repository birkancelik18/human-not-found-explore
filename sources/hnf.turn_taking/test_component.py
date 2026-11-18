"""Tests for the turn-taking rules. Run: python -m pytest -q (from this folder)."""

import component as rules

GROUP = [{"id": f"p{i}", "display_name": f"P{i}", "role": "participant"} for i in (1, 2, 3)]
MOD = {"id": "m", "display_name": "Moderator", "role": "moderator"}
BASE = {"action_type": "discussion.message", "max_turns": 12, "finish": True}


def simulate(rule, people, config=None, text=lambda actor, n: "word " * 3, bid=lambda actor, n: False,
             pass_to=lambda actor, n: "anyone", seed=7, limit=300):
    """Play the engine: answer open offers in the order they were made, turn invites into messages.

    Returns (speakers in order, turn.status payloads, finished, every effect)."""
    config = {**BASE, **(config or {})}
    state, queue, speakers, statuses, every = {}, [], [], [], []
    events = [{"topic": "run.started"}]
    for _ in range(limit):
        if not events:
            if not queue:
                return speakers, statuses, False, every
            offer = queue.pop(0)
            action = offer["actions"][0]
            n = len(speakers)
            value = bid(offer["actor_id"], n) if action["type"] == "turn.request" else pass_to(offer["actor_id"], n)
            events.append({"topic": "action.accepted", "actor_id": offer["actor_id"], "offer_id": offer["id"],
                           "action_type": action["type"], "payload": value, "own": True})
        event = events.pop(0)
        own = event.pop("own", False)
        result = rule({"event": event, "participants": people, "config": config, "state": state, "seed": seed,
                       "own_event": own, "shared_state": {}, "limits": {}})
        for effect in result["effects"]:
            every.append(effect)
            kind = effect["type"]
            if kind == "update":
                state = effect["state"]
            elif kind == "offer":
                queue.append(effect)
            elif kind == "cancel_offer":
                queue = [item for item in queue if item["id"] != effect["id"]]
            elif kind == "finish":
                return speakers, statuses, True, every
            elif kind == "emit" and effect["topic"] == "turn.status":
                statuses.append(effect["payload"])
            elif kind == "emit" and effect["topic"] == "discussion.invite":
                actor = effect["payload"]["actor_id"]
                speakers.append(actor)
                events.append({"topic": "action.accepted", "actor_id": actor, "offer_id": "speak",
                               "action_type": "discussion.message", "payload": text(actor, len(speakers))})
    raise AssertionError("the rule never finished")


# Least active next -------------------------------------------------------

def test_least_active_invites_quietest():
    words = {"p1": "w " * 10, "p2": "w " * 2, "p3": "w " * 5}
    speakers, *_ = simulate(rules.least_active, GROUP, {"max_turns": 4}, text=lambda actor, n: words[actor])
    first = speakers[0]
    assert sorted(speakers[:3]) == ["p1", "p2", "p3"]  # nobody speaks twice before everyone spoke once
    assert speakers[3] == "p2"  # then the one with the fewest words
    assert first in ("p1", "p2", "p3")


def test_least_active_finishes_after_max_turns():
    speakers, _, finished, _ = simulate(rules.least_active, GROUP, {"max_turns": 2})
    assert finished and len(speakers) == 2


def test_least_active_skips_moderator_unless_it_asks():
    speakers, *_ = simulate(rules.least_active, [MOD] + GROUP, {"max_turns": 6})
    assert "m" not in speakers
    speakers, *_ = simulate(rules.least_active, [MOD] + GROUP, {"max_turns": 6}, bid=lambda actor, n: n == 2)
    assert speakers[2] == "m" and speakers.count("m") == 1


def test_moderator_is_asked_privately_after_each_member_message():
    *_, every = simulate(rules.least_active, [MOD] + GROUP, {"max_turns": 3})
    asks = [effect for effect in every if effect["type"] == "offer"]
    assert len(asks) == 2  # after the first and second messages; the third ends the step
    assert all(effect["actor_id"] == "m" and effect["actions"][0]["type"] == "turn.request"
               and effect["actions"][0]["audience"] == ["m"] for effect in asks)


def test_status_counts_group_only():
    _, statuses, *_ = simulate(rules.least_active, [MOD] + GROUP, {"max_turns": 4},
                               bid=lambda actor, n: n == 1, text=lambda actor, n: "one two")
    last = statuses[-1]
    assert set(last["messages"]) == {"p1", "p2", "p3"} and sum(last["messages"].values()) == 3
    assert last["words"] == {key: 2 * count for key, count in last["messages"].items()}
    assert last["turn"] == 4 and last["last_message"] == "one two"


def test_no_moderator_means_no_offers():
    *_, every = simulate(rules.least_active, GROUP, {"max_turns": 5})
    assert not [effect for effect in every if effect["type"] == "offer"]


# Group balance ------------------------------------------------------------

def record(actor, words, step="discuss"):
    return {"event_type": "action_applied", "actor_id": actor, "step_id": step,
            "payload": {"action_type": "discussion.message", "value": "w " * words}}


def balance(records, people=None, step=""):
    return rules.group_balance({"config": {"action_type": "discussion.message", "step": step},
                                "experiment": {"participants": people or [MOD] + GROUP},
                                "authorized_events": records})


def test_group_balance_excludes_moderators():
    result = balance([record("p1", 5), record("p2", 5), record("p3", 5), record("m", 50)])
    assert result["status"] == "ok" and result["value"] == 1.0
    assert "m" not in result["details"]["words"]


def test_group_balance_counts_silent_members():
    result = balance([record("p1", 5)])
    assert result["value"] == 0 and result["details"]["messages"]["p3"] == 0


def test_group_balance_missing_without_messages():
    assert balance([], step="discuss")["status"] == "missing"


def test_self_test():
    assert rules.self_test() == {"ok": True}
