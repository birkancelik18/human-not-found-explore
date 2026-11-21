"""The study templates. scripts/build.py publishes each spec in a temporary workspace and exports it as a template."""

V = "1.0.0"
SIM = ("Participants are simulated: each is a Model participant, using the free test model until you choose a "
       "model, so the first runs only check the design; with the test model every participant takes the sample answer.")


# Packages with a newer version than V.
VERSIONS = {"hnf.ranking_tasks": "1.0.1", "hnf.moderator": "1.0.2", "hnf.turn_taking": "1.0.2"}


def ref(component, **config):
    return {"id": component, "version": VERSIONS.get(component.rsplit(".", 1)[0], V), "config": config}


def people(count, roles=None, private=None, instructions=""):
    roles, private = roles or {}, private or {}
    return [{"id": f"p{i}", "display_name": f"Participant {i}", "enabled": True, "role": roles.get(i, "participant"),
             "agent": ref("hnf.participants.model", model_ref="default", persona="", instructions=instructions),
             "private_context": private.get(i, {})} for i in range(1, count + 1)]


def measure(identifier, label, component, **config):
    return {"id": identifier, "label": label, "scope": "run", "evaluator": ref(component, **config)}


def spec(experiment_id, title, description, question, participants, measurements, components=(), steps=None,
         conditions=None, actions=100):
    result = {"schema_version": "2.0.0", "experiment_id": experiment_id, "title": title, "description": description,
              "research": {"question": question, "hypotheses": []}, "participants": participants,
              "environment": {"initial_state": {"shared": {}, "private_by_participant": {}}},
              "components": list(components), "conditions": conditions or [{"id": "main", "label": "Main", "overrides": []}],
              "measurements": measurements,
              "execution": {"repetitions_per_condition": 10, "max_model_calls_per_run": actions * 2,
                            "max_actions_per_run": actions, "max_wall_seconds_per_run": 3600,
                            "max_estimated_cost_usd_per_run": 2.0, "seed": 1, "max_memory_events": 40}}
    if steps:
        result["steps"] = steps
    return result


def condition(identifier, label, *overrides):
    return {"id": identifier, "label": label, "overrides": [{"path": path, "value": value} for path, value in overrides]}


EG = "hnf.economic_games."
PG_PROMPT = ("You are one of four members of a group. Tokens you earn are converted to money at the end of the study.")

# The murder case used by the two hidden-profile templates. It is new, written for these templates; it follows
# the hidden-profile paradigm of Stasser & Stewart (1992) but is not their case.
SUSPECTS = ["Dana Whitlow", "Marcus Hale", "Lena Ortiz"]
CASE = ("Robert Kline, owner of the Harbor Hotel, was found dead in his office at 11 pm, poisoned by a sedative in his tea. "
        "The police have three suspects: Dana Whitlow (his business partner), Marcus Hale (the night manager) and "
        "Lena Ortiz (the head chef). Exactly one of them did it.")
SHARED = ["Marcus Hale argued loudly with Robert Kline that afternoon after being told he would be fired.",
          "Marcus Hale's fingerprints were found on the office door handle.",
          "Nobody can confirm where Marcus Hale was between 10 and 11 pm.",
          "Lena Ortiz was seen leaving the kitchen at 10:30 pm.",
          "Dana Whitlow says she spent the whole evening at home."]
UNIQUE = {
    1: [("keycard", ["key card", "loading dock"],
         "The security log shows Marcus Hale's key card opening the loading dock, at the far end of the building, at 10:40 pm."),
        ("car", ["car park", "dana's car"], "A guest saw Dana Whitlow's car in the staff car park at 10:50 pm.")],
    2: [("lawyer", ["lawyer", "partnership"],
         "Robert Kline had told his lawyer he would end his partnership with Dana Whitlow the next morning."),
        ("rounds", ["rounds", "every evening"], "Marcus Hale opens the office door every evening as part of his rounds.")],
    3: [("receipt", ["receipt", "pharmacy"],
         "A pharmacy receipt for the same sedative, in Dana Whitlow's name, was found in a hotel bin."),
        ("waiters", ["waiters", "10:35"], "Two waiters say Lena Ortiz was back in the kitchen by 10:35 pm and stayed there.")],
}
CLUES = [{"id": clue_id, "keywords": keywords, "kind": "unique"} for items in UNIQUE.values() for clue_id, keywords, _ in items]
MYSTERY_PRIVATE = {i: {"case": CASE, "clues_everyone_has": SHARED, "your_own_clues": [text for *_, text in UNIQUE[i]],
                       "note": "The other members have their own clues, which may differ from yours."} for i in UNIQUE}
MYSTERY_TALK = ref("hnf.group_discussion.discussion", turns="round_robin", rounds=3,
                   prompt="Discuss the case with your group. Share the clues you have; the others may know things you do not.",
                   sample="Here is what I know about the case so far.", finish=True)

MOON_ITEMS = ["Box of matches", "Food concentrate", "50 feet of nylon rope", "Parachute silk", "Portable heating unit",
              "Two .45 calibre pistols", "One case of dehydrated milk", "Two 100-lb tanks of oxygen", "Stellar map",
              "Self-inflating life raft", "Magnetic compass", "5 gallons of water", "Signal flares",
              "First aid kit including injection needles", "Solar-powered FM receiver-transmitter"]
MOON_KEY = ["Two 100-lb tanks of oxygen", "5 gallons of water", "Stellar map", "Food concentrate",
            "Solar-powered FM receiver-transmitter", "50 feet of nylon rope", "First aid kit including injection needles",
            "Parachute silk", "Self-inflating life raft", "Signal flares", "Two .45 calibre pistols",
            "One case of dehydrated milk", "Portable heating unit", "Magnetic compass", "Box of matches"]
MOON_PROMPT = ("You are a member of a space crew that was to meet the mother ship on the lighted surface of the moon. "
               "Mechanical trouble forced your ship to crash-land 200 miles from the meeting point. Only 15 items were "
               "left intact. Rank them by how important they are for reaching the mother ship: 1 is the most important.")

CHOICE_DILEMMA = ("Sam is a mid-career engineer with a secure, adequately paid job at a large company. A small new firm "
                  "offers Sam a job with a much higher salary and a share in the business if it succeeds, but the firm "
                  "may fail within a year. What is the lowest chance that the new firm succeeds at which Sam should "
                  "take the job?")
ODDS = ["1 in 10", "3 in 10", "5 in 10", "7 in 10", "9 in 10", "Sam should not take it, whatever the chance"]

TEMPLATES = [
    {"id": "public-goods-conditional-cooperation",
     "name": "Conditional cooperation in a public goods game",
     "description": (
         "Original study: Fischbacher, U., Gächter, S., & Fehr, E. (2001). Are people conditionally cooperative? Evidence "
         "from a public goods experiment. Economics Letters, 71(3), 397-404. Groups of four each received 20 tokens and "
         "chose how many to put in a group project; the project was multiplied so that each token contributed returned "
         "0.4 tokens to every member. The original measured conditional cooperation with a one-shot strategy method: "
         "each person gave an unconditional contribution and a table of contributions for every possible average "
         "contribution of the others. Public goods games are the most common paradigm in our survey of 500 "
         "multi-participant experiments (65 studies). This template runs the same group size, endowment and return "
         "over 10 repeated rounds instead of the strategy method: after each round everyone sees every member's "
         "contribution and their own earnings, so conditional cooperation shows as contributions that follow the "
         "others' previous contributions. " + SIM),
     "spec": spec("public-goods-conditional-cooperation", "Conditional cooperation (public goods)",
                  "Four members, 20 tokens each, return of 0.4 per token, 10 rounds with feedback.",
                  "Do people contribute more when the others contributed more in the previous round?",
                  people(4), [measure("contributions", "Mean contribution", EG + "amounts_given", kind="contributed", step=""),
                              measure("cooperation", "Contribution rate", EG + "cooperation_rate", step=""),
                              measure("payoffs", "Earnings", EG + "payoffs", step="")],
                  components=[ref(EG + "pool", prompt=PG_PROMPT, endowment=20, multiplier=1.6, rounds=10, punishment=False,
                                  punishment_cost=1, punishment_effect=3, max_points=10, finish=True)], actions=100)},
    {"id": "public-goods-punishment",
     "name": "Public goods game with and without punishment",
     "description": (
         "Original study: Fehr, E., & Gächter, S. (2000). Cooperation and punishment in public goods experiments. "
         "American Economic Review, 90(4), 980-994. Groups of four received 20 tokens per period and chose how much to "
         "contribute to a group project returning 0.4 tokens per token to every member, for 10 periods without and 10 "
         "periods with a punishment opportunity: after seeing the others' contributions, members could assign costly "
         "punishment points that reduced the punished member's earnings. Public goods games appear in 65 of the 500 "
         "studies in our survey. This template runs the two treatments as two conditions (between runs, not within the "
         "same group). Punishment is linear here: each point costs the punisher 1 token and removes 3 from the punished "
         "member (the original used an increasing cost schedule and a percentage reduction), with up to 10 points per "
         "member per period. " + SIM),
     "spec": spec("public-goods-punishment", "Public goods with punishment",
                  "Four members, 20 tokens, return 0.4 per token, 10 periods; condition 'punishment' adds a punishment stage.",
                  "Does the opportunity to punish raise contributions?",
                  people(4), [measure("contributions", "Mean contribution", EG + "amounts_given", kind="contributed", step=""),
                              measure("cooperation", "Contribution rate", EG + "cooperation_rate", step=""),
                              measure("payoffs", "Earnings", EG + "payoffs", step="")],
                  components=[ref(EG + "pool", prompt=PG_PROMPT, endowment=20, multiplier=1.6, rounds=10, punishment=False,
                                  punishment_cost=1, punishment_effect=3, max_points=10, finish=True)],
                  conditions=[condition("no-punishment", "Without punishment"),
                              condition("punishment", "With punishment", ("/components/0/config/punishment", True))],
                  actions=150)},
    {"id": "dictator-game",
     "name": "Dictator game",
     "description": (
         "Original study: Forsythe, R., Horowitz, J. L., Savin, N. E., & Sefton, M. (1994). Fairness in simple bargaining "
         "experiments. Games and Economic Behavior, 6(3), 347-369. Anonymous pairs: one person decided how to split a "
         "sum of money ($5 or $10) with the other, who had no say. Comparing these dictator games with ultimatum games "
         "separated fairness from fear of rejection. Dictator games appear in 58 of the 500 studies in our survey. "
         "This template has one sender and one receiver, and the two pie sizes as two conditions; the sender may send "
         "any amount from 0 to the pie. " + SIM),
     "spec": spec("dictator-game", "Dictator game", "One sender splits $5 or $10 with a receiver who has no say.",
                  "How much do people give when the other person cannot refuse?",
                  people(2, roles={1: "sender", 2: "receiver"}),
                  [measure("given", "Amount given", EG + "amounts_given", kind="sent", step=""),
                   measure("payoffs", "Earnings", EG + "payoffs", step="")],
                  components=[ref(EG + "give", prompt="You have been paired with another person, whom you will not meet. "
                                  "Amounts are in dollars.", endowment=5, multiplier=1, return_step=False,
                                  receiver_endowment=0, rounds=1, roles="order", finish=True)],
                  conditions=[condition("pie-5", "$5 pie"),
                              condition("pie-10", "$10 pie", ("/components/0/config/endowment", 10))], actions=10)},
    {"id": "brainstorming-nominal-vs-interacting",
     "name": "Brainstorming: nominal versus interacting groups",
     "description": (
         "Original study: Diehl, M., & Stroebe, W. (1987). Productivity loss in brainstorming groups: Toward the solution "
         "of a riddle. Journal of Personality and Social Psychology, 53(3), 497-509. Participants generated ideas on a "
         "problem either in interacting groups of four or alone; the ideas of four people working alone were pooled as a "
         "'nominal group' and their non-redundant ideas counted. The studies examined why interacting groups produce "
         "fewer ideas than nominal groups. Idea generation appears in 48 of the 500 studies in our survey. In this "
         "template both conditions have four participants who submit lists of ideas over three rounds (standing in for "
         "the session time): in the interacting condition everyone sees the others' ideas; in the nominal condition "
         "each works alone and only the analysis pools the ideas. Participants do not speak or wait for each other, so "
         "this design does not reproduce production blocking. The brainstorming problem is new, not the original. "
         + SIM),
     "spec": spec("brainstorming-nominal-vs-interacting", "Brainstorming: nominal vs interacting",
                  "Four participants generate ideas alone (nominal) or seeing each other's ideas (interacting).",
                  "Do interacting groups produce fewer unique ideas than the same number of people working alone?",
                  people(4), [measure("ideas", "Unique ideas", "hnf.idea_generation.ideas_count", step="")],
                  components=[ref("hnf.idea_generation.ideas", prompt="How could your town reduce the amount of waste it "
                                  "sends to landfill? Give as many ideas as you can; quantity counts and no idea is too "
                                  "unusual.", rounds=3, max_ideas=5, visible=True,
                                  sample_ideas=["Charge households by the bag for rubbish", "Open a repair cafe",
                                                "Ban single-use plastic bags in shops"], finish=True)],
                  conditions=[condition("interacting", "Interacting group of 4"),
                              condition("nominal", "Alone (nominal group of 4)", ("/components/0/config/visible", False))],
                  actions=20)},
    {"id": "ultimatum-game",
     "name": "Ultimatum game",
     "description": (
         "Original study: Forsythe, R., Horowitz, J. L., Savin, N. E., & Sefton, M. (1994). Fairness in simple bargaining "
         "experiments. Games and Economic Behavior, 6(3), 347-369. In the ultimatum condition a proposer offered a split "
         "of $5 and the responder accepted it, or rejected it so that both got nothing; offers were compared with "
         "dictator games. Ultimatum games appear in 47 of the 500 studies in our survey. This template has one "
         "proposer and one responder splitting $5, with no counter-offers. " + SIM),
     "spec": spec("ultimatum-game", "Ultimatum game", "A proposer offers a split of $5; the responder accepts or rejects.",
                  "How much do proposers offer, and which offers are rejected?",
                  people(2, roles={1: "proposer", 2: "responder"}),
                  [measure("offered", "Amount offered", EG + "amounts_given", kind="offered", step=""),
                   measure("acceptance", "Acceptance rate", EG + "acceptance_rate", step=""),
                   measure("payoffs", "Earnings", EG + "payoffs", step="")],
                  components=[ref(EG + "ultimatum", prompt="You have been paired with another person, whom you will not "
                                  "meet. Amounts are in dollars.", endowment=5, counter_offers=0, roles="order", finish=True)],
                  actions=10)},
    {"id": "trust-game",
     "name": "Trust game",
     "description": (
         "Original study: Berg, J., Dickhaut, J., & McCabe, K. (1995). Trust, reciprocity, and social history. Games and "
         "Economic Behavior, 10(1), 122-142. Both people in an anonymous pair received $10. The sender could send any "
         "part of it to the receiver; the amount sent was tripled, and the receiver decided how much to send back. "
         "Trust games appear in 47 of the 500 studies in our survey. This template follows the no-history condition: "
         "one sender, one receiver, $10 each, amount sent tripled, one round. " + SIM),
     "spec": spec("trust-game", "Trust game", "The sender sends part of $10, which is tripled; the receiver returns any part.",
                  "How much do senders trust, and how much do receivers return?",
                  people(2, roles={1: "sender", 2: "receiver"}),
                  [measure("sent", "Amount sent", EG + "amounts_given", kind="sent", step=""),
                   measure("returned", "Amount returned", EG + "amounts_given", kind="returned", step=""),
                   measure("payoffs", "Earnings", EG + "payoffs", step="")],
                  components=[ref(EG + "give", prompt="You have been paired with another person, whom you will not meet. "
                                  "Amounts are in dollars.", endowment=10, multiplier=3, return_step=True,
                                  receiver_endowment=10, rounds=1, roles="order", finish=True)], actions=10)},
    {"id": "repeated-prisoners-dilemma",
     "name": "Finitely repeated prisoner's dilemma",
     "description": (
         "Original study: Andreoni, J., & Miller, J. H. (1993). Rational cooperation in the finitely repeated prisoner's "
         "dilemma: Experimental evidence. The Economic Journal, 103(418), 570-585. Pairs played a prisoner's dilemma for "
         "a known, fixed number of rounds; the study compared fixed partners with re-matched strangers to test whether "
         "people cooperate early in a finitely repeated game to build a reputation. Prisoner's dilemma games appear in "
         "43 of the 500 studies in our survey. This template runs one ten-round game with a fixed partner (the partners "
         "design), with payoffs of 7 each for mutual cooperation, 4 each for mutual defection, and 12 and 0 when one "
         "defects; the original repeated such games many times. " + SIM),
     "spec": spec("repeated-prisoners-dilemma", "Repeated prisoner's dilemma", "Two partners play ten rounds of a prisoner's dilemma.",
                  "How does cooperation change over a known, finite number of rounds?",
                  people(2), [measure("cooperation", "Cooperation rate", EG + "cooperation_rate", step=""),
                              measure("payoffs", "Earnings", EG + "payoffs", step="")],
                  components=[ref(EG + "matrix", prompt="You will play 10 rounds with the same partner. Points are "
                                  "converted to money at the end.", moves=["Cooperate", "Defect"], payoffs=[
                                      {"row": "Cooperate", "column": "Cooperate", "row_payoff": 7, "column_payoff": 7},
                                      {"row": "Cooperate", "column": "Defect", "row_payoff": 0, "column_payoff": 12},
                                      {"row": "Defect", "column": "Cooperate", "row_payoff": 12, "column_payoff": 0},
                                      {"row": "Defect", "column": "Defect", "row_payoff": 4, "column_payoff": 4}],
                                  cooperative_move="Cooperate", rounds=10, finish=True)], actions=40)},
    {"id": "social-loafing-effort",
     "name": "Social loafing: effort alone and in a group",
     "description": (
         "Original study: Latané, B., Williams, K., & Harkins, S. (1979). Many hands make light the work: The causes and "
         "consequences of social loafing. Journal of Personality and Social Psychology, 37(6), 822-832. Participants "
         "clapped and shouted as loudly as they could, alone or in groups of up to six; sound output per person fell "
         "as group size grew, even when participants only believed others were shouting with them. Effort tasks appear "
         "in 22 of the 500 studies in our survey. In this template six participants each choose an effort level from 0 "
         "to 10 for the shouting task: in the alone condition each person's effort is recorded and credited to them; in "
         "the group condition only the group's combined effort is recorded. Chosen effort stands in for measured sound. "
         + SIM),
     "spec": spec("social-loafing-effort", "Social loafing", "Six participants choose effort with individual or pooled credit.",
                  "Do people put in less effort when only the group's combined output is recorded?",
                  people(6), [measure("effort", "Mean effort", "hnf.effort_task.effort_mean", step="")],
                  components=[ref("hnf.effort_task.effort", prompt="Your task is to shout as loudly as you can when the "
                                  "signal is given.", credit="individual", rounds=1, finish=True)],
                  conditions=[condition("alone", "Alone (individual credit)"),
                              condition("group", "Group of 6 (pooled credit)", ("/components/0/config/credit", "pooled"))],
                  actions=20)},
    {"id": "group-decision-discussion",
     "name": "Group decision after discussion (choice dilemma)",
     "description": (
         "Original study: Siegel, J., Dubrovsky, V., Kiesler, S., & McGuire, T. W. (1986). Group processes in "
         "computer-mediated communication. Organizational Behavior and Human Decision Processes, 37(2), 157-187. Groups "
         "of three made individual choices on choice-dilemma problems, then discussed each problem face to face or "
         "through a computer and reached a group decision; the studies compared participation, choice shift and "
         "behavior across these media. Group decision tasks appear in 19 of the 500 studies in our survey. This "
         "template keeps the computer-mediated sequence for one group of three: each member answers a choice dilemma "
         "privately, the group discusses it in text over three rounds, and the group then votes until it agrees "
         "(up to three votes). The choice dilemma is new, not one of the original items, and there is no face-to-face "
         "condition. " + SIM),
     "spec": spec("group-decision-discussion", "Group decision after discussion",
                  "Private choice, discussion, then a unanimous group decision on a choice dilemma.",
                  "Does the group's decision differ from its members' private choices?",
                  people(3), [measure("private", "Private choices", "hnf.questionnaire.summary", step="alone"),
                              measure("balance", "Participation balance", "hnf.group_discussion.participation_balance",
                                      action_type="discussion.message", step="discuss")],
                  steps=[{"id": "alone", "title": "Choose alone", "components": [ref(
                             "hnf.questionnaire.questionnaire", prompt=CHOICE_DILEMMA, visibility="private", finish=True,
                             items=[{"id": "odds", "prompt": "Lowest acceptable chance of success", "type": "choice",
                                     "min": 1, "max": 7, "options": ODDS}])]},
                         {"id": "discuss", "title": "Discuss", "components": [ref(
                             "hnf.group_discussion.discussion", turns="free", rounds=3, finish=True,
                             prompt=CHOICE_DILEMMA + " Discuss with your group and try to agree.",
                             sample="I think Sam should only move if the new firm is fairly likely to succeed.")]},
                         {"id": "decide", "title": "Decide as a group", "components": [ref(
                             "hnf.group_decision.decision", prompt=CHOICE_DILEMMA + " Give the group's answer.",
                             options=ODDS, rule="unanimity", leader="", visible=True, max_ballots=3, finish=True)]}],
                  actions=40)},
    {"id": "hidden-profile",
     "name": "Hidden profile: solving a problem versus making a judgment",
     "description": (
         "Original study: Stasser, G., & Stewart, D. (1992). Discovery of hidden profiles by decision-making groups: "
         "Solving a problem versus making a judgment. Journal of Personality and Social Psychology, 63(3), 426-434. "
         "Groups of three read a murder mystery with three suspects. Clues everyone shared pointed to the wrong suspect; "
         "the clues that identified the culprit were split among the members, so the group could only find the answer "
         "by pooling them. Groups were told either that the case had a correct solution (solve) or to make their best "
         "judgment (judge). Hidden-profile tasks appear in 17 of the 500 studies in our survey. This template keeps the "
         "two instructions as two conditions: each member gets the shared clues and two of their own in their private "
         "information, the group discusses over three rounds, then decides by consensus (up to three votes). The case "
         "is new, written for this template, and follows the paradigm; it is not the original booklet. " + SIM),
     "spec": spec("hidden-profile", "Hidden profile: solve vs judge",
                  "Three members with private clues discuss a murder case and decide together.",
                  "Do groups pool their unshared clues more when told the problem has a correct solution?",
                  people(3, private=MYSTERY_PRIVATE),
                  [measure("accuracy", "Correct suspect", "hnf.group_decision.decision_accuracy", answer_key="Dana Whitlow", step="decide"),
                   measure("information", "Unshared clues mentioned", "hnf.group_decision.information_shared",
                           clues=CLUES, action_type="discussion.message", step="discuss"),
                   measure("balance", "Participation balance", "hnf.group_discussion.participation_balance",
                           action_type="discussion.message", step="discuss")],
                  steps=[{"id": "discuss", "title": "Discuss the case", "components": [MYSTERY_TALK]},
                         {"id": "decide", "title": "Decide as a group", "components": [ref(
                             "hnf.group_decision.decision", options=SUSPECTS, rule="unanimity", leader="", visible=True,
                             max_ballots=3, finish=True,
                             prompt="The case has a correct solution: one suspect committed the murder, and the clues, "
                                    "taken together, show who. Agree as a group on the guilty suspect.")]}],
                  conditions=[condition("solve", "Solve: there is a correct answer"),
                              condition("judge", "Judge: make your best judgment", (
                                  "/steps/1/components/0/config/prompt",
                                  "There is not enough information to be certain. As a group, make your best judgment "
                                  "of which suspect is most likely to have committed the murder."))],
                  actions=30)},
    {"id": "murder-mystery",
     "name": "Murder mystery: individual vote, discussion, group decision",
     "description": (
         "After Stasser, G., & Stewart, D. (1992). Discovery of hidden profiles by decision-making groups: Solving a "
         "problem versus making a judgment. Journal of Personality and Social Psychology, 63(3), 426-434. In this "
         "hidden-profile paradigm, groups of three solve a murder mystery with three suspects: the clues everyone "
         "shares point to the wrong suspect, and the clues that reveal the culprit are split among the members. "
         "Hidden-profile tasks appear in 17 of the 500 studies in our survey. Here each member reads the shared clues "
         "and two clues of their own (in their private information) and votes alone and privately, the group discusses "
         "over three rounds, then decides by majority vote. Comparing the private votes with the group decision shows "
         "whether discussion surfaced the unshared clues. The case is new, written for this template, and follows the "
         "paradigm; the original booklets are not used. " + SIM),
     "spec": spec("murder-mystery", "Murder mystery (hidden profile)",
                  "Private clues, a private vote, discussion, then a majority decision on the culprit.",
                  "Do groups find the culprit that no member can identify from their own clues?",
                  people(3, private=MYSTERY_PRIVATE),
                  [measure("accuracy", "Correct suspect", "hnf.group_decision.decision_accuracy", answer_key="Dana Whitlow", step="decide"),
                   measure("information", "Unshared clues mentioned", "hnf.group_decision.information_shared",
                           clues=CLUES, action_type="discussion.message", step="discuss")],
                  steps=[{"id": "alone", "title": "Read your clues and vote alone", "components": [ref(
                             "hnf.group_decision.decision", options=SUSPECTS, rule="individual", leader="", visible=False,
                             max_ballots=1, finish=True,
                             prompt="Read the case and your clues. Who do you think committed the murder?")]},
                         {"id": "discuss", "title": "Discuss the case", "components": [MYSTERY_TALK]},
                         {"id": "decide", "title": "Decide as a group", "components": [ref(
                             "hnf.group_decision.decision", options=SUSPECTS, rule="majority", leader="", visible=True,
                             max_ballots=3, finish=True, prompt="As a group, decide which suspect committed the murder.")]}],
                  actions=30)},
    {"id": "moon-survival",
     "name": "NASA Moon Survival Task",
     "description": (
         "Original study: Hall, J., & Watson, W. H. (1970). The effects of a normative intervention on group "
         "decision-making performance. Human Relations, 23(4), 299-317. Members of five-person groups first ranked 15 "
         "items salvaged from a crash landing on the moon by their importance for survival, then reached a group "
         "ranking by consensus; rankings were scored against the order given by NASA experts, and groups were compared "
         "with their own members. Hall and Watson tested whether brief instructions on how to reach consensus improved "
         "group performance. The task is a classic group-decision exercise used in team research and training; ranking "
         "tasks are rare in our survey of 500 multi-participant experiments. In this template five participants rank "
         "the items alone and privately, discuss over two rounds, and then one member (the reporter) submits the "
         "ranking the group agreed on. There is no normative-intervention condition. Error scores add up how many places "
         "each item is from the expert ranking (lower is better); synergy compares the group with its average and best "
         "member. " + SIM),
     "spec": spec("moon-survival", "NASA Moon Survival Task",
                  "Rank 15 items alone, discuss, then rank as a group; scored against the NASA expert ranking.",
                  "Does the group's ranking beat its average and its best member?",
                  people(5),
                  [measure("individual", "Individual error score", "hnf.ranking_tasks.error_score", answer_key=MOON_KEY, step="alone"),
                   measure("group", "Group error score", "hnf.ranking_tasks.error_score", answer_key=MOON_KEY, step="group"),
                   measure("synergy", "Group synergy", "hnf.ranking_tasks.synergy", individual_step="alone",
                           group_step="group", answer_key=MOON_KEY)],
                  steps=[{"id": "alone", "title": "Rank alone", "components": [ref(
                             "hnf.ranking_tasks.ranking", prompt=MOON_PROMPT, items=MOON_ITEMS, mode="individual",
                             reporter="", visibility="private", finish=True)]},
                         {"id": "discuss", "title": "Discuss", "components": [ref(
                             "hnf.group_discussion.discussion", turns="round_robin", rounds=2, finish=True,
                             prompt=MOON_PROMPT + " Discuss the ranking with your group and try to reach a consensus.",
                             sample="I would put the oxygen and the water first; what do the rest of you think?")]},
                         {"id": "group", "title": "Rank as a group", "components": [ref(
                             "hnf.ranking_tasks.ranking", prompt=MOON_PROMPT, items=MOON_ITEMS, mode="group",
                             reporter="", visibility="shared", finish=True)]}],
                  actions=30)},
]

# AI moderation of survival tasks (Conte, 2026) -----------------------------------------------------------------

# Item names and orders follow Appendix A of the thesis (metric units, as shown to its participants).
CONTE_MOON_KEY = ["Two oxygen tanks (5 kg each)", "20 litres of water", "Star map", "Food concentrate",
                  "Solar-powered FM transceiver", "15 metres of nylon rope", "First-aid kit with injection needles",
                  "Parachute silk", "Self-inflating life raft", "Signal flares", "Two .45-calibre pistols",
                  "One case of powdered milk", "Portable heating unit", "Magnetic compass", "Box of matches"]
CONTE_MOON_PROMPT = ("You are a team of astronauts stranded on the Moon after your lander crashed about 300 km from the "
                     "lunar base, on the lit side of the Moon. These 15 items survived the crash. Rank them by their "
                     "importance for survival and for reaching the base: 1 is the most important.")
SEA_KEY = ["Shaving mirror", "Can of petrol (10 litres)", "Can of water (25 litres)", "Case of army rations",
           "Opaque plastic sheet (2 square metres)", "Chocolate bars (2 packs)", "Sea fishing kit with rod",
           "Nylon rope (5 metres)", "Floating seat cushion", "Shark repellent", "Bottle of 160-proof rum",
           "Transistor radio", "Map of the Atlantic Ocean", "Mosquito netting", "Sextant (without accessories)"]
SEA_PROMPT = ("You chartered a yacht with three friends to cross the Atlantic. In mid-Atlantic a fire broke out; the "
              "skipper and crew were lost fighting it, the yacht is slowly sinking, and the navigation and radio equipment "
              "are destroyed. You are probably many hundreds of miles from land. You saved 15 intact items, along with a "
              "life raft and a box of matches. Rank the items by their importance while you wait to be rescued: 1 is the "
              "most important.")
# Hall & Watson (1970) consensus instructions, as read out in Conte (2026), Appendix A.3.
GROUND_RULES = (
    "1. Avoid arguing for your own ranking: present your position clearly and logically, but seriously consider the "
    "group's reactions. 2. Avoid win-lose stalemates: when you reach an impasse, look for the next most acceptable "
    "alternative for everyone. 3. Do not change your mind only to avoid conflict; resist pressure to yield that has no "
    "sound basis. 4. Avoid conflict-reducing techniques such as majority vote, averaging, bargaining or coin flipping; "
    "treat differences of opinion as a sign that information is still missing, and ask for it. 5. See differences of "
    "opinion as natural and helpful, not as an obstacle. 6. Treat initial agreement as suspect: check that people agree "
    "for the same or complementary reasons.")
# Our addition, not from the thesis: three adults like its sample (both genders, students and not), who take part
# with different readiness to speak, so that the moderator's balancing has something to act on.
CONTE_PERSONAS = [
    ("Giulia", "You are Giulia, a 24-year-old engineering student in Milan. You are confident and talkative: you speak "
               "up first, explain your views at length and like to steer the group."),
    ("Marco", "You are Marco, a 38-year-old office administrator in Milan who did not go to university. You take part "
              "at an ordinary pace: you say what you think briefly and listen to the others."),
    ("Sara", "You are Sara, a 29-year-old shop assistant in Milan. You are reserved: you keep your messages short, "
             "rarely open a new point and tend to go along with the others unless someone asks for your view."),
]
CONTE_ROLEPLAY = ("Take part as this person would, in their own way of speaking and of joining in, not as an assistant. "
                  "Keep their manner throughout the discussion. The discussion is in English. When you are asked "
                  "whether you want to speak next: once your group has agreed on one complete ranking and you have "
                  "nothing to add, answer false; this tells the group you are ready to conclude.")
CONTE_SOURCE = (
    "Original study: Conte, S. P. (2026). AI Moderation in Multi-Party Voice Conversations: Architecture, Strategies, "
    "and Evaluation (Master's thesis, Politecnico di Milano). Ten groups of three ranked 15 items alone, then discussed "
    "by voice for up to 30 minutes under the consensus ground rules of Hall & Watson (1970) and submitted one group "
    "ranking, once with an AI moderator that balanced participation and enforced the ground rules, and once without "
    "it. Each group did NASA Moon Survival in one session and Lost at Sea in the other, with task and moderator order "
    "counterbalanced. Rankings were scored against the expert ranking (error score, lower is better) and against the "
    "group's own members (synergy); participation balance was the Gini index of floor-holding time. ")
CONTE_DESIGN = (
    "In this template three members with personas (a talkative engineering student, an office administrator who "
    "takes part at an ordinary pace and a reserved shop assistant; the personas are ours, not the thesis's) rank the items alone and privately, discuss in text with the ground rules, "
    "speaking when they raise a hand, until nobody asks for the floor (they stop once they agree, like pressing 'ready "
    "to conclude') or 40 member turns, and then the first member submits the group ranking. In the 'Moderator on' "
    "condition an AI moderator follows the thesis's policy: after about 8 minutes of speaking it invites a member under "
    "half the group average by name, or opens up the point of a member over twice the average, with a cooldown; after "
    "each message it judges conflict, direct requests, off-topic drift and ground-rule breaks, with a severity floor "
    "of 0.4; it does not rank. Speaking time is estimated from the members' words at 150 words per minute, and the "
    "2-minute cooldown is our choice, as the thesis does not give its value. In "
    "'Moderator off' it is disabled and the ground rules are only stated at the start. Participation inequality uses "
    "the thesis's Gini formula on the members' words, which stand in for floor-holding time in a text discussion. Run this template and "
    "its sibling together to reproduce the within-group design; every repetition uses the same three personas, so "
    "repetitions differ only through the model's own variation. " + SIM)


def moderated_survival(identifier, name, task, prompt, key, sample, sibling):
    items = sorted(key)
    members = [{"id": f"p{i}", "display_name": who, "enabled": True, "role": "participant",
                "agent": ref("hnf.participants.model", model_ref="default", persona=persona, instructions=CONTE_ROLEPLAY),
                "private_context": {}} for i, (who, persona) in enumerate(CONTE_PERSONAS, 1)]
    moderator = {"id": "moderator", "display_name": "AI moderator", "enabled": True, "role": "moderator",
                 "agent": ref("hnf.moderator.moderator", model_ref="default", balance=True, civility=False,
                              expertise=False, ground_rules=GROUND_RULES, balance_threshold=0.3, persona="",
                              policy="conte", warmup_minutes=8, words_per_minute=150, cooldown_minutes=2,
                              under_ratio=0.5, over_ratio=2.0, min_severity=0.4,
                              instructions=f"The group is doing the {task} task and must agree on one shared ranking."),
                 "private_context": {}}
    measures = [measure("individual", "Individual error score", "hnf.ranking_tasks.error_score", answer_key=key, step="alone"),
                measure("group", "Group error score", "hnf.ranking_tasks.error_score", answer_key=key, step="group"),
                measure("synergy", "Group synergy", "hnf.ranking_tasks.synergy", individual_step="alone",
                        group_step="group", answer_key=key),
                measure("gini", "Participation inequality (Gini)", "hnf.turn_taking.gini",
                        action_type="discussion.message", step="discuss"),
                measure("duration", "Discussion length (estimated speaking minutes)", "hnf.turn_taking.discussion_minutes",
                        action_type="discussion.message", step="discuss", words_per_minute=150)]
    return {"id": identifier, "name": name,
            "description": CONTE_SOURCE + CONTE_DESIGN.replace("its sibling", f"its sibling ({sibling})"),
            "spec": spec(identifier, name,
                         f"{task}: rank alone, discuss under consensus ground rules with or without an AI moderator, "
                         "then rank as a group; scored against the expert ranking.",
                         "Does an AI moderator that balances participation and enforces consensus ground rules change "
                         "the quality of the group's decision and how evenly members take part?",
                         members + [moderator], measures,
                         steps=[{"id": "alone", "title": "Rank alone", "components": [ref(
                                    "hnf.ranking_tasks.ranking", prompt=prompt, items=items, mode="individual",
                                    reporter="", visibility="private", finish=True)]},
                                {"id": "discuss", "title": "Discuss", "components": [
                                    ref("hnf.group_discussion.discussion", turns="procedure", rounds=5, finish=False,
                                        prompt=(prompt + " Discuss the ranking with your group and reach a consensus on "
                                                "one shared ranking. Ground rules: " + GROUND_RULES),
                                        sample=sample),
                                    ref("hnf.turn_taking.raise_hands", action_type="discussion.message", max_turns=40,
                                        finish=True, quiet_rounds=2, tie_break="least_active")]},
                                {"id": "group", "title": "Rank as a group", "components": [ref(
                                    "hnf.ranking_tasks.ranking", prompt=prompt, items=items, mode="group",
                                    reporter="", visibility="shared", finish=True)]}],
                         conditions=[condition("moderator_on", "Moderator on"),
                                     condition("moderator_off", "Moderator off", ("/participants/3/enabled", False))],
                         actions=600)}


TEMPLATES += [
    moderated_survival("moon-survival-ai-moderator", "NASA Moon Survival with an AI moderator", "NASA Moon Survival",
                       CONTE_MOON_PROMPT, CONTE_MOON_KEY,
                       "I would put the oxygen and the water first; why would anyone rank them differently?",
                       "Lost at Sea with an AI moderator"),
    moderated_survival("lost-at-sea-ai-moderator", "Lost at Sea with an AI moderator", "Lost at Sea",
                       SEA_PROMPT, SEA_KEY,
                       "I would put the mirror and the petrol first so we can signal; why would anyone disagree?",
                       "NASA Moon Survival with an AI moderator"),
]

# Recent high-citation studies (2015-2026) -----------------------------------------------------------------------

ROLEPLAY = ("Answer as this person would, from their own views, knowledge and habits, not as an assistant. "
            "Keep the person's views even when they differ from yours.")

# Ten US adults, balanced on party, gender, age and education. Used by the US survey templates.
US_PANEL = [
    "You are a 34-year-old woman from Ohio. You work as a nurse and have some college education. You identify as a Democrat.",
    "You are a 58-year-old man from Texas. You own a small plumbing business and finished high school. You identify as a Republican.",
    "You are a 27-year-old man from California. You test software and have a bachelor's degree. You identify as a Democrat.",
    "You are a 45-year-old woman from Georgia. You are a school administrator with a master's degree. You identify as a Republican.",
    "You are a 63-year-old retired bank clerk from Pennsylvania, a woman who finished high school. You identify as a Democrat.",
    "You are a 39-year-old truck driver from Arizona, a man who finished high school. You identify as a Republican.",
    "You are a 22-year-old woman from New York studying at a state university. You identify as a Democrat.",
    "You are a 51-year-old man from Florida who sells real estate and has a bachelor's degree. You identify as a Republican.",
    "You are a 70-year-old retired autoworker from Michigan, a man who finished high school. You identify as a Democrat.",
    "You are a 31-year-old woman from Missouri who stays at home with her children and has some college education. "
    "You identify as a Republican.",
]

# Ten adults of mixed age, gender, education and income; the country is added per condition.
WORLD_PANEL = [
    "a 24-year-old woman, a university student", "a 37-year-old man who works in a factory",
    "a 52-year-old woman who runs a small shop", "a 68-year-old retired man who worked as a teacher",
    "a 29-year-old man who drives for a delivery company", "a 45-year-old woman who works as an accountant",
    "a 33-year-old woman who works in a hospital kitchen", "a 59-year-old man who farms his own land",
    "a 41-year-old man who manages an office", "a 19-year-old woman who has just finished school",
]


def panel(personas):
    """Model participants with a persona each."""
    return [{"id": f"p{i}", "display_name": f"Participant {i}", "enabled": True, "role": "participant",
             "agent": ref("hnf.participants.model", model_ref="default", persona=persona, instructions=ROLEPLAY),
             "private_context": {}} for i, persona in enumerate(personas, 1)]


def world(country):
    return [f"You are {who} living in {country}. You grew up there and share its everyday culture." for who in WORLD_PANEL]


def country_condition(identifier, country):
    return condition(identifier, country, *((f"/participants/{i}/agent/config/persona", persona)
                                           for i, persona in enumerate(world(country))))


def ask(prompt, items, finish=True):
    return ref("hnf.questionnaire.questionnaire", prompt=prompt, items=items, visibility="private", finish=finish)


def scale(identifier, prompt, low, high):
    return {"id": identifier, "prompt": prompt, "type": "scale", "min": low, "max": high, "options": []}


def choice(identifier, prompt, options):
    return {"id": identifier, "prompt": prompt, "type": "choice", "min": 1, "max": 7, "options": options}


SM = "hnf.survey_measures."


def summary(identifier, label, step):
    return measure(identifier, label, "hnf.questionnaire.summary", step=step)


# Political headlines written for these templates. Item ids say whether the headline is true and which party it favours.
HEADLINES = [
    ("true_dem_1", "Supreme Court rules that same-sex couples have a constitutional right to marry in every state"),
    ("true_dem_2", "Nearly every country in the world adopts the Paris climate agreement to limit global warming"),
    ("true_dem_3", "Share of Americans without health insurance falls to a record low after the Affordable Care Act"),
    ("true_rep_1", "New tax law cuts the US corporate tax rate from 35% to 21%"),
    ("true_rep_2", "United States becomes a net exporter of petroleum for the first time in decades"),
    ("true_rep_3", "Supreme Court overturns Roe v. Wade and returns abortion law to the states"),
    ("false_dem_1", "Leaked memo shows Republican leaders planned to cancel the next presidential election"),
    ("false_dem_2", "Republican lawmakers pass bill making voting by mail a felony"),
    ("false_dem_3", "Oil companies signed a secret pact with Republican leaders to repeal every clean-air law"),
    ("false_rep_1", "House Democrats pass bill banning private ownership of all guns"),
    ("false_rep_2", "Federal investigation finds millions of non-citizens voted in the last presidential election"),
    ("false_rep_3", "Democratic governors agree to replace their police departments with unarmed volunteers"),
]
SEEN_HEADLINES = ("true_dem_1", "true_rep_1", "false_dem_1", "false_rep_1")  # shown in the exposure step
ACCURACY_Q = "To the best of your knowledge, how accurate is this headline? 1 = not at all accurate, 4 = very accurate."

COVID_HEADLINES = [
    ("true_1", "Washing your hands with soap for 20 seconds removes the coronavirus from your skin"),
    ("true_2", "People without symptoms can still spread the coronavirus"),
    ("true_3", "Older adults face the highest risk of severe illness from COVID-19"),
    ("true_4", "Health agencies say vitamin C supplements do not prevent COVID-19"),
    ("true_5", "Face masks reduce the spread of the respiratory droplets that carry the coronavirus"),
    ("false_1", "Drinking hot water every 15 minutes flushes the coronavirus into the stomach, where acid kills it"),
    ("false_2", "5G mobile networks are spreading the coronavirus"),
    ("false_3", "Gargling with salt water every morning prevents COVID-19 infection"),
    ("false_4", "Eating raw garlic protects you from catching the coronavirus"),
    ("false_5", "Hot-air hand dryers kill the coronavirus on your hands"),
]

CRT = [  # Thomson & Oppenheimer (2016) CRT-2 items; options add the intuitive and the correct answer.
    choice("crt_race", "If you're running a race and you pass the person in second place, what place are you in?",
           ["First", "Second", "Third", "Other"]),
    choice("crt_sheep", "A farmer had 15 sheep and all but 8 died. How many are left?", ["7", "8", "15", "Other"]),
    choice("crt_emily", "Emily's father has three daughters. The first two are named April and May. What is the third "
           "daughter's name?", ["June", "Emily", "July", "Other"]),
    choice("crt_hole", "How many cubic feet of dirt are there in a hole that is 3 feet deep, 3 feet wide and 3 feet long?",
           ["27", "0", "9", "Other"]),
]

# Moral Machine dilemmas, one per attribute. The original randomised the side of each group; here the option order
# alternates. Option text names the group that is SPARED.
MM_PROMPT = ("A self-driving car with sudden brake failure will hit one of two groups. It can stay in its lane or swerve. "
             "For each case, choose which group the car should spare. Everyone else in the case dies.")
MM = [
    ("species", "Staying kills 3 people crossing; swerving kills 3 dogs crossing in the other lane.", ["Spare the 3 people", "Spare the 3 dogs"]),
    ("number", "Staying kills 5 pedestrians; swerving kills 1 pedestrian.", ["Spare the 1 pedestrian", "Spare the 5 pedestrians"]),
    ("age", "Staying kills 2 children; swerving kills 2 elderly people.", ["Spare the 2 children", "Spare the 2 elderly people"]),
    ("gender", "Staying kills 2 women; swerving kills 2 men.", ["Spare the 2 men", "Spare the 2 women"]),
    ("status", "Staying kills 2 business executives; swerving kills 2 homeless people.",
     ["Spare the 2 business executives", "Spare the 2 homeless people"]),
    ("fitness", "Staying kills 2 athletes; swerving kills 2 large, unfit people.", ["Spare the 2 large, unfit people", "Spare the 2 athletes"]),
    ("law", "Staying kills 2 people crossing on a green signal; swerving kills 2 people crossing on a red signal.",
     ["Spare those crossing on green", "Spare those crossing on red"]),
    ("intervention", "Staying kills 2 pedestrians ahead; swerving kills 2 other pedestrians in the other lane.",
     ["Stay (spare those in the other lane)", "Swerve (spare those ahead)"]),
    ("passengers", "Staying kills 3 pedestrians; swerving into a barrier kills the 3 passengers in the car.",
     ["Spare the 3 passengers", "Spare the 3 pedestrians"]),
]

GPS_ITEMS = [  # Qualitative items of the Global Preference Survey (Falk et al., 2016 module description).
    scale("risk", "In general, how willing or unwilling are you to take risks? 0 = completely unwilling, 10 = very willing.", 0, 10),
    scale("patience", "How willing are you to give up something that is beneficial for you today in order to benefit more "
          "from that in the future? 0 = completely unwilling, 10 = very willing.", 0, 10),
    scale("pos_reciprocity", "When someone does me a favor I am willing to return it. 0 = does not describe me at all, "
          "10 = describes me perfectly.", 0, 10),
    scale("neg_reciprocity_revenge", "If I am treated very unjustly, I will take revenge at the first occasion, even if there "
          "is a cost to do so. 0 = does not describe me at all, 10 = describes me perfectly.", 0, 10),
    scale("neg_reciprocity_self", "How willing are you to punish someone who treats you unfairly, even if there may be costs "
          "for you? 0 = completely unwilling, 10 = very willing.", 0, 10),
    scale("neg_reciprocity_others", "How willing are you to punish someone who treats others unfairly, even if there may be "
          "costs for you? 0 = completely unwilling, 10 = very willing.", 0, 10),
    scale("altruism", "How willing are you to give to good causes without expecting anything in return? 0 = completely "
          "unwilling, 10 = very willing.", 0, 10),
    scale("donation", "Imagine that today you unexpectedly received an amount equal to about 1,000 euro in your local "
          "currency. How much of it, in euro, would you donate to a good cause? (0 to 1000)", 0, 1000),
    scale("trust", "I assume that people have only the best intentions. 0 = does not describe me at all, 10 = describes me "
          "perfectly.", 0, 10),
]

# Algorithm appreciation: estimate, receive advice, revise (Logg, Minson & Moore, 2019, Experiment 1A style).
PEOPLE_TO_ESTIMATE = [
    ("weight_1", "A man, 5 feet 10 inches tall, broad shoulders, slightly rounded stomach, wearing a medium T-shirt."),
    ("weight_2", "A woman, 5 feet 4 inches tall, slim, runs regularly, wearing size small running clothes."),
    ("weight_3", "A man, 6 feet 2 inches tall, heavily built, works in construction, wearing an XXL jacket."),
]
ADVICE = {"weight_1": 186, "weight_2": 121, "weight_3": 238}
ESTIMATE_PROMPT = "Estimate each person's weight in pounds from the description (80 to 350)."
ADVICE_SOURCE = {"algorithm": "an algorithm that estimates weight from descriptions",
                 "person": "the average estimate of 275 participants in a previous study"}


def advice_prompt(source):
    lines = "; ".join(f"{key}: {value} lb" for key, value in ADVICE.items())
    return (f"You have already given your own estimates. Here are the estimates of {ADVICE_SOURCE[source]}: {lines}. "
            f"Now give your final estimate for each person (80 to 350). You may keep your first estimate or change it.")


# Algorithm aversion: forecasting MBA applicants' success (Dietvorst, Simmons & Massey, 2015, after Study 1).
FORECAST_TASK = ("You will forecast how well MBA applicants do in their program, as a percentile from 1 to 100, from "
                 "their undergraduate degree, GMAT scores, years of work experience and interview rating. A statistical "
                 "model built by analysts makes the same forecasts from the same data. Your bonus depends on how close "
                 "the forecasts are to the real outcomes.")
SEEN = {
    "control": "",
    "model": (" In the first 10 practice cases you saw the model's forecasts next to the real outcomes. The model was "
              "off by 17, 4, 26, 9, 31, 12, 6, 22, 15 and 8 percentile points; in one case it was off by 31 points."),
    "both": (" In the first 10 practice cases you made your own forecasts and saw the model's. The model was off by 17, 4, "
             "26, 9, 31, 12, 6, 22, 15 and 8 percentile points (average 15). You were off by 21, 10, 30, 14, 26, 19, 11, "
             "28, 17 and 14 points (average 19)."),
}
FORECAST_ITEMS = [choice("bonus_source", "For the next 10 cases, whose forecasts should decide your bonus?",
                         ["My own forecasts", "The model's forecasts"]),
                  scale("confidence_model", "How confident are you in the model's forecasts? 1 = none, 5 = a lot.", 1, 5),
                  scale("confidence_self", "How confident are you in your own forecasts? 1 = none, 5 = a lot.", 1, 5)]

# Vaccine misinformation (Loomba et al., 2021): posts written for this template, paraphrasing claims circulating in 2020.
VACCINE_INTENT = choice("intent", "If a new coronavirus vaccine became available, would you accept it for yourself?",
                        ["Yes, definitely", "Unsure, but leaning towards yes", "Unsure, but leaning towards no",
                         "No, definitely not"])
MISINFORMATION_POSTS = (
    "Post 1: 'The new coronavirus vaccines use technology that will permanently change your DNA. Don't be a guinea pig.' "
    "Post 2: 'Over 99% of people survive COVID. Why take a rushed vaccine that skipped safety testing?' "
    "Post 3: 'Doctors are warning that the vaccine could make women infertile. They are not telling you this on TV.' "
    "Post 4: 'Leaked documents show the vaccine contains a tracking chip.' "
    "Post 5: 'A nurse fainted on live TV minutes after getting the vaccine. Share before this is deleted.'")
FACTUAL_POSTS = (
    "Post 1: 'Coronavirus vaccine trials have enrolled tens of thousands of volunteers to test safety and effectiveness.' "
    "Post 2: 'mRNA vaccines teach cells to make a harmless protein; they do not enter the nucleus or change your DNA.' "
    "Post 3: 'Vaccines are reviewed by independent regulators before they are approved for use.' "
    "Post 4: 'Common side effects of vaccines include a sore arm and tiredness for a day or two.' "
    "Post 5: 'Getting vaccinated also helps protect people who cannot be vaccinated, such as some cancer patients.'")
POST_PROMPT = ("It is September 2020. Here are five posts you might see on social media about a coronavirus vaccine. {posts} "
               "Answer the questions about them.")
POST_ITEMS = [scale("trustworthy", "Overall, how trustworthy do these posts seem? 1 = not at all, 5 = very.", 1, 5),
              scale("share", "How likely would you be to share posts like these? 1 = very unlikely, 5 = very likely.", 1, 5)]

AV_PROMPT = ("Imagine a self-driving car with {who} inside, driving at the speed limit. Ten pedestrians suddenly appear in "
             "its path and it cannot stop. The car can stay on course and kill the ten pedestrians, or swerve into a wall, "
             "killing {victims} but saving the ten pedestrians.")
AV_ITEMS = [scale("moral_swerve", "How moral is it for the car to swerve and sacrifice its passengers to save the ten "
                  "pedestrians? 0 = not at all moral, 100 = completely moral.", 0, 100),
            scale("buy_utilitarian", "How likely would you be to buy a car programmed to sacrifice its passengers to save "
                  "more people? 0 = not at all, 100 = extremely likely.", 0, 100),
            scale("buy_self_protective", "How likely would you be to buy a car programmed to protect its passengers at all "
                  "costs? 0 = not at all, 100 = extremely likely.", 0, 100),
            scale("support_regulation", "Should the government require self-driving cars to sacrifice their passengers to "
                  "save more people? 0 = strongly oppose, 100 = strongly support.", 0, 100)]

TEMPLATES += [
    {"id": "moral-machine",
     "name": "Moral Machine: whom should a self-driving car spare?",
     "description": (
         "Original study: Awad, E., Dsouza, S., Kim, R., Schulz, J., Henrich, J., Shariff, A., Bonnefon, J.-F., & "
         "Rahwan, I. (2018). The Moral Machine experiment. Nature, 563(7729), 59-64. An online platform collected about "
         "40 million decisions from millions of people in 233 countries and territories on dilemmas in which a "
         "self-driving car must kill one of two groups. Globally, people preferred to spare humans over animals, more "
         "lives over fewer and the young over the old; countries formed Western, Eastern and Southern clusters that "
         "weighed these preferences differently. This template gives ten participants nine dilemmas, each varying one "
         "attribute (species, number, age, gender, social status, fitness, lawfulness, intervention, passengers versus "
         "pedestrians), and runs three conditions whose participants live in the United States, Japan or Brazil, one "
         "country from each cluster. The original randomised every attribute of each scene and estimated effects with "
         "conjoint analysis; here each dilemma isolates one attribute and the option order alternates. Compare the share "
         "choosing each side per dilemma with the paper's Figure 2 and across conditions with its Figure 3. " + SIM),
     "spec": spec("moral-machine", "Moral Machine", "Ten participants decide nine self-driving-car dilemmas; three countries.",
                  "Which lives do people prefer a self-driving car to spare, and does this differ between cultures?",
                  panel(world("the United States")), [summary("choices", "Choices per dilemma", "")],
                  components=[ask(MM_PROMPT, [choice(key, text, options) for key, text, options in MM])],
                  conditions=[country_condition("united-states", "the United States"),
                              country_condition("japan", "Japan"), country_condition("brazil", "Brazil")],
                  actions=20)},
    {"id": "fake-news-cognitive-reflection",
     "name": "Lazy, not biased: reasoning and belief in fake news",
     "description": (
         "Original study: Pennycook, G., & Rand, D. G. (2019). Lazy, not biased: Susceptibility to partisan fake news is "
         "better explained by lack of reasoning than by motivated reasoning. Cognition, 188, 39-50. In two studies, "
         "3,446 Mechanical Turk workers took the Cognitive Reflection Test (CRT) and rated the accuracy of real and fake "
         "political news headlines favouring Democrats or Republicans. Higher CRT scores went with lower belief in fake "
         "news and better discernment between real and fake, even for headlines that matched the participant's party. "
         "In this template ten US participants (five Democrats, five Republicans) answer four CRT-2 items (Thomson & "
         "Oppenheimer, 2016) and then rate twelve headlines on the original 4-point accuracy scale: three true and "
         "three false favouring each party. The headlines are new, written for this template, and shown as text rather "
         "than as Facebook posts; the CRT items are multiple choice, offering the intuitive and the correct answer. "
         "Item ids mark each headline as true or false and pro-Democrat or pro-Republican. Measures: truth discernment "
         "(mean rating of true minus false headlines) and CRT score (share correct), each also given per participant "
         "so they can be related to each other and to the participant's party. " + SIM),
     "spec": spec("fake-news-cognitive-reflection", "Lazy, not biased",
                  "Ten US participants take the CRT and rate the accuracy of 12 partisan headlines.",
                  "Is belief in fake news explained by lack of reasoning rather than by partisan motivated reasoning?",
                  panel(US_PANEL), [summary("accuracy", "Accuracy ratings", "headlines"),
                   measure("discernment", "Truth discernment", SM + "item_contrast", group_a=["true_"], group_b=["false_"], step="headlines"),
                   measure("crt", "CRT score", SM + "answer_key_accuracy", step="crt", answer_key=[
                       {"item": "crt_race", "answer": "Second"}, {"item": "crt_sheep", "answer": "8"},
                       {"item": "crt_emily", "answer": "Emily"}, {"item": "crt_hole", "answer": "0"}])],
                  steps=[{"id": "crt", "title": "Reasoning questions", "components": [ask("Please answer these questions.", CRT)]},
                         {"id": "headlines", "title": "Rate headlines", "components": [ask(
                             "You will see news headlines. " + ACCURACY_Q,
                             [scale(key, f'"{text}"', 1, 4) for key, text in HEADLINES])]}],
                  actions=40)},
    {"id": "accuracy-nudge-sharing",
     "name": "Accuracy nudge: sharing COVID-19 headlines",
     "description": (
         "Original study: Pennycook, G., McPhetres, J., Zhang, Y., Lu, J. G., & Rand, D. G. (2020). Fighting COVID-19 "
         "misinformation on social media: Experimental evidence for a scalable accuracy-nudge intervention. "
         "Psychological Science, 31(7), 770-780. Across two studies with more than 1,700 US adults, people were worse "
         "at telling true from false COVID-19 headlines when deciding what to share than when judging accuracy; in "
         "Study 2, asking people to judge the accuracy of a single unrelated headline first nearly tripled truth "
         "discernment in their sharing intentions. This template follows Study 2 with ten US participants: in the "
         "treatment condition they first rate the accuracy of one non-COVID headline, in the control condition they "
         "answer a neutral question instead (the original control had no first task), and both then rate how likely "
         "they would be to share each of ten COVID-19 headlines (five true, five false) on a 6-point scale. The "
         "headlines are new, written for this template from claims circulating in March 2020. The sharing discernment "
         "measure is the mean of true minus false items; compare it between the conditions. " + SIM),
     "spec": spec("accuracy-nudge-sharing", "Accuracy nudge",
                  "Ten US participants rate sharing intentions for COVID-19 headlines, after an accuracy prompt or not.",
                  "Does a prompt to think about accuracy improve truth discernment in sharing?",
                  panel(US_PANEL), [summary("sharing", "Sharing intentions", "share"),
                   measure("discernment", "Sharing discernment", SM + "item_contrast", group_a=["true_"], group_b=["false_"], step="share")],
                  steps=[{"id": "first", "title": "First question", "components": [ask(
                             "Before the main task, please answer this question.",
                             [scale("first", "To the best of your knowledge, how accurate is this headline? \"Scientists "
                                    "confirm that the Moon has water ice in craters at its south pole\" 1 = not at all "
                                    "accurate, 4 = very accurate.", 1, 4)])]},
                         {"id": "share", "title": "Sharing", "components": [ask(
                             "It is March 2020. You will see news headlines about the coronavirus. For each, how likely "
                             "would you be to share it online, for example on Facebook or Twitter? 1 = extremely "
                             "unlikely, 6 = extremely likely.",
                             [scale(key, f'"{text}"', 1, 6) for key, text in COVID_HEADLINES])]}],
                  conditions=[condition("accuracy-prompt", "Accuracy prompt first"),
                              condition("control", "Control", ("/steps/0/components/0/config/items/0", scale(
                                  "first", "How many hours a day do you usually spend on social media? 1 = less than "
                                  "one hour, 4 = more than three hours.", 1, 4)))],
                  actions=40)},
    {"id": "illusory-truth-fake-news",
     "name": "Prior exposure and belief in fake news",
     "description": (
         "Original study: Pennycook, G., Cannon, T. D., & Rand, D. G. (2018). Prior exposure increases perceived accuracy "
         "of fake news. Journal of Experimental Psychology: General, 147(12), 1865-1880. Mechanical Turk participants "
         "first saw a set of real and fake headlines and said whether they would share them; after a distractor task "
         "they rated the accuracy of those headlines and new ones. A single prior exposure raised the perceived "
         "accuracy of fake news, even when the fake headlines had carried a 'Disputed by 3rd Party Fact-Checkers' "
         "warning, and even for headlines against the participant's politics. In this template ten US participants "
         "see four headlines (two true, two false) and say whether they would share each, then rate the accuracy "
         "of all twelve headlines (the four seen and eight new). The warning condition labels the false headlines as "
         "disputed during exposure. There is no distractor task, and the headlines are new, written for this template. "
         "The illusory-truth measure is the mean accuracy of the seen false headlines minus the new false ones; "
         "above zero means prior exposure raised belief. " + SIM),
     "spec": spec("illusory-truth-fake-news", "Prior exposure to fake news",
                  "Ten US participants see four headlines, then rate the accuracy of twelve, four of them seen before.",
                  "Does seeing a fake headline once make it seem more accurate later?",
                  panel(US_PANEL), [summary("accuracy", "Accuracy ratings", "rate"),
                   measure("illusory_truth", "Seen minus new false headlines", SM + "item_contrast", step="rate",
                           group_a=["false_dem_1", "false_rep_1"], group_b=["false_dem_2", "false_dem_3", "false_rep_2", "false_rep_3"])],
                  steps=[{"id": "expose", "title": "Headlines", "components": [ask(
                             "Here are some news headlines. For each, would you consider sharing it on social media?",
                             [choice(key, f'"{text}"', ["Yes", "No"]) for key, text in HEADLINES
                              if key in SEEN_HEADLINES])]},
                         {"id": "rate", "title": "Rate headlines", "components": [ask(
                             "You will see news headlines; some you may have seen earlier. " + ACCURACY_Q,
                             [scale(key, f'"{text}"', 1, 4) for key, text in HEADLINES])]}],
                  conditions=[condition("no-warning", "No warning"),
                              condition("warning", "Disputed warning on false headlines", *(
                                  (f"/steps/0/components/0/config/items/{i}/prompt", f'"{text}" [Disputed by 3rd Party Fact-Checkers]')
                                  for i, (key, text) in enumerate(item for item in HEADLINES if item[0] in SEEN_HEADLINES)
                                  if key.startswith("false")))],
                  actions=40)},
    {"id": "algorithm-appreciation",
     "name": "Algorithm appreciation: advice from an algorithm or from people",
     "description": (
         "Original study: Logg, J. M., Minson, J. A., & Moore, D. A. (2019). Algorithm appreciation: People prefer "
         "algorithmic to human judgment. Organizational Behavior and Human Decision Processes, 151, 90-103. In six "
         "experiments, people made an estimate, received advice, and made a final estimate. They moved further toward "
         "the advice when it was said to come from an algorithm than from people; the effect waned when they chose "
         "between the algorithm and their own judgment, and among experienced forecasters. In Experiment 1A people "
         "estimated a person's weight from a photograph. In this template ten US participants estimate the weight of "
         "three people from written descriptions (the photographs are not used), then see advice labelled as coming "
         "from an algorithm or from the average of 275 earlier participants, and give final estimates. The advice is the "
         "same in both conditions. The weight-of-advice measure is (final - first) / (advice - first), limited to 0-1; "
         "compare it between the conditions. The advice values are " + ", ".join(f"{k}: {v} lb" for k, v in ADVICE.items()) + ". " + SIM),
     "spec": spec("algorithm-appreciation", "Algorithm appreciation",
                  "Ten participants estimate, receive advice labelled as algorithmic or human, and revise.",
                  "Do people weigh advice more when it comes from an algorithm than from other people?",
                  panel(US_PANEL), [summary("first", "First estimates", "first"), summary("final", "Final estimates", "final"),
                   measure("woa", "Weight of advice", SM + "weight_of_advice", first_step="first", final_step="final", truncate=True,
                           advice=[{"item": key, "value": value} for key, value in ADVICE.items()])],
                  steps=[{"id": "first", "title": "Your estimate", "components": [ask(
                             ESTIMATE_PROMPT, [scale(key, text, 80, 350) for key, text in PEOPLE_TO_ESTIMATE])]},
                         {"id": "final", "title": "Final estimate", "components": [ask(
                             advice_prompt("algorithm"), [scale(key, text, 80, 350) for key, text in PEOPLE_TO_ESTIMATE])]}],
                  conditions=[condition("algorithm", "Advice from an algorithm"),
                              condition("people", "Advice from people", ("/steps/1/components/0/config/prompt", advice_prompt("person")))],
                  actions=40)},
    {"id": "algorithm-aversion",
     "name": "Algorithm aversion after seeing an algorithm err",
     "description": (
         "Original study: Dietvorst, B. J., Simmons, J. P., & Massey, C. (2015). Algorithm aversion: People erroneously "
         "avoid algorithms after seeing them err. Journal of Experimental Psychology: General, 144(1), 114-126. "
         "Participants forecast MBA students' success from admissions data. Those who had seen a statistical model's "
         "forecasts and errors were less likely to bet their bonus on the model, and more likely to choose their own "
         "forecasts, than those who had not, even when they saw that the model outperformed them. In this template ten "
         "participants read the forecasting task and its incentive, then choose whose forecasts decide their bonus for "
         "the next ten cases and rate their confidence in each. Conditions: no practice information (control); a "
         "summary of the model's errors in ten practice cases (model); or the model's and their own errors, the model "
         "being better (both). The original had participants make the practice forecasts themselves and a fourth "
         "condition (own forecasts only); here the practice feedback is a written summary. Compare the share choosing "
         "the model between conditions. " + SIM),
     "spec": spec("algorithm-aversion", "Algorithm aversion",
                  "After seeing a model's errors or not, ten participants choose the model or themselves for their bonus.",
                  "Do people avoid an algorithm after seeing it make mistakes, even when it beats them?",
                  panel(US_PANEL), [summary("choice", "Choice of forecasts", "")],
                  components=[ask(FORECAST_TASK + SEEN["control"], FORECAST_ITEMS)],
                  conditions=[condition("control", "No practice information"),
                              condition("model", "Saw the model's errors", ("/components/0/config/prompt", FORECAST_TASK + SEEN["model"])),
                              condition("both", "Saw both, the model better", ("/components/0/config/prompt", FORECAST_TASK + SEEN["both"]))],
                  actions=20)},
    {"id": "vaccine-misinformation-intent",
     "name": "COVID-19 vaccine misinformation and vaccination intent",
     "description": (
         "Original study: Loomba, S., de Figueiredo, A., Piatek, S. J., de Graaf, K., & Larson, H. J. (2021). Measuring "
         "the impact of COVID-19 vaccine misinformation on vaccination intent in the UK and USA. Nature Human Behaviour, "
         "5(3), 337-348. In a pre-registered randomized controlled trial with 8,001 respondents in the UK and the US in "
         "September 2020, people stated whether they would accept a COVID-19 vaccine, were shown five recent social "
         "media posts containing vaccine misinformation or five factual posts, and stated their intent again. "
         "Misinformation lowered intent relative to the factual posts. This template runs the US arm with ten US "
         "participants: intent before (the original 4-point item), five posts with questions about trust and sharing, "
         "and intent after. The posts are new, written for this template, paraphrasing claims that circulated in 2020; "
         "the original used real posts with images. The intent-change measure is the share answering 'Yes, definitely' after "
         "minus before; compare it between the conditions. " + SIM),
     "spec": spec("vaccine-misinformation-intent", "Vaccine misinformation and intent",
                  "Ten US participants state vaccination intent before and after seeing misinformation or factual posts.",
                  "Does exposure to vaccine misinformation lower the intent to get vaccinated?",
                  panel(US_PANEL), [summary("before", "Intent before", "before"), summary("posts", "Ratings of posts", "posts"),
                                    summary("after", "Intent after", "after"),
                                    measure("intent_change", "Change in definite acceptance", SM + "step_change", item="intent",
                                            target="Yes, definitely", before_step="before", after_step="after")],
                  steps=[{"id": "before", "title": "Before", "components": [ask("It is September 2020.", [VACCINE_INTENT])]},
                         {"id": "posts", "title": "Posts", "components": [ask(POST_PROMPT.format(posts=MISINFORMATION_POSTS), POST_ITEMS)]},
                         {"id": "after", "title": "After", "components": [ask("Please answer this question again.", [VACCINE_INTENT])]}],
                  conditions=[condition("misinformation", "Misinformation posts"),
                              condition("factual", "Factual posts", ("/steps/1/components/0/config/prompt", POST_PROMPT.format(posts=FACTUAL_POSTS)))],
                  actions=40)},
    {"id": "global-preference-survey",
     "name": "Global Preference Survey: risk, patience, reciprocity, altruism and trust",
     "description": (
         "Original study: Falk, A., Becker, A., Dohmen, T., Enke, B., Huffman, D., & Sunde, U. (2018). Global evidence on "
         "economic preferences. The Quarterly Journal of Economics, 133(4), 1645-1692. The Global Preference Survey "
         "measured risk taking, patience, positive and negative reciprocity, altruism and trust among 80,000 people in "
         "representative samples of 76 countries, with survey items validated against incentivized experiments. "
         "Preferences varied strongly between countries and even more within them, and predicted saving, schooling, "
         "health and prosocial behaviour. This template asks ten participants of mixed age, gender and occupation the "
         "survey's qualitative items, with six conditions placing them in the United States, Germany, Sweden, Japan, "
         "Nigeria or Brazil. The original's quantitative staircase items (lottery and time-delay choices) are left out, "
         "so the composite preference indices cannot be rebuilt exactly; compare item means across countries with the "
         "country-level data published by the authors. " + SIM),
     "spec": spec("global-preference-survey", "Global Preference Survey",
                  "Ten participants answer the GPS qualitative items; six countries as conditions.",
                  "How do economic preferences differ between countries?",
                  panel(world("the United States")), [summary("preferences", "Preference items", "")],
                  components=[ask("Please answer each question about yourself.", GPS_ITEMS)],
                  conditions=[country_condition(slug, name) for slug, name in (
                      ("united-states", "the United States"), ("germany", "Germany"), ("sweden", "Sweden"),
                      ("japan", "Japan"), ("nigeria", "Nigeria"), ("brazil", "Brazil"))],
                  actions=20)},
    {"id": "autonomous-vehicle-dilemma",
     "name": "The social dilemma of autonomous vehicles",
     "description": (
         "Original study: Bonnefon, J.-F., Shariff, A., & Rahwan, I. (2016). The social dilemma of autonomous vehicles. "
         "Science, 352(6293), 1573-1576. In six online studies with US Mechanical Turk participants, most people judged "
         "it moral for a self-driving car to sacrifice its passenger to save ten pedestrians, but were less willing to "
         "buy such a car than a self-protective one, and opposed regulations that would require it, especially when "
         "imagining family members in the car. This template asks ten US participants how moral the sacrifice is, how "
         "likely they would be to buy a utilitarian or a self-protective car, and whether they support regulation, on "
         "the original 0-100 scales, with two conditions: alone in the car, or with a family member. The wording is "
         "written for this template and the six studies' other variations are not included. Compare moral approval "
         "with willingness to buy the utilitarian car, and both conditions. " + SIM),
     "spec": spec("autonomous-vehicle-dilemma", "Social dilemma of autonomous vehicles",
                  "Ten US participants judge, would buy and would regulate self-sacrificing self-driving cars.",
                  "Do people approve of self-sacrificing cars but not want to buy them?",
                  panel(US_PANEL), [summary("ratings", "Ratings", "")],
                  components=[ask(AV_PROMPT.format(who="you alone", victims="you"), AV_ITEMS)],
                  conditions=[condition("alone", "You alone in the car"),
                              condition("family", "You and a family member", ("/components/0/config/prompt",
                                        AV_PROMPT.format(who="you and a family member", victims="you and your family member")))],
                  actions=20)},
]
