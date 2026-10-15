"""Scene 1, hook: a network reports, then 34 meters go silent at 18:00.
Numbers: results/decision_log_demo.jsonl line 2 (34 meters, onset 18:00), ledger C9-01. The network is an
illustration, not the simulated grid."""
from style import *


class S01Hook(Timed):
    DEFAULT = [5, 10]

    def construct(self):
        tr, lines, meters = network()
        note = T("illustration", 18, FAINT).to_corner(DR, buff=MARGIN)
        self.add(tag())
        # ---- a: the network grows and reports (5.4 s; compressed only when the beat is shorter) ---------
        f = 1.0 if self.beats[0] >= 5.4 else (self.beats[0] - 0.15) / 5.4
        self.play(Create(tr), run_time=0.8 * f)
        self.play(LaggedStart(*[Create(l) for l in lines], lag_ratio=0.15), FadeIn(note), run_time=1.4 * f)
        self.play(LaggedStart(*[GrowFromCenter(m) for m in meters], lag_ratio=0.03), run_time=1.6 * f)
        self.play(LaggedStart(*[Indicate(m, scale_factor=1.6, color=TEXT) for m in meters], lag_ratio=0.02),
                  run_time=1.6 * f)
        self.hold()
        # ---- b: 34 go silent ----------------------------------------------------------------------------
        clock = T("18:00 · 34 meters silent", 26, TEXT).to_corner(UL, buff=MARGIN)
        self.play(FadeIn(clock, shift=DOWN * 0.2), run_time=0.6)
        self.play(LaggedStart(*[m.animate.set_fill(BG, 1).set_stroke(FAINT) for m in meters[SILENT]], lag_ratio=0.06),
                  run_time=3.0)
        box = DashedVMobject(SurroundingRectangle(VGroup(*meters[SILENT]), color=UNCERTAIN, buff=0.22,
                                                  corner_radius=0.15, stroke_width=3), num_dashes=70)
        q = T("?", 72, UNCERTAIN, BOLD).next_to(box, RIGHT, buff=0.5)
        self.play(Create(box), run_time=1.0)
        self.play(Write(q), run_time=0.8)
        self.hold()
