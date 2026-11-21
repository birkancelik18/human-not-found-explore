"""AI moderator: a participant behaviour that follows conversational strategies (goal -> trigger -> behaviour).

Goals: balance participation (uneven words, measured by a Gini index -> invite the quietest member), civility
(a disrespectful message -> remind the group to stay respectful), ground rules (a message that breaks the
group's rules -> recall the rule gently) and expertise. The 'conte' policy follows Conte (2026) instead (a point that fits someone's public
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


# Conte (2026) policy ---------------------------------------------------------------------------------------------
# The model proposes, deterministic filters decide: participation reasons use the group average with a warm-up and a
# cooldown; the model judges conflict, direct requests, off-topic drift and ground-rule breaks, with a severity floor.
# Time is speaking time estimated from the members' words (words / words_per_minute).

SEVERITY = ("Rate how serious the problem is from 0 to 1: 0.1-0.3 barely noticeable, 0.4-0.5 worth a light touch, "
            "0.6-0.7 clear, 0.8-1.0 serious.")


def participation(config, words, minute, interventions):
    """Exclusion (a member under under_ratio x the average) or monopolization (over over_ratio x), after the warm-up
    and outside the cooldown for that reason. Returns (reason, member) or None."""
    if minute < config["warmup_minutes"] or not words:
        return None
    average = sum(words.values()) / len(words)
    if average == 0:
        return None
    def cooling(reason):
        last = [item["minute"] for item in interventions if item["reason"] == reason]
        return bool(last) and minute - last[-1] < config["cooldown_minutes"]
    under = [key for key in words if words[key] < config["under_ratio"] * average]
    over = [key for key in words if words[key] > config["over_ratio"] * average]
    if under and not cooling("exclusion"):
        return "exclusion", min(under, key=lambda key: words[key])
    if over and not cooling("monopolization"):
        return "monopolization", max(over, key=lambda key: words[key])
    return None


CONTE_DEFAULTS = {"warmup_minutes": 8, "words_per_minute": 150, "cooldown_minutes": 2, "under_ratio": 0.5,
                  "over_ratio": 2.0, "min_severity": 0.4}


def conte_moderator(request):
    config = {**CONTE_DEFAULTS, **request["config"]}
    observation, invocation = request["observation"], request["invocation_id"]
    state = dict(request.get("state") or {})
    interventions = list(state.get("interventions", []))
    action = observation["allowed_actions"][0]
    words, last = counts(observation)
    minute = round(sum(words.values()) / config["words_per_minute"], 2)
    rules = config.get("ground_rules", "").strip()

    def reply(body, **changes):
        return {**body, "invocation_id": invocation, "state": {**state, "interventions": interventions, **changes}}

    def ask_model(*parts, prompt=None):
        body = {"request_model": True, "system": system(config, *parts)}
        return {**body, "action_prompt": prompt} if prompt else body

    if action["type"] == "turn.request":
        found = participation(config, words, minute, interventions)
        if found:
            return reply({"action_type": action["type"], "payload": True}, pending={"reason": found[0], "member": found[1]})
        recent = [f"{item['reason']} at minute {item['minute']}" for item in interventions[-5:]] or ["none"]
        reasons = ["conflict: aggressive tone, insults or personal attacks (always step in)",
                   "a direct request to you, the moderator, such as asking for a recap (always step in)",
                   "off-topic drift away from the task"]
        if rules:
            reasons.append("a break of the group's ground rules: " + rules)
        return reply(ask_model(
            "Possible reasons to step in: " + "; ".join(reasons) + ". " + SEVERITY,
            f"Your recent interventions: {', '.join(recent)}. It is now minute {minute} of speaking time. Do not step in "
            f"again for off-topic drift or the ground rules within {config['cooldown_minutes']} minutes of your last "
            "intervention of that kind.",
            f"The last message was: {last!r}", prompt=(
                "Answer true only if the last message needs you to step in: always for conflict or a direct request to "
                f"you; for off-topic drift or a ground-rule break only when its severity is at least "
                f"{config['min_severity']} and the reason is not cooling down. Otherwise answer false.")),
            pending={"reason": "judged"})
    if action["type"] == "discussion.message":
        pending = state.get("pending") or {}
        reason = pending.get("reason", "floor")
        member = name(observation, pending["member"]) if pending.get("member") else ""
        if reason == "exclusion":
            trigger = (f"{member} has spoken much less than the others. Invite {member} by name, tying the invitation to "
                       "a concrete point that has just come up, so they have something specific to react to.")
        elif reason == "monopolization":
            trigger = (f"{member} has taken much of the floor. Do not reprimand them: pick up a point {member} raised and "
                       "open it to the others.")
        elif reason == "judged":
            trigger = ("You decided to step in after the last message. If it was a conflict, lower the tension without "
                       "taking sides and bring the group back to the substance. If someone asked you something, answer "
                       "briefly (a recap only from what was actually said) and hand the floor back. If the group drifted "
                       "off topic, bring it back to the point it had reached. If a ground rule was broken, gently recall "
                       "the idea of that rule (not its number) as a reminder, not a reproach. " + SEVERITY +
                       " Match your tone to the severity: soft for light problems, firm for serious ones."
                       + (f" The ground rules: {rules}" if rules else ""))
        else:
            trigger = NO_TRIGGER
        interventions.append({"reason": reason, "minute": minute})
        return reply(ask_model(trigger, f"The last message was: {last!r}"), pending=None)
    if action["type"] == "turn.pass":
        allowed = action["schema"].get("enum", [])
        choice = quietest(words, allowed)
        return reply({"action_type": action["type"], "payload": choice if choice else "anyone"})
    return reply(ask_model())


def moderator(request):
    if request["config"].get("policy") == "conte":
        return conte_moderator(request)
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

    rules = config.get("ground_rules", "").strip()
    if action["type"] == "turn.request":
        if unbalanced:
            return answer(True)
        checks = (["it was rude, hostile or disrespectful and needs a response about tone"] if config["civility"] else []) + (
            ["it breaks one of the group's ground rules"] if rules else [])
        if checks:
            context = [f"The group's ground rules: {rules}"] if rules else []
            return ask_model(*context, f"The last message was: {last!r}", prompt=(
                f"Answer true only if the last message needs you to step in because {' or '.join(checks)}; "
                "otherwise answer false."))
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
        if rules:
            extra.append(f"The group's ground rules: {rules} If the last message breaks one, gently recall the idea "
                         "of that rule (not its number) as a reminder, not a reproach, and steer the group back.")
        if config["expertise"]:
            extra.append(f"If someone's details make them the right person for the current point, ask them: {people_details(observation)}.")
        return ask_model(trigger, *extra)
    return ask_model()


def self_test():
    base = {"model_ref": "default", "balance": True, "civility": False, "expertise": False, "balance_threshold": 0.3,
            "persona": "", "instructions": ""}
    observation = {"participants": [{"id": "p1"}, {"id": "p2"}], "memory": [],
                   "allowed_actions": [{"type": "turn.request", "schema": {}}]}
    def bid(config):
        return moderator({"config": config, "observation": observation, "invocation_id": "i"})
    return {"ok": gini([1, 1, 1]) == 0 and abs(gini([0, 0, 9]) - 2 / 3) < 1e-9 and gini([]) == 0
            and bid(base).get("payload") is False
            and "No majority votes." in bid({**base, "ground_rules": "No majority votes."}).get("system", "")
            and conte_checks()}


def conte_checks():
    config = {"model_ref": "default", "balance": True, "civility": False, "expertise": False, "balance_threshold": 0.3,
              "persona": "", "instructions": "", "ground_rules": "", "policy": "conte", "warmup_minutes": 8,
              "words_per_minute": 150, "cooldown_minutes": 2, "under_ratio": 0.5, "over_ratio": 2.0, "min_severity": 0.4}
    people = [{"id": "p1", "display_name": "A"}, {"id": "p2", "display_name": "B"}, {"id": "p3", "display_name": "C"}]
    def bid(words, state=None):
        status = {"topic": "turn.status", "payload": {"words": words, "last_message": "x"}}
        return conte_moderator({"config": config, "invocation_id": "i", "state": state or {}, "observation": {
            "participants": people, "memory": [status], "allowed_actions": [{"type": "turn.request", "schema": {}}]}})
    early = bid({"p1": 500, "p2": 400, "p3": 10})           # 6 minutes: still warming up, so the model judges
    late = bid({"p1": 800, "p2": 700, "p3": 20})            # 10 minutes, p3 far under half the average
    cooling = bid({"p1": 800, "p2": 700, "p3": 20}, {"interventions": [{"reason": "exclusion", "minute": 9.5}]})
    return (early.get("request_model") is True and late.get("payload") is True
            and late["state"]["pending"] == {"reason": "exclusion", "member": "p3"}
            and cooling.get("request_model") is True)
