"""Turn-taking rules for group discussion, and a participation measure that leaves moderators out.

Every rule decides who speaks next and tells the Discussion activity (turns set to "procedure") with a
`discussion.invite` event. After each turn it publishes `turn.status` with the group's counts so far.
Participants whose role is "moderator" are outside the group: they are never put in the rotation, are left out of
the counts, and are asked first after each group member's message whether they want to step in.
"""

import copy
import math
from random import Random

NOTHING = {"effects": []}


def group(people):
    return [person["id"] for person in people if person.get("role") != "moderator"]


def moderators(people):
    return [person["id"] for person in people if person.get("role") == "moderator"]


def fresh(people):
    members = group(people)
    return {"turn": 0, "member_turns": 0, "messages": {key: 0 for key in members}, "words": {key: 0 for key in members},
            "last": None, "last_member": None, "phase": "speaking", "pending": {}, "yes": [], "quiet": 0,
            "competitors": [], "round": 0}


def tally(state, actor, text):
    if actor in state["messages"]:
        state["messages"][actor] += 1
        state["words"][actor] += len(str(text).split())
    return state


def status(state, speaker, last_message):
    return {"type": "emit", "topic": "turn.status", "audience": "shared", "payload": {
        "speaker": speaker, "turn": state["turn"], "messages": dict(state["messages"]), "words": dict(state["words"]),
        "last_message": str(last_message)[:1000], "competitors": list(state["competitors"])}}


def invite(state, actor):
    state.update(phase="speaking", pending={}, yes=[])
    return [{"type": "emit", "topic": "discussion.invite", "audience": "shared", "payload": {"actor_id": actor}}]


def ask(state, actors, phase):
    """Ask each actor privately whether they want to speak next. With nobody to ask, the last member goes on."""
    if not actors:
        return invite(state, state["last_member"])
    state["round"] += 1
    state.update(phase=phase, yes=[], pending={f"{phase}.{state['round']}.{actor}": actor for actor in actors})
    return [{"type": "offer", "id": offer_id, "actor_id": actor, "actions": [{
        "type": "turn.request", "prompt": "Do you want to speak next? Answer true to ask for the floor, false to listen.",
        "audience": [actor], "schema": {"type": "boolean"}, "sample": True}]} for offer_id, actor in state["pending"].items()]


def offer_pass(state, actor, people):
    """Ask the speaker who finished to pick the next speaker, or leave the floor open."""
    others = [person["id"] for person in people if person["id"] != actor]
    state["round"] += 1
    offer_id = f"pass.{state['round']}"
    state.update(phase="pass", yes=[], pending={offer_id: actor})
    names = ", ".join(f"{person['id']} ({person.get('display_name', person['id'])})" for person in people
                      if person["id"] != actor)
    return [{"type": "offer", "id": offer_id, "actor_id": actor, "actions": [{
        "type": "turn.pass", "prompt": f"Who should speak next? Name one of {names}, or 'anyone' to leave the floor open.",
        "audience": "shared", "schema": {"enum": others + ["anyone"]}, "sample": "anyone"}]}]


def quietest(state, candidates, seed):
    """The candidate with the fewest words so far; ties are broken with the run's seed."""
    fewest = min(state["words"].get(key, 0) for key in candidates)
    tied = [key for key in candidates if state["words"].get(key, 0) == fewest]
    return Random(seed).choice(tied)


def done(state, effects):
    return {"effects": [{"type": "update", "state": state}] + effects}


# The rules ------------------------------------------------------------------

def opening(kind, request, state):
    people = request["participants"]
    if kind == "least_active":
        return invite(state, quietest(state, group(people), request["seed"]))
    if kind == "raise_hands":
        return ask(state, group(people), "bids")  # moderators never open the discussion
    return invite(state, group(people)[0])


def after_turn(kind, request, state):
    """Choose what happens once a turn is over and no moderator stepped in."""
    people = request["participants"]
    if kind == "least_active":
        return invite(state, quietest(state, group(people), request["seed"]))
    if kind == "raise_hands":
        return ask(state, [person["id"] for person in people if person["id"] != state["last"]], "bids")
    return offer_pass(state, state["last"], people)


def winner(kind, request, state, yes):
    if kind == "raise_hands":
        mods = [key for key in yes if key in moderators(request["participants"])]
        if mods:
            return mods[0]
        if request["config"].get("tie_break") == "random":
            return Random(request["seed"]).choice(yes)
        return quietest(state, yes, request["seed"])
    return yes[0]


def nobody(kind, request, state):
    """Nobody asked for the floor: count a quiet round, end the step after enough of them."""
    config = request["config"]
    state["quiet"] += 1
    if state["quiet"] >= config["quiet_rounds"]:
        state.update(phase="ended", pending={}, yes=[])
        return [{"type": "finish"}] if config["finish"] else []
    if kind == "raise_hands":  # ask again, this time letting the last speaker go on too
        return ask(state, [person["id"] for person in request["participants"]], "bids")
    return invite(state, state["last_member"] or group(request["participants"])[0])  # the speaker continues


def react(request, kind):
    event, config, people = request["event"], request["config"], request["participants"]
    if event["topic"] == "run.started":
        state = fresh(people)
        if not group(people):  # only moderators: there is no discussion to run
            state["phase"] = "ended"
            return done(state, [{"type": "finish"}] if config["finish"] else [])
        return done(state, opening(kind, request, state))
    if event["topic"] != "action.accepted":
        return NOTHING
    state = copy.deepcopy(request["state"])
    if state.get("phase") == "ended":
        return NOTHING
    action_type, actor = event.get("action_type"), event.get("actor_id")
    if action_type == config["action_type"]:
        state["turn"] += 1
        tally(state, actor, event.get("payload", ""))
        state["last"] = actor
        member = actor in state["messages"]
        if member:
            state["last_member"] = actor
            state["member_turns"] += 1
        effects = [status(state, actor, event.get("payload", ""))]
        state["competitors"] = []
        # Only members' messages use up turns, so a moderator does not shorten the group's discussion.
        if state["member_turns"] >= config["max_turns"]:
            state.update(phase="ended", pending={}, yes=[])
            return done(state, effects + ([{"type": "finish"}] if config["finish"] else []))
        mods = moderators(people)
        if member and mods and kind != "raise_hands":
            return done(state, effects + ask(state, mods, "moderators"))
        return done(state, effects + after_turn(kind, request, state))
    if not request.get("own_event") or event.get("offer_id") not in state.get("pending", {}):
        return NOTHING
    del state["pending"][event["offer_id"]]
    if action_type == "turn.pass":
        if event["payload"] == "anyone":
            # Offers are answered in the order they are made, so shuffle it: the first to say yes is not always
            # whoever is listed first.
            others = [person["id"] for person in people if person["id"] != actor]
            Random(request["seed"]).shuffle(others)
            return done(state, ask(state, others, "bids"))
        state["quiet"] = 0
        return done(state, invite(state, event["payload"]))
    if event.get("payload") is True:
        state["yes"].append(actor)
    if state["pending"]:
        return done(state, [])
    yes, phase = state["yes"], state["phase"]
    if phase == "moderators":
        return done(state, invite(state, yes[0]) if yes else after_turn(kind, request, state))
    if not yes:
        return done(state, nobody(kind, request, state))
    state["quiet"] = 0
    state["competitors"] = list(yes) if len(yes) > 1 else []
    return done(state, invite(state, winner(kind, request, state, yes)))


def least_active(request):
    """Always invite the group member with the fewest words so far."""
    return react(request, "least_active")


# Measure ------------------------------------------------------------------------

def evenness(counts):
    """Normalized Shannon entropy of the shares: 1 when everyone contributes equally, 0 when one person does everything."""
    total = sum(counts)
    if len(counts) < 2:
        return 1.0
    if total == 0:
        return None
    entropy = sum(-count / total * math.log(count / total) for count in counts if count)
    return round(entropy / math.log(len(counts)), 6)


def contributions(request):
    """Discussion messages and words per group member (moderators left out), or None when no member wrote."""
    config = request["config"]
    members = group(request["experiment"].get("participants", []))
    messages, words = {key: 0 for key in members}, {key: 0 for key in members}
    for record in request["authorized_events"]:
        if (record["event_type"] == "action_applied" and record["payload"]["action_type"] == config["action_type"]
                and record["actor_id"] in messages and (not config["step"] or record["step_id"] == config["step"])):
            messages[record["actor_id"]] += 1
            words[record["actor_id"]] += len(str(record["payload"]["value"]).split())
    return (messages, words) if sum(messages.values()) else None


NO_MESSAGES = {"status": "missing", "value": None,
               "details": {"reason": "No discussion messages from group members were recorded."}}


def group_balance(request):
    counted = contributions(request)
    if counted is None:
        return NO_MESSAGES
    messages, words = counted
    return {"status": "ok", "value": evenness(list(words.values())), "unit": "evenness (0-1)", "details": {
        "messages": messages, "words": words, "message_evenness": evenness(list(messages.values()))}}


def gini(counts):
    """Gini coefficient: sum of |t_i - t_j| over all pairs (i, j), divided by 2 n sum(t). 0 is perfectly equal."""
    total = sum(counts)
    if total == 0:
        return None
    return round(sum(abs(a - b) for a in counts for b in counts) / (2 * len(counts) * total), 6)


def participation_gini(request):
    counted = contributions(request)
    if counted is None:
        return NO_MESSAGES
    messages, words = counted
    return {"status": "ok", "value": gini(list(words.values())), "unit": "Gini of words (0-1, lower is more equal)",
            "details": {"messages": messages, "words": words, "message_gini": gini(list(messages.values()))}}


def self_test():
    return {"ok": evenness([3, 3, 3]) == 1 and evenness([5, 0]) == 0 and evenness([1]) == 1
            and gini([4, 4, 4]) == 0 and gini([0, 0, 9]) == round(2 / 3, 6) and gini([0, 0]) is None}


def raise_hands(request):
    """Before each turn, ask everyone but the last speaker whether they want the floor; pick among the raised hands."""
    return react(request, "raise_hands")


def speaker_selects(request):
    """The speaker picks who goes next; 'anyone' opens the floor to raised hands; if nobody wants it, the speaker goes on."""
    return react(request, "speaker_selects")
