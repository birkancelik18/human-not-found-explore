"""Economic games: giving and transfers, offers and responses, public goods, payoff-matrix games, and their measures.

Every game emits a shared `econ.result` event when a pair or group finishes a round:
{game, round, amounts: [{actor, role, kind, amount, of}], payoffs: {participant: earnings}, max_total, ...}.
The measures read these events.
"""

NOTHING = {"effects": []}


# Shared helpers -------------------------------------------------------------

def money(value):
    return round(float(value), 2)


def accepted_here(request, *action_types):
    event = request["event"]
    return (event["topic"] == "action.accepted" and request["own_event"]
            and event["action_type"] in action_types and "payload" in event)


def pairs_of(request, first_role, second_role):
    """Pair participants: by listed order (1st with 2nd, 3rd with 4th, ...) or by their role."""
    people = request["participants"]
    if request["config"].get("roles") == "participant_role":
        firsts = [person["id"] for person in people if person["role"] == first_role]
        seconds = [person["id"] for person in people if person["role"] == second_role]
    else:
        ids = [person["id"] for person in people]
        firsts, seconds = ids[0::2], ids[1::2]
    pairs = [list(pair) for pair in zip(firsts, seconds)]
    if not pairs:
        raise ValueError(f"This game needs at least one {first_role} and one {second_role}.")
    return pairs


def offer(offer_id, actor, action_type, prompt, schema, sample, audience):
    return {"type": "offer", "id": offer_id, "actor_id": actor, "actions": [
        {"type": action_type, "prompt": prompt, "schema": schema, "sample": sample, "audience": audience}]}


def result(payload):
    return {"type": "emit", "topic": "econ.result", "audience": "shared", "payload": payload}


def amount_schema(maximum):
    return {"type": "number", "minimum": 0, "maximum": money(maximum)}


def end_or_next(request, state, next_round):
    """After a round: start the next one, or end the step (unless finish is off)."""
    if state["round"] < request["config"]["rounds"]:
        state["round"] += 1
        return next_round(state)
    state["over"] = True
    return [{"type": "finish"}] if request["config"]["finish"] else []


def saved(state, effects):
    """Save the component state (as it is after this reaction) before the other effects."""
    return {"effects": [{"type": "update", "state": state}] + effects}


# Give and transfer (dictator; trust with multiplier and return step) ------

def give(request):
    config, event = request["config"], request["event"]
    endowment, multiplier = config["endowment"], config["multiplier"]

    def send_offers(state):
        effects = []
        for sender, receiver in state["pairs"]:
            note = f" Whatever you send is multiplied by {multiplier:g} before {receiver} receives it." if multiplier != 1 else ""
            back = f" {receiver} can then send any part of it back to you." if config["return_step"] else ""
            effects.append(offer("send." + sender, sender, "give.send",
                                 f"{config['prompt']}\nRound {state['round']} of {config['rounds']}. You have {endowment:g}. "
                                 f"Choose how much to send to {receiver} (0 to {endowment:g}).{note}{back}",
                                 amount_schema(endowment), money(endowment / 2), [receiver]))
        return effects

    if event["topic"] == "run.started":
        state = {"round": 1, "pairs": pairs_of(request, "sender", "receiver"), "sent": {}, "done": []}
        return saved(state, send_offers(state))
    if not accepted_here(request, "give.send", "give.return"):
        return NOTHING
    state = dict(request["state"])
    if state.get("over"):
        return NOTHING
    actor, value = event["actor_id"], event["payload"]
    sender, receiver = next(pair for pair in state["pairs"] if actor in pair)
    if event["action_type"] == "give.send":
        state["sent"] = {**state["sent"], sender: value}
        received = value * multiplier
        if config["return_step"] and received > 0:
            return saved(state, [offer(
                "return." + receiver, receiver, "give.return",
                f"Round {state['round']}: {sender} sent you {value:g}, which became {money(received):g}. "
                f"Choose how much of it to send back to {sender} (0 to {money(received):g}).",
                amount_schema(received), money(received / 2), [sender])])
        returned = 0 if config["return_step"] else None
    else:
        returned = value
    sent = state["sent"][sender]
    received = money(sent * multiplier)
    amounts = [{"actor": sender, "role": "sender", "kind": "sent", "amount": sent, "of": endowment}]
    if returned is not None:
        amounts.append({"actor": receiver, "role": "receiver", "kind": "returned", "amount": returned, "of": received})
    payoffs = {sender: money(endowment - sent + (returned or 0)),
               receiver: money(config["receiver_endowment"] + received - (returned or 0))}
    effects = [result({"game": "trust" if config["return_step"] else "dictator", "round": state["round"],
                       "amounts": amounts, "payoffs": payoffs,
                       "max_total": money(endowment * max(multiplier, 1) + config["receiver_endowment"])})]
    state["done"] = state["done"] + [sender]
    if len(state["done"]) == len(state["pairs"]):
        state.update(sent={}, done=[])
        effects += end_or_next(request, state, send_offers)
    return saved(state, effects)


# Offer and respond (ultimatum, optional counter-offers) ---------------------

def ultimatum(request):
    config, event = request["config"], request["event"]
    endowment = config["endowment"]

    def propose(index, proposer, responder, counter):
        kind = "a counter-offer" if counter else "an offer"
        return offer(f"offer{index}", proposer, "ultimatum.offer",
                     f"{config['prompt']}\nThere are {endowment:g} to split with {responder}. Make {kind}: "
                     f"how much {responder} gets (0 to {endowment:g}). You keep the rest if {responder} accepts; "
                     "if they reject, you both get nothing.",
                     amount_schema(endowment), money(endowment / 2), [responder])

    if event["topic"] == "run.started":
        games = [{"proposer": a, "responder": b, "offers": [], "responses": []} for a, b in pairs_of(request, "proposer", "responder")]
        effects = [propose(index, game["proposer"], game["responder"], False) for index, game in enumerate(games)]
        return saved({"games": games, "done": 0}, effects)
    if not accepted_here(request, "ultimatum.offer", "ultimatum.respond"):
        return NOTHING
    state = dict(request["state"])
    games = [dict(game) for game in state["games"]]
    index = next(i for i, game in enumerate(games) if event["actor_id"] in (game["proposer"], game["responder"]))
    game, actor = games[index], event["actor_id"]
    other = game["responder"] if actor == game["proposer"] else game["proposer"]
    if event["action_type"] == "ultimatum.offer":
        game["offers"] = game["offers"] + [{"actor": actor, "amount": event["payload"]}]
        state["games"] = games
        return saved(state, [offer(
            f"respond{index}", other, "ultimatum.respond",
            f"{actor} offers you {event['payload']:g} of {endowment:g} and keeps {money(endowment - event['payload']):g}. "
            "Accept or reject. If you reject, you both get nothing"
            + (" this time, and you may make a counter-offer." if len(game["offers"]) <= config["counter_offers"] else "."),
            {"type": "string", "enum": ["accept", "reject"]}, "accept", [other])])
    accepted = event["payload"] == "accept"
    last = game["offers"][-1]
    game["responses"] = game["responses"] + [{"actor": actor, "amount": last["amount"], "accepted": accepted}]
    state["games"] = games
    if not accepted and len(game["offers"]) <= config["counter_offers"]:
        return saved(state, [propose(index, actor, other, True)])
    payoffs = {game["proposer"]: 0, game["responder"]: 0}
    if accepted:
        payoffs = {last["actor"]: money(endowment - last["amount"]), actor: money(last["amount"])}
    roles = {game["proposer"]: "proposer", game["responder"]: "responder"}
    state["done"] += 1
    effects = [result({
        "game": "ultimatum", "round": 1, "accepted": accepted, "responses": game["responses"], "payoffs": payoffs,
        "max_total": endowment,
        "amounts": [{"actor": item["actor"], "role": roles[item["actor"]], "kind": "offered", "amount": item["amount"],
                     "of": endowment} for item in game["offers"]]})]
    if state["done"] == len(games) and config["finish"]:
        effects.append({"type": "finish"})
    return saved(state, effects)


# Contribute to a pool (public goods, optional punishment) ------------------

def pool(request):
    config, event = request["config"], request["event"]
    endowment, people = config["endowment"], [person["id"] for person in request["participants"]]
    if len(people) < 2:
        raise ValueError("A public goods game needs at least two participants.")
    share = config["multiplier"] / len(people)

    def contribute_offers(state):
        last = state.get("last")
        effects = []
        for person in people:
            note = (f"\nLast round: contributions {last['contributions']}, group total {last['total']}, "
                    f"your earnings {last['payoffs'][person]:g}.") if last else ""
            effects.append(offer("give." + person, person, "pool.contribute",
                                 f"{config['prompt']}\nRound {state['round']} of {config['rounds']}. You have {endowment} tokens. "
                                 f"Choose how many to put in the group pool (0 to {endowment}). The pool is multiplied by "
                                 f"{config['multiplier']:g} and shared equally among all {len(people)} members; you keep "
                                 f"what you do not contribute.{note}",
                                 {"type": "integer", "minimum": 0, "maximum": endowment}, endowment // 2, []))
        return effects

    if event["topic"] == "run.started":
        state = {"round": 1, "stage": "contribute", "contributions": {}, "points": {}}
        return saved(state, contribute_offers(state))
    if not accepted_here(request, "pool.contribute", "pool.punish"):
        return NOTHING
    state = dict(request["state"])
    if state.get("over"):
        return NOTHING
    key = "contributions" if event["action_type"] == "pool.contribute" else "points"
    state[key] = {**state[key], event["actor_id"]: event["payload"]}
    if len(state[key]) < len(people):
        return saved(state, [])
    contributions = state["contributions"]
    total = sum(contributions.values())
    earnings = {person: endowment - contributions[person] + total * share for person in people}
    if config["punishment"] and state["stage"] == "contribute":
        state["stage"] = "punish"
        shown = ", ".join(f"{person}: {contributions[person]}" for person in people)
        effects = [{"type": "emit", "topic": "pool.contributions", "audience": "shared",
                    "payload": {"round": state["round"], "contributions": contributions, "total": total}}]
        for person in people:
            others = [other for other in people if other != person]
            effects.append(offer("punish." + person, person, "pool.punish",
                                 f"Round {state['round']} contributions: {shown}. Your earnings so far: {money(earnings[person]):g}. "
                                 f"You may assign 0 to {config['max_points']} deduction points to each other member. Each point "
                                 f"costs you {config['punishment_cost']:g} and reduces that member's earnings by "
                                 f"{config['punishment_effect']:g}.",
                                 {"type": "object", "additionalProperties": False, "required": others,
                                  "properties": {other: {"type": "integer", "minimum": 0, "maximum": config["max_points"]}
                                                 for other in others}},
                                 {other: 0 for other in others}, []))
        return saved(state, effects)
    amounts = [{"actor": person, "role": "member", "kind": "contributed", "amount": contributions[person], "of": endowment}
               for person in people]
    if config["punishment"]:
        points = state["points"]
        for person in people:
            given = sum(points[person].values())
            received = sum(points[other].get(person, 0) for other in people if other != person)
            earnings[person] -= given * config["punishment_cost"] + received * config["punishment_effect"]
            amounts.append({"actor": person, "role": "member", "kind": "punishment", "amount": given,
                            "of": config["max_points"] * (len(people) - 1)})
    payoffs = {person: money(value) for person, value in earnings.items()}
    effects = [result({"game": "public_goods", "round": state["round"], "amounts": amounts, "payoffs": payoffs,
                       "max_total": money(endowment * len(people) * max(config["multiplier"], 1)), "total": total})]
    state["last"] = {"contributions": contributions, "total": total, "payoffs": payoffs}
    state.update(stage="contribute", contributions={}, points={})
    effects += end_or_next(request, state, contribute_offers)
    return saved(state, effects)


# Payoff-matrix game (prisoner's dilemma by default) ------------------------

def payoff_table(config):
    table = {(cell["row"], cell["column"]): (cell["row_payoff"], cell["column_payoff"]) for cell in config["payoffs"]}
    missing = [(a, b) for a in config["moves"] for b in config["moves"] if (a, b) not in table]
    if missing:
        raise ValueError(f"The payoff table has no entry for {missing[0][0]} against {missing[0][1]}.")
    return table


def matrix(request):
    config, event = request["config"], request["event"]
    moves, table = config["moves"], payoff_table(config)

    def described(row):
        """The payoff table from one player's side."""
        mine, theirs = (0, 1) if row else (1, 0)
        cell = (lambda a, b: table[(a, b)]) if row else (lambda a, b: table[(b, a)])
        return "; ".join(f"you {a}, other {b}: you get {cell(a, b)[mine]:g}, they get {cell(a, b)[theirs]:g}"
                         for a in moves for b in moves)

    def choice_offers(state):
        effects = []
        for pair in state["pairs"]:
            for me, other in (pair, pair[::-1]):
                last = state.get("last", {}).get(me)
                recap = f"\nLast round you chose {last[0]}, {other} chose {last[1]}, and you earned {last[2]:g}." if last else ""
                effects.append(offer("choose." + me, me, "matrix.choose",
                                     f"{config['prompt']}\nRound {state['round']} of {config['rounds']} with {other}. "
                                     f"Both choose at the same time. Payoffs: {described(me == pair[0])}.{recap}",
                                     {"type": "string", "enum": moves}, moves[0], []))
        return effects

    if event["topic"] == "run.started":
        state = {"round": 1, "pairs": pairs_of(request, "row player", "column player"), "choices": {}}
        return saved(state, choice_offers(state))
    if not accepted_here(request, "matrix.choose"):
        return NOTHING
    state = dict(request["state"])
    if state.get("over"):
        return NOTHING
    state["choices"] = {**state["choices"], event["actor_id"]: event["payload"]}
    pair = next(pair for pair in state["pairs"] if event["actor_id"] in pair)
    effects = []
    if all(person in state["choices"] for person in pair):
        row, column = pair
        a, b = state["choices"][row], state["choices"][column]
        gain = table[(a, b)]
        state["last"] = {**state.get("last", {}), row: [a, b, gain[0]], column: [b, a, gain[1]]}
        effects.append(result({"game": "matrix", "round": state["round"], "choices": {row: a, column: b},
                               "cooperative_move": config["cooperative_move"], "payoffs": {row: gain[0], column: gain[1]},
                               "amounts": [], "max_total": max(sum(cell) for cell in table.values())}))
    if len(state["choices"]) == 2 * len(state["pairs"]):
        state["choices"] = {}
        effects += end_or_next(request, state, choice_offers)
    return saved(state, effects)


# Measures -------------------------------------------------------------------

def missing(reason):
    return {"status": "missing", "value": None, "details": {"reason": reason}}


def results(request):
    step = request["config"]["step"]
    return [record["payload"]["payload"] for record in request["authorized_events"]
            if record["event_type"] == "component_event" and record["payload"].get("topic") == "econ.result"
            and (not step or record["step_id"] == step)]


def mean(values):
    return round(sum(values) / len(values), 6) if values else None


def grouped(entries, key):
    groups = {}
    for entry in entries:
        groups.setdefault(str(entry[key]), []).append(entry["amount"])
    return {name: mean(values) for name, values in sorted(groups.items())}


def amounts_given(request):
    kind = request["config"]["kind"]
    entries = [dict(entry, round=item["round"]) for item in results(request) for entry in item["amounts"]
               if kind == "all" or entry["kind"] == kind]
    if not entries:
        return missing("No amounts of this kind were recorded.")
    shares = [entry["amount"] / entry["of"] for entry in entries if entry["of"]]
    return {"status": "ok", "value": mean([entry["amount"] for entry in entries]), "unit": "mean amount", "details": {
        "n": len(entries), "mean_share_of_available": mean(shares), "by_kind": grouped(entries, "kind"),
        "by_role": grouped(entries, "role"), "by_round": grouped(entries, "round"),
        "distribution": sorted(entry["amount"] for entry in entries)}}


def cooperation_rate(request):
    decisions = []
    for item in results(request):
        if item["game"] == "matrix" and item["cooperative_move"]:
            decisions += [(actor, item["round"], 1.0 if move == item["cooperative_move"] else 0.0)
                          for actor, move in item["choices"].items()]
        elif item["game"] == "public_goods":
            decisions += [(entry["actor"], item["round"], entry["amount"] / entry["of"] if entry["of"] else 0.0)
                          for entry in item["amounts"] if entry["kind"] == "contributed"]
    if not decisions:
        return missing("No payoff-matrix choices or public goods contributions were recorded.")
    by = lambda index: {str(key): mean([d[2] for d in decisions if d[index] == key])
                        for key in sorted({d[index] for d in decisions})}
    return {"status": "ok", "value": mean([d[2] for d in decisions]), "unit": "rate (0-1)",
            "details": {"n": len(decisions), "by_participant": by(0), "by_round": by(1)}}


def gini(values):
    values = sorted(values)
    total = sum(values)
    if len(values) < 2 or total <= 0:
        return 0.0
    weighted = sum((index + 1) * value for index, value in enumerate(values))
    return round((2 * weighted) / (len(values) * total) - (len(values) + 1) / len(values), 6)


def payoffs(request):
    items = results(request)
    if not items:
        return missing("No game results were recorded.")
    totals = {}
    for item in items:
        for actor, value in item["payoffs"].items():
            totals[actor] = round(totals.get(actor, 0) + value, 6)
    possible = sum(item["max_total"] for item in items)
    return {"status": "ok", "value": mean(list(totals.values())), "unit": "mean earnings per participant", "details": {
        "by_participant": totals, "total": round(sum(totals.values()), 6),
        "efficiency": round(sum(totals.values()) / possible, 6) if possible else None,
        "inequality_gini": gini(list(totals.values()))}}


def acceptance_rate(request):
    responses = [response for item in results(request) if item["game"] == "ultimatum" for response in item["responses"]]
    if not responses:
        return missing("No offer was answered.")
    accepted = [response["amount"] for response in responses if response["accepted"]]
    rejected = [response["amount"] for response in responses if not response["accepted"]]
    return {"status": "ok", "value": round(len(accepted) / len(responses), 6), "unit": "rate (0-1)", "details": {
        "responses": len(responses), "accepted": len(accepted), "mean_accepted_offer": mean(accepted),
        "mean_rejected_offer": mean(rejected)}}


def self_test():
    table = payoff_table({"moves": ["C", "D"], "payoffs": [
        {"row": a, "column": b, "row_payoff": 1, "column_payoff": 1} for a in "CD" for b in "CD"]})
    return {"ok": gini([1, 1, 1]) == 0 and gini([0, 0, 1]) == round(2 / 3, 6) and len(table) == 4
            and mean([1, 2]) == 1.5}
