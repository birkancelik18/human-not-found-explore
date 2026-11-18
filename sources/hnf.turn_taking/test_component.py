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


# Raise hands -----------------------------------------------------------------

HANDS = {"tie_break": "least_active", "quiet_rounds": 2}


def test_raise_hands_asks_everyone_but_last_speaker_privately():
    *_, every = simulate(rules.raise_hands, [MOD] + GROUP, {**HANDS, "max_turns": 2},
                         bid=lambda actor, n: actor == "p1" if n == 0 else actor == "p2")
    offers = [effect for effect in every if effect["type"] == "offer"]
    first, second = offers[:4], offers[4:]
    assert {effect["actor_id"] for effect in first} == {"m", "p1", "p2", "p3"}
    assert {effect["actor_id"] for effect in second} == {"m", "p2", "p3"}  # p1 just spoke
    assert all(effect["actions"][0]["audience"] == [effect["actor_id"]] for effect in offers)


def test_raise_hands_tie_goes_to_least_active():
    words = {"p1": "w " * 9, "p2": "w", "p3": "w " * 2}
    turns = [{"p1"}, {"p3"}, {"p2"}, {"p1", "p3"}]  # p2 spoke last, so p1 and p3 compete
    speakers, statuses, *_ = simulate(rules.raise_hands, GROUP, {**HANDS, "max_turns": 4},
                                      text=lambda actor, n: words[actor], bid=lambda actor, n: actor in turns[n])
    assert speakers == ["p1", "p3", "p2", "p3"]
    assert statuses[-1]["competitors"] == ["p1", "p3"]


def test_raise_hands_moderator_wins_tie():
    speakers, *_ = simulate(rules.raise_hands, [MOD] + GROUP, {**HANDS, "max_turns": 2},
                            bid=lambda actor, n: n == 1 and actor in ("m", "p2") or (n == 0 and actor == "p1"))
    assert speakers == ["p1", "m"]


def test_raise_hands_ends_after_quiet_rounds():
    speakers, _, finished, every = simulate(rules.raise_hands, GROUP, HANDS, bid=lambda actor, n: n == 0 and actor == "p2")
    assert finished and speakers == ["p2"]
    assert len([effect for effect in every if effect["type"] == "offer"]) == 3 + 2 + 2  # opening round + two quiet rounds


def test_raise_hands_random_tie_is_seeded():
    def run(seed):
        return simulate(rules.raise_hands, GROUP, {**HANDS, "tie_break": "random", "max_turns": 1},
                        bid=lambda actor, n: True, seed=seed)[0]
    assert run(1) == run(1) and {run(seed)[0] for seed in range(20)} == {"p1", "p2", "p3"}


def test_raise_hands_lone_member_with_moderator_progresses():
    lone = [MOD, GROUP[0]]
    speakers, _, finished, _ = simulate(rules.raise_hands, lone, {**HANDS, "max_turns": 3}, bid=lambda actor, n: True)
    assert finished and speakers == ["m", "p1", "m"]


# Speaker picks next ------------------------------------------------------------

PICK = {"quiet_rounds": 2}


def test_speaker_selects_starts_with_first_member_not_moderator():
    speakers, *_ = simulate(rules.speaker_selects, [MOD] + GROUP, {**PICK, "max_turns": 1})
    assert speakers == ["p1"]


def test_named_participant_is_invited():
    names = {"p1": "p3", "p3": "p2", "p2": "p1"}
    speakers, *_ = simulate(rules.speaker_selects, GROUP, {**PICK, "max_turns": 4},
                            pass_to=lambda actor, n: names[actor])
    assert speakers == ["p1", "p3", "p2", "p1"]


def test_pass_offer_lists_others_and_anyone_after_moderators_decline():
    *_, every = simulate(rules.speaker_selects, [MOD] + GROUP, {**PICK, "max_turns": 2},
                         pass_to=lambda actor, n: "p2")
    offers = [effect for effect in every if effect["type"] == "offer"]
    assert offers[0]["actions"][0]["type"] == "turn.request" and offers[0]["actor_id"] == "m"
    passed = offers[1]["actions"][0]
    assert offers[1]["actor_id"] == "p1" and passed["type"] == "turn.pass"
    assert passed["schema"]["enum"] == ["m", "p2", "p3", "anyone"]


def test_anyone_opens_the_floor_and_first_yes_wins():
    speakers, *_ = simulate(rules.speaker_selects, GROUP, {**PICK, "max_turns": 2},
                            bid=lambda actor, n: actor in ("p2", "p3"))
    assert speakers == ["p1", "p2"]


def test_nobody_wants_the_floor_speaker_continues_then_step_ends():
    speakers, _, finished, _ = simulate(rules.speaker_selects, GROUP, PICK)
    assert finished and speakers == ["p1", "p1"]  # one continuation, then the second quiet round ends it


def test_moderator_can_be_named():
    speakers, *_ = simulate(rules.speaker_selects, [MOD] + GROUP, {**PICK, "max_turns": 3},
                            pass_to=lambda actor, n: "m" if actor == "p1" else "p3")
    assert speakers == ["p1", "m", "p3"]


def test_open_floor_order_is_shuffled_with_the_seed():
    def first_taker(seed):
        return simulate(rules.speaker_selects, GROUP, {**PICK, "max_turns": 2}, bid=lambda actor, n: True, seed=seed)[0][1]
    assert first_taker(3) == first_taker(3)
    assert {first_taker(seed) for seed in range(20)} == {"p2", "p3"}
