"""Group discussion: a discussion activity with built-in turn-taking, a turn-order procedure, and participation balance."""

import math
from random import Random

NOTHING = {"effects": []}


def message_offer(config, offer_id, actor, heading):
    return {"type": "offer", "id": offer_id, "actor_id": actor, "actions": [{
        "type": "discussion.message", "prompt": f"{config['prompt']}\n{heading}", "audience": "shared",
        "schema": {"type": "string", "minLength": 1, "maxLength": 4000}, "sample": config["sample"]}]}


def discussion(request):
    """Shared messages. Turns: round robin (one speaker at a time, in listed order), free (everyone may speak
    each round), or procedure (speak when a turn-order procedure sends discussion.invite)."""
    config, event = request["config"], request["event"]
    people = [person["id"] for person in request["participants"]]
    turns, rounds = config["turns"], config["rounds"]
    state = dict(request["state"])
    if turns == "procedure":
        if event["topic"] == "discussion.invite" and event.get("payload", {}).get("actor_id") in people:
            count = state.get("invites", 0) + 1
            return {"effects": [{"type": "update", "state": {"invites": count}},
                                message_offer(config, f"speak{count}", event["payload"]["actor_id"], "It is your turn to speak.")]}
        return NOTHING
    if event["topic"] == "run.started":
        state = {"spoken": 0}
        if turns == "round_robin":
            return {"effects": [{"type": "update", "state": state},
                                message_offer(config, "speak", people[0], f"Round 1 of {rounds}. It is your turn to speak.")]}
        return {"effects": [{"type": "update", "state": state}] + [
            message_offer(config, "speak." + person, person, f"Round 1 of {rounds}. Add your message.") for person in people]}
    if not (event["topic"] == "action.accepted" and request["own_event"] and event["action_type"] == "discussion.message"):
        return NOTHING
    state["spoken"] += 1
    effects = [{"type": "update", "state": state}]
    if state["spoken"] >= rounds * len(people):
        return {"effects": effects + ([{"type": "finish"}] if config["finish"] else [])}
    round_number = state["spoken"] // len(people) + 1
    if turns == "round_robin":
        effects.append(message_offer(config, "speak", people[state["spoken"] % len(people)],
                                     f"Round {round_number} of {rounds}. It is your turn to speak."))
    elif state["spoken"] % len(people) == 0:
        effects += [message_offer(config, "speak." + person, person, f"Round {round_number} of {rounds}. Add your message.")
                    for person in people]
    return {"effects": effects}


def turn_order(request):
    """Invite one speaker at a time with discussion.invite, for the configured number of rounds."""
    config, event = request["config"], request["event"]
    state = dict(request["state"])
    if event["topic"] == "run.started":
        order = [person["id"] for person in request["participants"]]
        if config["order"] == "random":
            Random(request["seed"]).shuffle(order)
        state = {"order": order, "turns": 0}
    elif event["topic"] == "action.accepted" and event.get("action_type") == config["action_type"]:
        state["turns"] += 1
    else:
        return NOTHING
    order = state["order"]
    if state["turns"] >= config["rounds"] * len(order):
        return {"effects": [{"type": "update", "state": state}] + ([{"type": "finish"}] if config["finish"] else [])}
    return {"effects": [{"type": "update", "state": state},
                        {"type": "emit", "topic": "discussion.invite", "audience": "shared",
                         "payload": {"actor_id": order[state["turns"] % len(order)]}}]}


def evenness(counts):
    """Normalized Shannon entropy of the shares: 1 when everyone contributes equally, 0 when one person does everything."""
    total = sum(counts)
    if len(counts) < 2:
        return 1.0
    if total == 0:
        return None
    entropy = sum(-count / total * math.log(count / total) for count in counts if count)
    return round(entropy / math.log(len(counts)), 6)


def participation_balance(request):
    config = request["config"]
    people = [person["id"] for person in request["experiment"].get("participants", [])]
    messages, words = {person: 0 for person in people}, {person: 0 for person in people}
    for record in request["authorized_events"]:
        if (record["event_type"] == "action_applied" and record["payload"]["action_type"] == config["action_type"]
                and (not config["step"] or record["step_id"] == config["step"])):
            actor, value = record["actor_id"], record["payload"]["value"]
            messages[actor] = messages.get(actor, 0) + 1
            words[actor] = words.get(actor, 0) + len(str(value).split())
    if not sum(messages.values()):
        return missing("No discussion messages were recorded.")
    return {"status": "ok", "value": evenness(list(words.values())), "unit": "evenness (0-1)", "details": {
        "messages": messages, "words": words, "message_evenness": evenness(list(messages.values()))}}


def missing(reason):
    return {"status": "missing", "value": None, "details": {"reason": reason}}


def self_test():
    return {"ok": evenness([3, 3, 3]) == 1 and evenness([5, 0]) == 0 and evenness([1]) == 1}
