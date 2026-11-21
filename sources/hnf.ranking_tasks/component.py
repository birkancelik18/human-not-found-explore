"""Ranking tasks: order a list of items alone or as a group; error score, group synergy and ranking change."""

NOTHING = {"effects": []}


def ranking_task(request):
    """Individual mode: everyone ranks at the same time. Group mode: one reporter submits the group's ranking."""
    config, event = request["config"], request["event"]
    # A moderator (role 'moderator') runs the discussion; it does not rank, so it never skews the scores.
    people = [person["id"] for person in request["participants"] if person.get("role") != "moderator"]
    items = config["items"]
    if config["mode"] == "group":
        reporter = config["reporter"] or people[0]
        if reporter not in people:
            raise ValueError("The reporter must be an enabled participant who is not a moderator.")
        actors, kind = [reporter], "ranking.group_submit"
        note = "You report the group's ranking: submit the order your group agreed on."
    else:
        actors, kind = people, "ranking.submit"
        note = "Rank the items on your own."
    if event["topic"] == "run.started":
        return {"effects": [{"type": "offer", "id": "rank." + person, "actor_id": person, "actions": [{
            "type": kind, "audience": "shared" if config["visibility"] == "shared" else [],
            "prompt": f"{config['prompt']}\n{note} Put every item in order, most important first: {'; '.join(items)}",
            "schema": {"type": "array", "items": {"type": "string", "enum": items}, "uniqueItems": True,
                       "minItems": len(items), "maxItems": len(items)},
            "sample": list(items)}]} for person in actors]}
    if not (event["topic"] == "action.accepted" and request["own_event"] and event["action_type"] == kind):
        return NOTHING
    answered = sorted({*request["state"].get("answered", []), event["actor_id"]})
    done = set(answered) >= set(actors)
    return {"effects": [{"type": "update", "state": {"answered": answered}}]
            + ([{"type": "finish"}] if done and config["finish"] else [])}


# Measures -------------------------------------------------------------------

def missing(reason):
    return {"status": "missing", "value": None, "details": {"reason": reason}}


def rankings(request, step, kinds=("ranking.submit", "ranking.group_submit")):
    """The latest ranking per participant (and the group ranking) in a step; empty step means the whole run."""
    individual, group = {}, None
    for record in request["authorized_events"]:
        if (record["event_type"] == "action_applied" and record["payload"]["action_type"] in kinds
                and (not step or record["step_id"] == step)):
            if record["payload"]["action_type"] == "ranking.group_submit":
                group = record["payload"]["value"]
            else:
                individual[record["actor_id"]] = record["payload"]["value"]
    return individual, group


def error(ranking, key):
    """Sum of absolute differences between each item's rank and its rank in the key (items in both only)."""
    position = {item: index for index, item in enumerate(key)}
    return sum(abs(index - position[item]) for index, item in enumerate(ranking) if item in position)


def mean(values):
    return round(sum(values) / len(values), 6) if values else None


def error_score(request):
    config = request["config"]
    individual, group = rankings(request, config["step"])
    if not individual and group is None:
        return missing("No ranking was submitted in this step.")
    scores = {actor: error(value, config["answer_key"]) for actor, value in sorted(individual.items())}
    group_error = error(group, config["answer_key"]) if group is not None else None
    value = group_error if group_error is not None else mean(list(scores.values()))
    return {"status": "ok", "value": value, "unit": "error score (lower is better)", "details": {
        "group": group_error, "by_participant": scores, "mean_individual": mean(list(scores.values())),
        "best_individual": min(scores.values()) if scores else None}}


def group_synergy(request):
    config = request["config"]
    individual, _ = rankings(request, config["individual_step"], ("ranking.submit",))
    _, group = rankings(request, config["group_step"], ("ranking.group_submit",))
    if not individual or group is None:
        return missing("Synergy needs individual rankings in the individual step and a group ranking in the group step.")
    scores = [error(value, config["answer_key"]) for value in individual.values()]
    group_error = error(group, config["answer_key"])
    average, best = mean(scores), min(scores)
    return {"status": "ok", "value": round(average - group_error, 6), "unit": "points better than the average member",
            "details": {"group_error": group_error, "mean_individual_error": average, "best_individual_error": best,
                        "better_than_average": group_error < average, "better_than_best": group_error < best,
                        "gain_over_best": best - group_error}}


def ranking_change(request):
    config = request["config"]
    if not config["step_before"] or not config["step_after"]:
        return missing("Choose the steps before and after.")
    before, _ = rankings(request, config["step_before"])
    after, group_after = rankings(request, config["step_after"])
    moved = {actor: error(after[actor], before[actor]) for actor in sorted(before.keys() & after.keys())}
    if group_after is not None:
        # A group ranking counts as a new ranking for every member who ranked alone before.
        moved.update({actor: error(group_after, ranking) for actor, ranking in before.items() if actor not in after})
    if not moved:
        return missing("No participant ranked in both steps.")
    return {"status": "ok", "value": mean(list(moved.values())), "unit": "mean rank positions moved",
            "details": {"by_participant": moved}}


def self_test():
    started = ranking_task({"config": {"items": ["a", "b"], "mode": "individual", "prompt": "Rank.", "visibility": "private",
                                       "finish": True, "reporter": ""}, "event": {"topic": "run.started"}, "state": {},
                            "participants": [{"id": "p1", "role": "participant"}, {"id": "m", "role": "moderator"}]})
    offered = [effect["actor_id"] for effect in started["effects"]]
    return {"ok": error(["a", "b", "c"], ["a", "b", "c"]) == 0 and error(["c", "b", "a"], ["a", "b", "c"]) == 4
            and offered == ["p1"]}
