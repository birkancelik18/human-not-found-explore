"""AI moderator: a participant behaviour that follows conversational strategies (goal -> trigger -> behaviour).

Goals: balance participation (uneven words, measured by a Gini index -> invite the quietest member), civility
(a disrespectful message -> remind the group to stay respectful) and expertise (a point that fits someone's public
details -> ask them). It reads the group's counts from the `turn.status` events that the `hnf.turn_taking` rules
publish, or counts the discussion messages in its memory when no rule publishes them.
"""

ROLE = ("You are the moderator of a group discussion, not one of its members. You do not argue for an answer of your "
        "own; you help the group talk well. Keep every message to one or two short sentences.")
NO_TRIGGER = ("Nothing needs fixing right now: briefly sum up where the group stands, or move it on to the next "
              "open point, without giving your own opinion.")


def gini(values):
    """0 when everyone contributed the same, towards 1 when one person did everything."""
    values = list(values)
    total = sum(values)
    if not values or total == 0:
        return 0.0
    differences = sum(abs(a - b) for a in values for b in values)
    return differences / (2 * len(values) * total)


def members(observation):
    return [person for person in observation["participants"] if person.get("role") != "moderator"]


def counts(observation):
    """Words per group member in this discussion, and the last message said."""
    memory = observation.get("memory", [])
    ids = [person["id"] for person in members(observation)]
    for item in reversed(memory):
        if item.get("topic") == "turn.status" and isinstance(item.get("payload"), dict):
            words = item["payload"].get("words", {})
            return {key: words.get(key, 0) for key in ids}, item["payload"].get("last_message", "")
    words, last = {key: 0 for key in ids}, ""
    for item in memory:
        if item.get("topic") == "action.accepted" and item.get("action_type") == "discussion.message":
            last = str(item.get("payload", ""))
            if item.get("actor_id") in words:
                words[item["actor_id"]] += len(last.split())
    return words, last


def name(observation, key):
    return next((person.get("display_name", key) for person in observation["participants"] if person["id"] == key), key)


def quietest(words, allowed=None):
    candidates = [key for key in words if allowed is None or key in allowed]
    return min(candidates, key=lambda key: words[key]) if candidates else None


def system(config, *parts):
    text = " ".join(part.strip() for part in (ROLE, config["persona"], config["instructions"], *parts) if part.strip())
    return text[:8000]


def people_details(observation):
    return "; ".join(f"{person.get('display_name', person['id'])} ({person['id']}): {person.get('attributes', {})}"
                     for person in members(observation))


def moderator(request):
    config, observation, invocation = request["config"], request["observation"], request["invocation_id"]
    action = observation["allowed_actions"][0]
    words, last = counts(observation)
    unbalanced = config["balance"] and sum(words.values()) > 0 and gini(words.values()) > config["balance_threshold"]
    quiet = quietest(words)

    def answer(value):
        return {"invocation_id": invocation, "action_type": action["type"], "payload": value}

    def ask_model(*parts, prompt=None):
        reply = {"invocation_id": invocation, "request_model": True, "system": system(config, *parts)}
        if prompt:
            reply["action_prompt"] = prompt
        return reply

    if action["type"] == "turn.request":
        if unbalanced:
            return answer(True)
        if config["civility"]:
            return ask_model(f"The last message was: {last!r}", prompt=(
                "Answer true only if the last message was rude, hostile or disrespectful and needs a response about "
                "tone; otherwise answer false."))
        return answer(False)
    if action["type"] == "turn.pass":
        allowed = action["schema"].get("enum", [])
        if config["expertise"]:
            return ask_model(f"The group: {people_details(observation)}.", f"The last message was: {last!r}", prompt=(
                "Name the participant whose details make them best placed to speak to the last message."))
        choice = quietest(words, allowed)
        return answer(choice if choice else "anyone")
    if action["type"] == "discussion.message":
        if unbalanced and quiet:
            trigger = f"Participation is uneven. Invite {name(observation, quiet)} by name to share their view."
        else:
            trigger = NO_TRIGGER
        extra = []
        if config["civility"]:
            extra.append("If the last message was disrespectful, first remind the group to stay respectful and considerate.")
        if config["expertise"]:
            extra.append(f"If someone's details make them the right person for the current point, ask them: {people_details(observation)}.")
        return ask_model(trigger, *extra)
    return ask_model()


def self_test():
    return {"ok": gini([1, 1, 1]) == 0 and abs(gini([0, 0, 9]) - 2 / 3) < 1e-9 and gini([]) == 0}
