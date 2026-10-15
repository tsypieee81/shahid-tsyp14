"""Cuts of the demo video. `summary` is the full version (narration.py); `short` is the pitching cut
(at most 3:00). Each cut: narration per scene and beat, the module of each Manim scene, the console script
(one step per console beat), voice speed and the output name. Sources: video/STORYBOARD.md, "Short cut"."""
import narration

SHORT = {
    "S01Hook": [
        "Every fifteen minutes, smart meters report what their customers used.",
        "At six in the evening, thirty-four of them go silent at once. Did those customers lose power, "
        "or only their data?",
    ],
    "SIdeaShort": [
        "SHAHID asks the transformer. A meter on its low-voltage side still counts the energy of customers "
        "whose data stopped, but not of customers who lost power. That meter is our witness.",
        "From their own history, the silent customers should use M: 4.32 kilowatt-hours over two readings. "
        "The witness still sees R: 3.93. If the power had been cut, R would be close to zero. Here it is close to M.",
        "So the probability of a communication failure is above 0.999: decided, and no crew is sent. "
        "Between 0.03 and 0.97 the system does not decide: a person does.",
    ],
    "S04Console": [
        "This is the operator console, replaying a simulated day. It is a preview: no operator has used it "
        "yet, and every verdict here comes from stored simulations.",
        "A data concentrator fails. The evidence card shows what the witness still sees, the probability "
        "against its band, and a plain-language explanation written from the same record. On its own, the "
        "system may only open a data ticket, and rule R3 marks even that as provisional.",
        "A feeder loses power: thirty-seven meters go dark at once. The outage verdict waits in its own queue: no crew moves until a person "
        "reads the evidence and approves it.",
        "At midday, seven meters go quiet and the evidence is too thin. Its probability, 0.145, sits inside "
        "the band. The system abstains, and the case goes "
        "to a supervisor with its evidence, instead of a guess.",
        "Every action enters a hash-chained log. That approval came in under five seconds, so the console "
        "flags it for review: a check against over-trust.",
        "Change one character in a copy of the log, and verification fails at that entry: the record cannot "
        "be quietly edited.",
    ],
    "SResultsShort": [
        "On a held-out urban network, evaluated once with the method frozen, it decided 72 percent of events, "
        "with no false outages and under one percent of outages missed. The rest went to a person.",
        "One honest limit: with hourly readings instead of quarter-hourly ones, about a quarter of outages are "
        "missed, so it needs quarter-hour readings. Everything here is simulated, on German benchmark networks.",
    ],
    "SCloseShort": [
        "In the field, SHAHID also needs an energy meter at each transformer. Every number in this video "
        "traces to our claims ledger. SHAHID: the witness layer.",
    ],
}

SAY = {**narration.SAY, "0.03": "zero point zero three", "0.97": "zero point nine seven",
       "0.145": "zero point one four five"}

EXPLAINER = {
    "S01Hook": [
        "Every fifteen minutes, smart meters report what their customers used.",
        "At six in the evening, thirty-four go silent at once. Lost power, or only lost data?",
    ],
    "S03Idea": [
        "SHAHID asks the transformer. A meter on its low-voltage side keeps counting: that meter is the witness.",
        "From their own history, the silent customers should use M: 4.32 kilowatt-hours over two readings. "
        "The witness still sees R: 3.93.",
        "If the power had been cut, R would be close to zero. If only the data was lost, R would be close to M.",
        "Each cause predicts a curve. At 3.93, an outage is almost impossible; lost data is what we would expect.",
        "So the probability of a communication failure is above 0.999. Between 0.03 and 0.97 the system "
        "abstains, and a person decides.",
    ],
    "SResultsShort": [
        "On a held-out urban network, evaluated once, it decided 72 percent of events, with no false outages "
        "and under one percent of outages missed.",
        "The rest went to a person. Everything here is simulated, on German benchmark networks.",
    ],
    "SCloseShort": [
        "SHAHID needs an energy meter at each transformer. Every number traces to the claims ledger. "
        "SHAHID: the witness layer.",
    ],
}

CUTS = {
    "summary": {"narration": narration.SCENES, "say": narration.SAY, "speed": 1.0, "name": "shahid_demo",
                "files": {"S01Hook": "s01_hook", "S02Context": "s02_context", "S03Idea": "s03_idea",
                          "S05Results": "s05_results", "S06Governance": "s06_governance",
                          "S07Impact": "s07_impact", "S08Work": "s08_work"},
                "console": ["replay", "comms", "outage", "uncertain", "audit_and_tamper"]},
    "short": {"narration": SHORT, "say": SAY, "speed": 1.08, "name": "shahid_demo_short",
              "files": {"S01Hook": "s01_hook", "SIdeaShort": "short", "SResultsShort": "short",
                        "SCloseShort": "short"},
              "console": ["replay", "comms", "outage", "uncertain", "audit", "tamper"]},    "explainer": {"narration": EXPLAINER, "say": SAY, "speed": 1.08, "name": "shahid_explainer",
                  "files": {"S01Hook": "s01_hook", "S03Idea": "s03_idea", "SResultsShort": "short",
                            "SCloseShort": "short"},
                  "console": [], "media": True},
}
