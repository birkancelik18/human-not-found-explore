"""The study templates. scripts/build.py publishes each spec in a temporary workspace and exports it as a template."""

V = "1.0.0"
SIM = ("Participants are simulated: each is a Model participant, using the free test model until you choose a "
       "model, so the first runs only check the design; with the test model every participant takes the sample answer.")


def ref(component, **config):
    return {"id": component, "version": V, "config": config}


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
