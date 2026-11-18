"""Effort task: each participant chooses an effort from 0 to 10, credited individually or pooled."""

NOTHING = {"effects": []}
CREDIT = {"individual": "Your own effort is recorded and credited to you personally.",
          "pooled": "Only the group's combined effort is recorded; nobody can tell how much each member contributed."}


def effort_task(request):
    config, event = request["config"], request["event"]
    people = [person["id"] for person in request["participants"]]

    def ask(round_number):
        return [{"type": "offer", "id": f"effort{round_number}.{person}", "actor_id": person, "actions": [{
            "type": "effort.choose", "audience": [],
            "prompt": f"{config['prompt']}\nRound {round_number} of {config['rounds']}. {CREDIT[config['credit']]} "
                      "Choose how much effort to put in, from 0 (none) to 10 (your maximum).",
            "schema": {"type": "integer", "minimum": 0, "maximum": 10}, "sample": 5}]} for person in people]

    if event["topic"] == "run.started":
        return {"effects": [{"type": "update", "state": {"round": 1, "efforts": {}}}] + ask(1)}
    if not (event["topic"] == "action.accepted" and request["own_event"] and event["action_type"] == "effort.choose"
            and "payload" in event):
        return NOTHING
    state = dict(request["state"])
    state["efforts"] = {**state["efforts"], event["actor_id"]: event["payload"]}
    if len(state["efforts"]) < len(people):
        return {"effects": [{"type": "update", "state": state}]}
    efforts = state["efforts"]
    payload = {"round": state["round"], "credit": config["credit"], "total": sum(efforts.values()), "participants": len(efforts)}
    if config["credit"] == "individual":
        payload["efforts"] = efforts
    effects = [{"type": "emit", "topic": "effort.result", "audience": "shared", "payload": payload}]
    if state["round"] >= config["rounds"]:
        return {"effects": [{"type": "update", "state": state}] + effects + ([{"type": "finish"}] if config["finish"] else [])}
    state = {"round": state["round"] + 1, "efforts": {}}
    return {"effects": [{"type": "update", "state": state}] + effects + ask(state["round"])}


def effort(request):
    step = request["config"]["step"]
    records = [record for record in request["authorized_events"] if not step or record["step_id"] == step]
    credit = {record["step_id"]: record["payload"]["payload"]["credit"] for record in records
              if record["event_type"] == "component_event" and record["payload"].get("topic") == "effort.result"}
    choices = [(record["actor_id"], record["step_id"], record["payload"]["value"]) for record in records
               if record["event_type"] == "action_applied" and record["payload"]["action_type"] == "effort.choose"]
    if not choices:
        return {"status": "missing", "value": None, "details": {"reason": "No effort was chosen."}}
    mean = lambda values: round(sum(values) / len(values), 6) if values else None
    by_participant = {}
    for actor, _, value in choices:
        by_participant.setdefault(actor, []).append(value)
    return {"status": "ok", "value": mean([value for *_, value in choices]), "unit": "mean effort (0-10)", "details": {
        "individual": mean([value for _, step_id, value in choices if credit.get(step_id) == "individual"]),
        "pooled": mean([value for _, step_id, value in choices if credit.get(step_id) == "pooled"]),
        "by_participant": {actor: mean(values) for actor, values in sorted(by_participant.items())}, "n": len(choices)}}


def self_test():
    return {"ok": set(CREDIT) == {"individual", "pooled"}}
