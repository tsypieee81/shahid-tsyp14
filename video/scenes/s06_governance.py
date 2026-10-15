"""Scene 6, the honest twist, then governance and trust.
Twist: results/decision_log_demo.jsonl line 1 (8 meters, M 2.31, R 1.27, spreads 0.13 / 0.74, p 0.996); the true
cause was an outage and a delayed heavy reading inflated R: ledger C9-01, docs/LIMITATIONS.md item 12.
Rules: configs/escalation.yaml. Trust devices: ui/panels/trust.py, docs/BRIEF_COVERAGE.md Goal 3."""
from style import *

TWIST = dict(M=2.31, R=1.27, sO=0.13, sC=0.74)
P_TWIST = 0.996  # as logged

RULES = [("R1", "outage, 20 meters or more: alert at once", False),
         ("R2", "outage, p ≥ 0.95: alert with the evidence", False),
         ("R3", "data lost, p ≥ 0.95, ≤ 40 meters: ticket", True),
         ("R4", "other data-loss verdicts: ticket, reviewed", False),
         ("R5", "uncertain: review with the evidence", False)]


def person(color=MUTED):
    return VGroup(Circle(0.08, color=color, stroke_width=2.5),
                  Arc(radius=0.15, start_angle=0, angle=PI, color=color, stroke_width=2.5).shift(DOWN * 0.22))


class S06Governance(Timed):
    DEFAULT = [10, 12, 12]
    SECTION = "Governance and trust"

    def construct(self):
        self.add(tag())
        # ---- a: confident and wrong -------------------------------------------------------------------
        H = Hypotheses(TWIST)
        cap = self.caption("another simulated case · 8 meters", TEXT)
        fr = fraction()
        pv = T(pshow(P_TWIST), 44, COMMS, SEMIBOLD).next_to(fr, DOWN, buff=0.35)
        plab = T("probability: data lost", 18, FAINT).next_to(fr, UP, buff=0.3)
        self.play(FadeIn(cap), FadeIn(H.ax), FadeIn(H.xl), Create(H.out), Create(H.com), run_time=1.2)
        self.play(Create(H.rx), FadeIn(H.rlab), GrowFromCenter(H.do), GrowFromCenter(H.dc),
                  FadeIn(fr), FadeIn(plab), FadeIn(pv), run_time=1.0)
        stamp = VGroup(T("TRUE CAUSE: OUTAGE", 26, OUTAGE, BOLD))
        stamp.add(SurroundingRectangle(stamp[0], color=OUTAGE, buff=0.18, stroke_width=4))
        stamp.rotate(-0.08).move_to([4.7, -0.7, 0])
        self.play(FadeIn(stamp, scale=1.4), run_time=0.6, rate_func=ease_out_cubic)
        why = T("a delayed, heavy reading inflated R", 22, UNCERTAIN)
        why.next_to(H.ax.c2p(1.27, 2.85), RIGHT, buff=0.5).shift(DOWN * 0.6)
        arr = Arrow(why.get_left(), H.ax.c2p(1.32, 1.7), color=UNCERTAIN, stroke_width=3, buff=0.1)
        self.play(FadeIn(why), GrowArrow(arr), run_time=0.8)
        self.hold()
        # ---- b: the escalation table -------------------------------------------------------------------
        self.play(FadeOut(VGroup(H.ax, H.xl, H.out, H.com, H.rx, H.rlab, H.do, H.dc, fr, pv, plab, stamp, why, arr, cap)),
                  run_time=0.6)
        lt = self.lower_third()
        rows = VGroup()
        for rid, txt, auto in RULES:
            box = RoundedRectangle(corner_radius=0.1, width=9.0, height=0.7, stroke_color=COMMS if auto else BORDER,
                                   stroke_width=2, fill_color=CARD, fill_opacity=1)
            who = (chip("automatic, provisional", COMMS, 16) if auto else
                   VGroup(person(), T("person", 18, MUTED)).arrange(RIGHT, buff=0.12))
            row = VGroup(box, T(rid, 22, TEXT, SEMIBOLD).move_to(box).align_to(box, LEFT).shift(RIGHT * 0.25),
                         T(txt, 20, TEXT).move_to(box).align_to(box, LEFT).shift(RIGHT * 0.85),
                         who.move_to(box).align_to(box, RIGHT).shift(LEFT * 0.2))
            rows.add(row)
        rows.arrange(DOWN, buff=0.18).move_to([-1.9, 0.1, 0])
        hdr = self.caption("escalation table · first matching rule wins")
        lock = VGroup(RoundedRectangle(corner_radius=0.08, width=0.6, height=0.5, color=TEXT, stroke_width=3),
                      Arc(radius=0.2, start_angle=0, angle=PI, color=TEXT, stroke_width=3).shift(UP * 0.25))
        crew = VGroup(lock, VGroup(T("crew or customers:", 24, TEXT), T("always a person", 24, TEXT, SEMIBOLD))
                      .arrange(DOWN, buff=0.1)).arrange(DOWN, buff=0.3).move_to([4.8, 0.1, 0])
        self.play(FadeIn(hdr), LaggedStart(*[FadeIn(r, shift=LEFT * 0.3) for r in rows], lag_ratio=0.15), run_time=2.0)
        self.play(Indicate(rows[2], color=COMMS, scale_factor=1.03), run_time=1.0)
        self.play(FadeIn(crew, shift=UP * 0.2), run_time=0.8)
        self.hold()
        # ---- c: trust devices ---------------------------------------------------------------------------
        over = VGroup(T("Against over-trust", 26, TEXT, SEMIBOLD),
                      *[T("· " + s, 22, MUTED) for s in ("alternative cause on every verdict",
                                                         "audit sample of automatic closures",
                                                         "very fast approvals flagged")]).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        under = VGroup(T("Against under-trust", 26, TEXT, SEMIBOLD),
                       T("· track record per verdict class", 22, MUTED)).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        trust = VGroup(over, under).arrange(DOWN, aligned_edge=LEFT, buff=0.6).move_to([0, 0.3, 0])
        foot = T("effect not yet measured with operators", 18, FAINT).next_to(trust, DOWN, buff=0.5).align_to(trust, LEFT)
        self.play(FadeOut(VGroup(crew, rows, hdr)), run_time=0.7)
        self.play(LaggedStart(*[FadeIn(m, shift=RIGHT * 0.2) for m in [*over, *under]], lag_ratio=0.2), run_time=2.0)
        self.play(FadeIn(foot), run_time=0.6)
        self.hold()
