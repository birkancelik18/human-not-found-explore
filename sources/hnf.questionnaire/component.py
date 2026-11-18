"""Questionnaire: scale, choice and text items, and a summary measure. Adapted from the app's study kit survey."""

NOTHING = {"effects": []}


def item_schema(item):
    if item["type"] == "scale":
        return {"type": "integer", "minimum": item["min"], "maximum": item["max"]}
    if item["type"] == "choice":
        return {"type": "string", "enum": item["options"]}
    return {"type": "string", "minLength": 1, "maxLength": 2000}


def item_sample(item):
    if item["type"] == "scale":
        return (item["min"] + item["max"]) // 2
    if item["type"] == "choice":
        return item["options"][0]
    return "No further comments."


def item_line(item):
    if item["type"] == "scale":
        return f"- {item['id']}: {item['prompt']} ({item['min']} to {item['max']})"
    if item["type"] == "choice":
        return f"- {item['id']}: {item['prompt']} (one of: {', '.join(item['options'])})"
    return f"- {item['id']}: {item['prompt']} (free text)"


def questionnaire(request):
    config, event = request["config"], request["event"]
    items, people = config["items"], [person["id"] for person in request["participants"]]
    for item in items:
        if item["type"] == "choice" and not item["options"]:
            raise ValueError(f"Choice item '{item['id']}' needs at least one option.")
        if item["type"] == "scale" and item["min"] > item["max"]:
            raise ValueError(f"Scale item '{item['id']}' has a minimum above its maximum.")
    if event["topic"] == "run.started":
        action = {"type": "questionnaire.answers", "audience": "shared" if config["visibility"] == "shared" else [],
                  "prompt": "\n".join([config["prompt"]] + [item_line(item) for item in items]),
                  "schema": {"type": "object", "additionalProperties": False, "required": [item["id"] for item in items],
                             "properties": {item["id"]: item_schema(item) for item in items}},
                  "sample": {item["id"]: item_sample(item) for item in items}}
        return {"effects": [{"type": "offer", "id": "ask." + person, "actor_id": person, "actions": [action]}
                            for person in people]}
    if not (event["topic"] == "action.accepted" and request["own_event"] and event["action_type"] == "questionnaire.answers"):
        return NOTHING
    answered = sorted({*request["state"].get("answered", []), event["actor_id"]})
    effects = [{"type": "update", "state": {"answered": answered}}]
    if set(answered) >= set(people):
        effects.append({"type": "emit", "topic": "questionnaire.completed", "audience": "shared", "payload": {
            "items": [{"id": item["id"], "type": item["type"]} for item in items], "respondents": len(answered)}})
        if config["finish"]:
            effects.append({"type": "finish"})
    return {"effects": effects}


def questionnaire_summary(request):
    step = request["config"]["step"]
    latest, types = {}, {}
    for record in request["authorized_events"]:
        if step and record["step_id"] != step:
            continue
        if record["event_type"] == "action_applied" and record["payload"]["action_type"] == "questionnaire.answers":
            latest[record["actor_id"]] = record["payload"]["value"]
        elif record["event_type"] == "component_event" and record["payload"].get("topic") == "questionnaire.completed":
            types.update({item["id"]: item["type"] for item in record["payload"]["payload"]["items"]})
    if not latest:
        return {"status": "missing", "value": None, "details": {"reason": "No questionnaire answers were submitted."}}
    summary = {}
    for key in sorted({key for answer in latest.values() for key in answer}):
        values = [answer[key] for answer in latest.values() if key in answer]
        kind = types.get(key) or ("scale" if all(type(value) is int for value in values) else "text")
        if kind == "scale":
            summary[key] = {"type": kind, "mean": round(sum(values) / len(values), 6), "n": len(values)}
        elif kind == "choice":
            summary[key] = {"type": kind, "counts": {value: values.count(value) for value in sorted(set(values))}, "n": len(values)}
        else:
            summary[key] = {"type": "text", "n": len(values)}
    return {"status": "ok", "value": len(latest), "unit": "respondents", "details": {"items": summary}}


def self_test():
    item = {"id": "q", "prompt": "?", "type": "scale", "min": 1, "max": 7, "options": []}
    return {"ok": item_sample(item) == 4 and item_schema(item)["maximum"] == 7}
