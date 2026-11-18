"""Group decision: choose one option by majority, unanimity or a leader; measure accuracy and the information shared."""

NOTHING = {"effects": []}


def group_decision(request):
    config, event = request["config"], request["event"]
    people = [person["id"] for person in request["participants"]]
    options, rule = config["options"], config["rule"]
    leader = config["leader"] or people[0]
    if rule == "leader" and leader not in people:
        raise ValueError("The leader must be an enabled participant.")
    voters = [leader] if rule == "leader" else people
    audience = "shared" if config["visible"] else []
    rules = {"majority": "The option with the most votes is chosen; a tie means another vote.",
             "unanimity": "An option is chosen only if everyone votes for it; otherwise you vote again.",
             "leader": "You are the leader: your choice is the group's decision.",
             "individual": "Vote on your own; this is your personal choice, not a group decision."}

    def ballot(state, note=""):
        return [{"type": "offer", "id": f"vote{state['ballot']}.{person}", "actor_id": person, "actions": [{
            "type": "decision.vote", "audience": audience, "schema": {"type": "string", "enum": options},
            "sample": options[0],
            "prompt": f"{config['prompt']}\nVote {state['ballot']} of {config['max_ballots']}. {rules[rule]}{note}\n"
                      f"Choose one of: {', '.join(options)}"}]} for person in voters]

    if event["topic"] == "run.started":
        state = {"ballot": 1, "votes": {}}
        return {"effects": [{"type": "update", "state": state}] + ballot(state)}
    if not (event["topic"] == "action.accepted" and request["own_event"] and event["action_type"] == "decision.vote"
            and "payload" in event):
        return NOTHING
    state = dict(request["state"])
    state["votes"] = {**state["votes"], event["actor_id"]: event["payload"]}
    if len(state["votes"]) < len(voters):
        return {"effects": [{"type": "update", "state": state}]}
    counts = {option: list(state["votes"].values()).count(option) for option in options}
    top = max(counts.values())
    leaders = [option for option, count in counts.items() if count == top]
    if rule == "individual":
        decision = None
    elif rule == "unanimity":
        decision = leaders[0] if top == len(voters) else None
    else:
        decision = leaders[0] if len(leaders) == 1 else None
    if decision is None and rule != "individual" and state["ballot"] < config["max_ballots"]:
        state = {"ballot": state["ballot"] + 1, "votes": {}}
        shown = f" Last vote: {', '.join(f'{option} {count}' for option, count in counts.items() if count)}." if config["visible"] else ""
        return {"effects": [{"type": "update", "state": state},
                            {"type": "emit", "topic": "decision.revote", "audience": "shared",
                             "payload": {"ballot": state["ballot"] - 1, "counts": counts if config["visible"] else None}}]
                + ballot(state, " No decision was reached in the last vote." + shown)}
    effects = [{"type": "update", "state": {**state, "over": True}},
               {"type": "emit", "topic": "decision.result", "audience": "shared",
                "payload": {"decision": decision, "rule": rule, "ballots": state["ballot"], "counts": counts}}]
    return {"effects": effects + ([{"type": "finish"}] if config["finish"] else [])}


# Measures -------------------------------------------------------------------

def missing(reason):
    return {"status": "missing", "value": None, "details": {"reason": reason}}


def decision_accuracy(request):
    config = request["config"]
    results = [record["payload"]["payload"] for record in request["authorized_events"]
               if record["event_type"] == "component_event" and record["payload"].get("topic") == "decision.result"
               and (not config["step"] or record["step_id"] == config["step"])]
    if not results:
        return missing("No group decision was recorded.")
    outcome = results[-1]
    if outcome["rule"] == "individual":
        return missing("This step collected individual votes, not a group decision; choose the group decision step.")
    correct = outcome["decision"] is not None and outcome["decision"].strip().lower() == config["answer_key"].strip().lower()
    return {"status": "ok", "value": int(correct), "unit": "correct (1) or not (0)", "details": {
        "decision": outcome["decision"], "answer_key": config["answer_key"], "ballots": outcome["ballots"],
        "counts": outcome["counts"]}}


def mentioned(text, clue):
    text = text.lower()
    return any(keyword.strip().lower() in text for keyword in clue["keywords"] if keyword.strip())


def information_shared(request):
    config = request["config"]
    clues = config["clues"]
    if not clues:
        return missing("Configure the clues to look for.")
    messages = [(record["actor_id"], str(record["payload"]["value"])) for record in request["authorized_events"]
                if record["event_type"] == "action_applied" and record["payload"]["action_type"] == config["action_type"]
                and (not config["step"] or record["step_id"] == config["step"])]
    if not messages:
        return missing("No discussion messages were recorded.")
    by_clue = {clue["id"]: sorted({actor for actor, text in messages if mentioned(text, clue)}) for clue in clues}
    by_participant = {}
    for clue_id, actors in by_clue.items():
        for actor in actors:
            by_participant.setdefault(actor, []).append(clue_id)
    rate = lambda group: (round(sum(bool(by_clue[clue["id"]]) for clue in group) / len(group), 6) if group else None)
    return {"status": "ok", "value": rate(clues), "unit": "share of clues mentioned (0-1)", "details": {
        "mentioned_by": by_clue, "clues_by_participant": by_participant,
        "shared_clues_mentioned": rate([clue for clue in clues if clue["kind"] == "shared"]),
        "unique_clues_mentioned": rate([clue for clue in clues if clue["kind"] == "unique"])}}


def self_test():
    clue = {"id": "a", "keywords": ["Knife", " alibi"], "kind": "shared"}
    return {"ok": mentioned("He had no ALIBI.", clue) and not mentioned("Nothing here.", clue)}
