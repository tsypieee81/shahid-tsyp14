"""Scenes of the short cut (video/cuts.py): the idea without the curve walkthrough, one results card, the close.
Numbers and sources: video/STORYBOARD.md, "Short cut"."""
import json

from style import *

REPO = ROOT.parent
CASE = dict(M=4.32, R=3.93)   # results/decision_log_demo.jsonl line 2, ledger C9-01
P_CASE = 0.99998              # recomputed from that line with shahid/detect.py score(); shown as "> 0.999"
FZ = json.loads((REPO / "results/studies/classifier_comparison/summary.json").read_text(encoding="utf8"))["frozen"]["urban6"]
COV, FALSE, MISSED = FZ["coverage"]["rate"], FZ["false_outage_rate"]["rate"], FZ["missed_outage_rate"]["rate"]
HOURLY = [("15-min readings", 0.006), ("60-min readings", 0.245)]  # ledger CAD-4


class SIdeaShort(Timed):
    DEFAULT = [11, 13, 10]
    SECTION = "The idea"

    def construct(self):
        self.add(tag())
        self.lower_third()
        # ---- a: the witness ------------------------------------------------------------------------
        tr, lines, meters = network()
        for m in meters[SILENT]:
            silence(m)
        witness = VGroup(Square(0.62, color=COMMS, stroke_width=3), T("kWh", 16, COMMS))
        witness[1].move_to(witness[0])
        witness.next_to(tr, DOWN, buff=0.35)
        halo = Circle(0.5, color=COMMS, stroke_width=2).move_to(witness)
        cap = self.caption("the transformer meter: the witness")
        dots = VGroup(*[Dot(radius=0.04, color=TEXT).set_opacity(0.7) for _ in range(60)])
        for j, d in enumerate(dots):
            d.f, d.a = lines[2][j % 5], (j * 0.137) % 1

        def flow(grp, dt):
            for d in grp:
                d.a = (d.a + dt * 0.35) % 1
                d.move_to(d.f.point_from_proportion(d.a))
        dots.add_updater(flow)
        self.add(tr, lines, meters, dots)
        self.play(FadeIn(cap, shift=DOWN * 0.2), run_time=0.8)
        self.play(GrowFromCenter(witness), run_time=1.0, rate_func=ease_out_cubic)
        self.play(Create(halo), halo.animate.scale(1.6).set_opacity(0), run_time=1.4)
        self.hold()
        # ---- b: M against R, and the two worlds -------------------------------------------------------
        k = 0.62
        mT, rT = ValueTracker(0), ValueTracker(0)
        mbar = always_redraw(lambda: DashedVMobject(Rectangle(width=0.9, height=max(mT.get_value() * k, 0.01),
                             stroke_color=MUTED, stroke_width=3), num_dashes=40)
                             .move_to([3.2, -2.6 + mT.get_value() * k / 2, 0]))
        rbar = always_redraw(lambda: Rectangle(width=0.9, height=max(rT.get_value() * k, 0.01), stroke_width=0,
                             fill_color=COMMS, fill_opacity=0.85).move_to([5.4, -2.6 + rT.get_value() * k / 2, 0]))
        floor = Line([2.5, -2.6, 0], [6.1, -2.6, 0], color=LINE, stroke_width=2)
        mnum = always_redraw(lambda: T(f"{mT.get_value():.2f}", 30).next_to(mbar, UP, buff=0.15))
        rnum = always_redraw(lambda: T(f"{rT.get_value():.2f}", 30).next_to(rbar, UP, buff=0.15))
        ml = VGroup(T("M", 30, MUTED, SEMIBOLD), T("expected", 18, FAINT)).arrange(DOWN, buff=0.08).next_to([3.2, -2.6, 0], DOWN, 0.15)
        rl = VGroup(T("R", 30, COMMS, SEMIBOLD), T("witness sees", 18, FAINT)).arrange(DOWN, buff=0.08).next_to([5.4, -2.6, 0], DOWN, 0.15)
        unit = T("kWh, 2 readings", 18, FAINT).next_to(floor, UP, buff=3.3).align_to(floor, RIGHT)
        worlds = VGroup(T("power cut:  R ≈ 0", 26, OUTAGE), T("only data lost:  R ≈ M", 26, COMMS)
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25).move_to([4.3, 1.75, 0])
        self.play(Create(floor), FadeIn(ml), FadeIn(rl), FadeIn(unit), run_time=0.8)
        self.add(mbar, rbar, mnum, rnum)
        self.play(mT.animate.set_value(CASE["M"]), run_time=1.4, rate_func=ease_out_cubic)
        self.play(rT.animate.set_value(CASE["R"]), run_time=1.4, rate_func=ease_out_cubic)
        self.play(FadeIn(worlds, shift=DOWN * 0.2), run_time=0.8)
        self.hold()
        # ---- c: the probability and the band ----------------------------------------------------------
        dots.clear_updaters()
        for b in (mbar, rbar, mnum, rnum):
            b.clear_updaters()
        pt = ValueTracker(0.5)
        pval = always_redraw(lambda: T(pshow(pt.get_value()), 72, COMMS, SEMIBOLD).move_to([0, 1.0, 0]))
        plab = T("probability: only data lost", 24, MUTED).move_to([0, 2.3, 0])
        S = Scale(pt)
        self.play(FadeOut(VGroup(tr, lines, meters, witness, dots, cap, mbar, rbar, mnum, rnum, ml, rl, floor,
                                 unit, worlds)), run_time=0.8)
        self.add(pval)
        self.play(FadeIn(plab), Create(S.sc), FadeIn(S.band), FadeIn(S.ends), FadeIn(S.needle), run_time=1.0)
        self.play(pt.animate.set_value(P_CASE), run_time=1.6, rate_func=ease_out_cubic)
        self.play(FadeIn(S.bl, shift=UP * 0.2), run_time=0.8)
        self.hold()


class SResultsShort(Timed):
    DEFAULT = [13, 12]
    SECTION = "Results"

    def construct(self):
        self.add(tag())
        self.lower_third()
        cap = self.caption("held-out urban network · method frozen · evaluated once")
        stats_ = VGroup(*[VGroup(T(f"{v:.3f}", 72, TEXT, SEMIBOLD), T(l, 24, MUTED)).arrange(DOWN, buff=0.2)
                          for v, l in [(COV, "coverage: share decided"), (FALSE, "false-outage rate"),
                                       (MISSED, "missed-outage rate")]]).arrange(RIGHT, buff=1.3).move_to(UP * 1.2)
        w = 10.0
        dec = Rectangle(width=w * COV, height=0.45, stroke_width=0, fill_color=MUTED, fill_opacity=0.6)
        per = Rectangle(width=w * (1 - COV), height=0.45, stroke_width=0, fill_color=UNCERTAIN, fill_opacity=0.6)
        bar = VGroup(dec, per).arrange(RIGHT, buff=0).move_to(DOWN * 0.6)
        bl = VGroup(T(f"decided {100 * COV:.1f}%", 22, TEXT).next_to(dec, DOWN, buff=0.15),
                    T(f"to a person {100 * (1 - COV):.1f}%", 22, UNCERTAIN).next_to(per, DOWN, buff=0.15))
        self.play(FadeIn(cap, shift=DOWN * 0.2), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.3) for s in stats_], lag_ratio=0.3), run_time=1.8)
        self.play(GrowFromEdge(dec, LEFT), run_time=0.9)
        self.play(GrowFromEdge(per, LEFT), FadeIn(bl), run_time=0.7)
        self.hold()
        # one honest limit: hourly readings
        lim = VGroup(T("limit", 22, MUTED),
                     *[VGroup(T(lab, 22, MUTED), T(f"missed {v:.3f}", 22, OUTAGE if v > 0.05 else TEXT)).arrange(RIGHT, buff=0.3)
                       for lab, v in HOURLY]).arrange(RIGHT, buff=0.9).move_to(DOWN * 2.15)
        foot = T("SIMULATED on German benchmark networks · no Tunisian data tested yet", 20, UNCERTAIN).move_to(DOWN * 2.95)
        self.play(FadeIn(lim, shift=UP * 0.2), run_time=0.8)
        self.play(Indicate(lim[2], color=OUTAGE, scale_factor=1.06), FadeIn(foot), run_time=1.0)
        self.hold()


class SCloseShort(Timed):
    DEFAULT = [11]
    SECTION = ""

    def construct(self):
        tr = VGroup(Circle(0.3, color=TEXT, stroke_width=3), Circle(0.3, color=TEXT, stroke_width=3).shift(RIGHT * 0.3))
        meter = VGroup(Square(0.45, color=COMMS, stroke_width=3), T("kWh", 14, COMMS)).arrange(ORIGIN)
        need = VGroup(VGroup(tr, meter).arrange(RIGHT, buff=0.35),
                      T("needed in the field: an energy meter at each transformer", 26, TEXT)).arrange(RIGHT, buff=0.5)
        need.move_to(UP * 2.0)
        title = VGroup(T("SHAHID", 80, TEXT, BOLD), T("the witness layer", 36, MUTED)).arrange(DOWN, buff=0.3).move_to(DOWN * 0.3)
        sub = T("SIMULATED Phase 1 prototype · every number traced to the claims ledger", 20, FAINT).move_to(DOWN * 2.2)
        self.play(FadeIn(need, shift=DOWN * 0.2), run_time=0.9)
        self.play(FadeIn(title, scale=0.95), FadeIn(sub), run_time=1.0)
        self.hold()
