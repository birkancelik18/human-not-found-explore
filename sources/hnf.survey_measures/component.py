"""Measures computed from questionnaire answers: item contrast, answer-key accuracy, weight of advice, change."""


def answers(request, step):
    """Each participant's latest questionnaire answers in the step (empty step: whole run)."""
    latest = {}
    for record in request["authorized_events"]:
        if step and record["step_id"] != step:
            continue
        if record["event_type"] == "action_applied" and record["payload"]["action_type"] == "questionnaire.answers":
            latest[record["actor_id"]] = record["payload"]["value"]
    return latest


def mean(values):
    return round(sum(values) / len(values), 6) if values else None


def missing(reason):
    return {"status": "missing", "value": None, "details": {"reason": reason}}


def in_group(item, prefixes):
    return any(item.startswith(prefix) for prefix in prefixes)


def item_contrast(request):
    config = request["config"]
    latest = answers(request, config["step"])
    by_participant = {}
    for actor, answer in sorted(latest.items()):
        numbers = {key: value for key, value in answer.items() if type(value) in (int, float)}
        a = [value for key, value in numbers.items() if in_group(key, config["group_a"])]
        b = [value for key, value in numbers.items() if in_group(key, config["group_b"])]
        if a and b:
            by_participant[actor] = {"mean_a": mean(a), "mean_b": mean(b), "contrast": round(mean(a) - mean(b), 6)}
    if not by_participant:
        return missing("No participant answered scale items in both groups in this step.")
    rows = list(by_participant.values())
    return {"status": "ok", "value": mean([row["contrast"] for row in rows]), "unit": "scale points (group A - group B)",
            "details": {"mean_a": mean([row["mean_a"] for row in rows]), "mean_b": mean([row["mean_b"] for row in rows]),
                        "by_participant": by_participant}}


def answer_key_accuracy(request):
    config = request["config"]
    latest = answers(request, config["step"])
    key = {entry["item"]: entry["answer"] for entry in config["answer_key"]}
    by_participant, by_item = {}, {item: [] for item in key}
    for actor, answer in sorted(latest.items()):
        scored = [str(answer[item]) == correct for item, correct in key.items() if item in answer]
        for item, correct in key.items():
            if item in answer:
                by_item[item].append(str(answer[item]) == correct)
        if scored:
            by_participant[actor] = {"correct": sum(scored), "answered": len(scored), "accuracy": mean(scored)}
    if not by_participant:
        return missing("No participant answered an item in the answer key in this step.")
    return {"status": "ok", "value": mean([row["accuracy"] for row in by_participant.values()]), "unit": "share correct",
            "details": {"by_participant": by_participant,
                        "by_item": {item: mean(marks) for item, marks in by_item.items() if marks}}}


def weight_of_advice(request):
    config = request["config"]
    first, final = answers(request, config["first_step"]), answers(request, config["final_step"])
    advice = {entry["item"]: entry["value"] for entry in config["advice"]}
    by_participant = {}
    for actor in sorted(set(first) & set(final)):
        weights = {}
        for item, offered in advice.items():
            before, after = first[actor].get(item), final[actor].get(item)
            if type(before) not in (int, float) or type(after) not in (int, float) or offered == before:
                continue  # the weight is undefined when the advice equals the first estimate
            weight = (after - before) / (offered - before)
            weights[item] = round(min(max(weight, 0.0), 1.0) if config["truncate"] else weight, 6)
        if weights:
            by_participant[actor] = {"weights": weights, "mean": mean(list(weights.values()))}
    if not by_participant:
        return missing("No participant gave a first and a final estimate that differ from the advice.")
    return {"status": "ok", "value": mean([row["mean"] for row in by_participant.values()]), "unit": "weight of advice (0 = ignored, 1 = adopted)",
            "details": {"by_participant": by_participant}}


def step_change(request):
    config = request["config"]
    item, target = config["item"], config["target"]
    before, after = answers(request, config["before_step"]), answers(request, config["after_step"])
    pairs = {actor: (before[actor].get(item), after[actor].get(item)) for actor in sorted(set(before) & set(after))
             if item in before[actor] and item in after[actor]}
    if not pairs:
        return missing(f"No participant answered '{item}' in both steps.")
    if target:
        share = lambda index: mean([pair[index] == target for pair in pairs.values()])
        value, unit, details = round(share(1) - share(0), 6), f"change in the share answering '{target}'", {
            "before": share(0), "after": share(1)}
    else:
        numbers = {actor: pair for actor, pair in pairs.items() if all(type(v) in (int, float) for v in pair)}
        if not numbers:
            return missing(f"'{item}' has no numeric answers; set the answer to count.")
        avg = lambda index: mean([pair[index] for pair in numbers.values()])
        value, unit, details = round(avg(1) - avg(0), 6), "change in the mean answer", {"before": avg(0), "after": avg(1)}
    details["by_participant"] = {actor: {"before": pair[0], "after": pair[1]} for actor, pair in pairs.items()}
    return {"status": "ok", "value": value, "unit": unit, "details": details}


def self_test():
    def run(function, config, events):
        return function({"config": config, "authorized_events": events})["value"]
    def said(actor, step, value):
        return {"event_type": "action_applied", "step_id": step, "actor_id": actor,
                "payload": {"action_type": "questionnaire.answers", "value": value}}
    rated = [said("p1", "s", {"true_1": 4, "false_1": 1}), said("p2", "s", {"true_1": 3, "false_1": 2})]
    advice = [said("p1", "a", {"w": 100}), said("p1", "b", {"w": 150})]
    intent = [said("p1", "a", {"i": "No"}), said("p1", "b", {"i": "Yes"}), said("p2", "a", {"i": "Yes"}), said("p2", "b", {"i": "Yes"})]
    return {"ok": run(item_contrast, {"step": "s", "group_a": ["true_"], "group_b": ["false_"]}, rated) == 2.0
            and run(answer_key_accuracy, {"step": "s", "answer_key": [{"item": "true_1", "answer": "4"}]}, rated) == 0.5
            and run(weight_of_advice, {"first_step": "a", "final_step": "b", "truncate": True,
                                       "advice": [{"item": "w", "value": 200}]}, advice) == 0.5
            and run(step_change, {"item": "i", "target": "Yes", "before_step": "a", "after_step": "b"}, intent) == 0.5}
