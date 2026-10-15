"""Scene 3, the centrepiece: the witness, two hypotheses, the probability and the abstention band.

Numbers: results/decision_log_demo.jsonl line 2 (34-meter case, decided correctly, ledger C9-01);
p recomputed from the logged evidence with shahid/detect.py score(): 0.99998, shown as "> 0.999".
"""
from style import *

CASE = dict(M=4.32, R=3.93, sO=0.16, sC=0.68)  # log line 2
P_CASE = 0.99998                              # recomputed from CASE; the log rounds it to 1.0


class S03Idea(Timed):
    DEFAULT = [11, 13, 8, 15, 17]
    SECTION = "The idea"

    def construct(self):
        self.add(tag())
        self.lower_third()
        # ---- 3a: the witness ------------------------------------------------------------------------
        tr, lines, meters = network()
        for m in meters[SILENT]:
            silence(m)
        self.add(tr, lines, meters)
        cap = self.caption("the transformer meter: the witness")
        witness = VGroup(Square(0.62, color=COMMS, stroke_width=3), T("kWh", 16, COMMS))
        witness[1].move_to(witness[0])
        witness.next_to(tr, DOWN, buff=0.35)
        halo = Circle(0.5, color=COMMS, stroke_width=2).move_to(witness)
        # energy keeps flowing down every feeder, silent ones included: the power may still be there
        dots = VGroup(*[Dot(radius=0.04, color=TEXT).set_opacity(0.7) for _ in range(60)])
        for j, d in enumerate(dots):
            d.f, d.a = lines[2][j % 5], (j * 0.137) % 1

        def flow(grp, dt):
            for d in grp:
                d.a = (d.a + dt * 0.35) % 1
                d.move_to(d.f.point_from_proportion(d.a))
        dots.add_updater(flow)
        self.add(dots)
        self.play(FadeIn(cap, shift=DOWN * 0.2), run_time=0.8)
        self.play(GrowFromCenter(witness), run_time=1.0, rate_func=ease_out_cubic)
        self.play(Create(halo), halo.animate.scale(1.6).set_opacity(0), run_time=1.4)
        self.hold()

        # ---- 3b: M and R ------------------------------------------------------------------------------
        k = 0.62  # units per kWh
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
        self.play(Create(floor), FadeIn(ml), FadeIn(rl), FadeIn(unit), run_time=0.8)
        self.add(mbar, rbar, mnum, rnum)
        self.play(mT.animate.set_value(CASE["M"]), run_time=1.8, rate_func=ease_out_cubic)
        self.wait(1.5)
        self.play(rT.animate.set_value(CASE["R"]), run_time=1.8, rate_func=ease_out_cubic)
        self.hold()

        # ---- 3c: two worlds ---------------------------------------------------------------------------
        dots.clear_updaters()
        cut = T("If power was cut:  R ≈ 0", 30, OUTAGE).move_to([-3.4, 2.2, 0])
        lost = T("If only data was lost:  R ≈ M", 30, COMMS).move_to([-3.4, 1.2, 0])
        self.play(FadeOut(VGroup(tr, lines, meters, witness, dots, cap)), run_time=0.8)
        self.play(FadeIn(cut, shift=RIGHT * 0.3), rT.animate.set_value(0.03), run_time=1.4)
        self.wait(0.8)
        self.play(FadeIn(lost, shift=RIGHT * 0.3), rT.animate.set_value(CASE["M"]), run_time=1.4)
        self.hold()

        # ---- 3d: the curves ---------------------------------------------------------------------------
        for b in (mbar, rbar, mnum, rnum):
            b.clear_updaters()
        H = Hypotheses(CASE)
        hdr = self.caption("spread if outage 0.16 · if data lost 0.68")
        self.play(FadeOut(cut, lost), ReplacementTransform(VGroup(mbar, rbar, mnum, rnum, ml, rl, floor, unit),
                                                           VGroup(H.ax, H.xl)), run_time=1.2)
        self.play(Create(H.out), run_time=1.4)
        self.play(Create(H.com), FadeIn(hdr), run_time=1.4)
        self.play(Create(H.rx), FadeIn(H.rlab, shift=DOWN * 0.2), run_time=1.0)
        self.play(GrowFromCenter(H.do), GrowFromCenter(H.dc), run_time=0.8)
        self.play(Flash(H.dc, color=COMMS, flash_radius=0.3), run_time=0.8)
        self.hold()

        # ---- 3e: probability and band -----------------------------------------------------------------
        fr = fraction()
        pt = ValueTracker(0.5)
        pval = always_redraw(lambda: T(pshow(pt.get_value()), 44, COMMS, SEMIBOLD).next_to(fr, DOWN, buff=0.35))
        plab = T("probability: data lost", 18, FAINT).next_to(fr, UP, buff=0.3)
        self.play(TransformFromCopy(VGroup(H.dc, H.dc.copy(), H.do), VGroup(fr[1][0], fr[1][2][0], fr[1][2][2])),
                  FadeIn(fr[0]), FadeIn(fr[1][1]), FadeIn(fr[1][2][1]), FadeIn(plab), run_time=1.4)
        self.add(pval)
        self.play(pt.animate.set_value(P_CASE), run_time=1.2)
        S = Scale(pt)
        self.play(Create(S.sc), FadeIn(S.band), run_time=1.0)
        self.play(FadeIn(S.bl, shift=UP * 0.2), FadeIn(S.ends), FadeIn(S.needle), run_time=0.8)
        self.play(Indicate(S.needle, color=COMMS), run_time=0.8)
        self.hold()
