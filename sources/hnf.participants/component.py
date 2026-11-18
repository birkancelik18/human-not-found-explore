"""Participant behaviours: a model participant and a scripted participant."""

SYSTEM = ("You are a participant in a research study. Read the situation, the instructions and what you remember, "
          "then choose one of the allowed actions and give its value.")


def model_participant(request):
    """Hand every choice to the configured model, with the persona and instructions as the system prompt."""
    config = request["config"]
    system = " ".join(part for part in (SYSTEM, config["persona"].strip(), config["instructions"].strip()) if part)
    return {"invocation_id": request["invocation_id"], "request_model": True, "system": system[:8000]}


# Scripted participant ----------------------------------------------------

def pick(options, rule):
    """Choose among enum options: accept/reject look for an option with that word, otherwise the first."""
    if rule in ("accept", "reject"):
        for option in options:
            if isinstance(option, str) and rule in option.lower():
                return option
    return options[0]


def value_for(schema, rule, number):
    """A value that fits the action's schema, following the rule."""
    if "const" in schema:
        return schema["const"]
    if schema.get("enum"):
        return pick(schema["enum"], rule)
    for key in ("oneOf", "anyOf"):
        if schema.get(key):
            return value_for(schema[key][0], rule, number)
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = kind[0]
    if kind == "boolean":
        return rule != "reject"
    if kind in ("integer", "number"):
        low = schema.get("minimum", schema.get("exclusiveMinimum", 0))
        high = schema.get("maximum", schema.get("exclusiveMaximum", max(low, number)))
        value = min(max(number, low), high) if rule == "fixed_number" else low
        return int(value) if kind == "integer" else value
    if kind == "array":
        items = schema.get("items", {})
        count = min(schema.get("minItems", 1), schema.get("maxItems", 100))
        if items.get("enum") and schema.get("uniqueItems"):
            return items["enum"][:count]
        return [value_for(items, rule, number) for _ in range(count)]
    if kind == "object":
        properties = schema.get("properties", {})
        return {key: value_for(properties.get(key, {}), rule, number) for key in schema.get("required", [])}
    text = "OK."
    return (text * (1 + schema.get("minLength", 0) // len(text)))[:max(schema.get("maxLength", 4000), 1)]


def scripted_participant(request):
    """Answer with a fixed rule per action type, for confederates and controls."""
    config = request["config"]
    rules = {item["action_type"]: item for item in config["rules"]}
    actions = request["observation"]["allowed_actions"]
    action = next((item for item in actions if item["type"] in rules), actions[0])
    rule = rules.get(action["type"], {"rule": config["default_rule"], "number": config["default_number"]})
    return {"invocation_id": request["invocation_id"], "action_type": action["type"],
            "payload": value_for(action["schema"], rule["rule"], rule["number"])}


def self_test():
    number = {"type": "number", "minimum": 0, "maximum": 10}
    choice = {"type": "string", "enum": ["accept", "reject"]}
    return {"ok": value_for(number, "fixed_number", 4) == 4 and value_for(number, "fixed_number", 40) == 10
            and value_for(number, "first_option", 4) == 0 and value_for(choice, "reject", 0) == "reject"
            and value_for(choice, "accept", 0) == "accept" and value_for({"type": "boolean"}, "reject", 0) is False
            and value_for({"type": "string", "minLength": 1}, "first_option", 0) == "OK."}
