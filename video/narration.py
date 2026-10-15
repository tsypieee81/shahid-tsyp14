"""Narration, one entry per beat. Single source for the voice, the scene timings and the subtitles.
Numbers are written as on screen; SAY gives how the voice reads them. Sources: video/STORYBOARD.md.
"""
SCENES = {
    "S01Hook": [
        "Every fifteen minutes, smart meters report what their customers used.",
        "At six in the evening, thirty-four of them go silent at once. "
        "Did those customers lose power, or did only their data stop?",
    ],
    "S02Context": [
        "Tunisia's utility, STEG, is rolling out smart meters: about 80,000 low-voltage meters in pilot "
        "zones by the end of March 2026, in a first phase of 450,000.",
        "That summer, during a heatwave, its network went through rotating power cuts.",
        "So when a group of meters goes quiet, someone must choose quickly between two causes with "
        "opposite answers. An outage needs a crew. A communication failure needs no crew at all.",
    ],
    "S03Idea": [
        "Here is the idea. All the energy these customers use passes through one transformer, and a "
        "meter on its low-voltage side keeps counting. That meter is our witness.",
        "From the silent customers' own history, we expect them to use M: here, 4.32 kilowatt-hours "
        "over two readings. The witness still sees R, energy that no reporting meter accounts for: 3.93.",
        "If the power had been cut, R would be close to zero. If only the data stopped, R would be close to M.",
        "Each cause predicts a curve, with a spread learned from the transformer's fault-free days. "
        "At 3.93, an outage is almost impossible; a communication failure is just what we would expect.",
        "Comparing the two heights gives a probability: communication failure, above 0.999. "
        "And the system decides only when the probability falls outside a narrow band at either end. "
        "Anything in between goes to a person.",
    ],
    "S04Console": [
        "This is the operator console, replaying a simulated day. It is a preview: no operator has used it yet.",
        "A data concentrator fails. The evidence card shows what the witness still sees, the probability "
        "against its band, and a plain-language explanation written from the same record. "
        "The system opens a data ticket on its own, and nothing more.",
        "When a feeder loses power, the verdict never sends a crew by itself. "
        "It waits in its own queue until a person approves.",
        "When the evidence is too thin, as here at midday, the system abstains and hands the case over, "
        "with the evidence.",
        "Every action enters a hash-chained log. Change one character in a copy, "
        "and verification fails at that entry.",
    ],
    "S05Results": [
        "On a held-out urban network, evaluated once with the method frozen, it decided 72 percent of "
        "events. Among them: no false outages, and under one percent of outages missed. "
        "The rest went to a person.",
        "Simple rules decide everything, but get many wrong. Trained classifiers, under the same safety "
        "limits, decided less or erred more.",
        "It fails where the physics says it should: with hourly readings, or with unmetered energy that "
        "follows the load, about a quarter of outages are missed. All of this is simulated, on German "
        "benchmark networks. No Tunisian data has been tested yet.",
    ],
    "S06Governance": [
        "But confidence is not truth. Another case scored 0.996 for data lost; "
        "it was an outage, and one delayed reading had inflated R.",
        "That is why the rules are written down, as an escalation table. The system may act alone in one "
        "way only: flag missing data and open a ticket. Dispatching a crew or contacting customers always "
        "needs a person.",
        "Against over-trust, every verdict shows its alternative cause, automatic closures are sampled for "
        "audit, and very fast approvals are flagged. Against under-trust, each verdict class shows its "
        "track record.",
    ],
    "S07Impact": [
        "For a district the size of STEG's Douz agency, with 149 substations, computing is cheap: "
        "a year of one transformer is scored in about thirteen seconds.",
        "The real cost is people. At minimum wage, reviewing the cases costs at least 120,000 dinars a "
        "year; a gate not yet wired in would cut that to about 51,000.",
        "And it all needs an energy meter at each transformer.",
    ],
    "S08Work": [
        "Every protocol was committed before its run. Every number traces to a claims ledger, "
        "and every check passes.",
        "SHAHID: the witness layer.",
    ],
}

# how the voice reads what the subtitles show
SAY = {"80,000": "eighty thousand", "450,000": "four hundred and fifty thousand", "2026": "twenty twenty-six",
       "4.32": "four point three two", "3.93": "three point nine three", "0.999": "zero point nine nine nine",
       "0.996": "zero point nine nine six", "149": "a hundred and forty-nine", "120,000": "a hundred and twenty thousand",
       "51,000": "fifty-one thousand", "72 percent": "seventy-two percent",
       "Douz": "[Douz](/dˈuz/)"}
