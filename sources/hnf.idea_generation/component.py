"""Idea generation: participants list ideas over several rounds; the measure counts unique ideas."""

import re

NOTHING = {"effects": []}


def idea_generation(request):
    config, event = request["config"], request["event"]
    people = [person["id"] for person in request["participants"]]
    audience = "shared" if config["visible"] else []
    note = ("Everyone in your group sees the ideas you submit." if config["visible"]
            else "You are working alone; nobody else sees your ideas.")

    def ask(round_number):
        return [{"type": "offer", "id": f"ideas{round_number}.{person}", "actor_id": person, "actions": [{
            "type": "ideas.submit", "audience": audience,
            "prompt": f"{config['prompt']}\nRound {round_number} of {config['rounds']}. {note} "
                      f"List up to {config['max_ideas']} new ideas, one per item.",
            "schema": {"type": "array", "minItems": 1, "maxItems": config["max_ideas"],
                       "items": {"type": "string", "minLength": 1, "maxLength": 500}},
            "sample": config["sample_ideas"][:config["max_ideas"]]}]} for person in people]

    if event["topic"] == "run.started":
        return {"effects": [{"type": "update", "state": {"round": 1, "answered": []}}] + ask(1)}
    if not (event["topic"] == "action.accepted" and request["own_event"] and event["action_type"] == "ideas.submit"):
        return NOTHING
    state = dict(request["state"])
    state["answered"] = sorted({*state["answered"], event["actor_id"]})
    if len(state["answered"]) < len(people):
        return {"effects": [{"type": "update", "state": state}]}
    if state["round"] >= config["rounds"]:
        return {"effects": [{"type": "update", "state": state}] + ([{"type": "finish"}] if config["finish"] else [])}
    state = {"round": state["round"] + 1, "answered": []}
    return {"effects": [{"type": "update", "state": state}] + ask(state["round"])}


def normalized(idea):
    return " ".join(re.sub(r"[^\w\s]", " ", idea.lower()).split())


def ideas(request):
    step = request["config"]["step"]
    submitted = {}
    for record in request["authorized_events"]:
        if (record["event_type"] == "action_applied" and record["payload"]["action_type"] == "ideas.submit"
                and (not step or record["step_id"] == step)):
            submitted.setdefault(record["actor_id"], []).extend(record["payload"]["value"])
    if not submitted:
        return {"status": "missing", "value": None, "details": {"reason": "No ideas were submitted."}}
    own = {actor: {normalized(idea) for idea in items} - {""} for actor, items in submitted.items()}
    group = set().union(*own.values())
    return {"status": "ok", "value": len(group), "unit": "unique ideas (group)", "details": {
        "unique_per_participant": {actor: len(items) for actor, items in sorted(own.items())},
        "submitted_per_participant": {actor: len(items) for actor, items in sorted(submitted.items())},
        "submitted_total": sum(len(items) for items in submitted.values()),
        "mean_unique_per_participant": round(sum(len(items) for items in own.values()) / len(own), 6)}}


def self_test():
    return {"ok": normalized("  Plant more Trees! ") == "plant more trees" and normalized("plant more trees") == "plant more trees"}
