"""Scene 5, results (SIMULATED). Numbers read at render time from the stamped result files:
- held-out urban network: results/cp7_heldout.json, ledger C7-01 (coverage 0.723, false 0.000, missed 0.009);
- coverage vs. error plane: results/studies/classifier_comparison/summary.json (CLF-03..05), the data of the
  paper's coverage-vs-safety figure;
- failures: missed outages 0.006 (15-min readings) and 0.245 (60-min), CAD-4; 0.241 with 10 kW of load-shaped
  unmetered energy, C6-05 / AU-04. These two come from ledger rows only (their files live on study branches
  or need a rerun), so they are constants here with their row ids.
"""
import json

from style import *

REPO = ROOT.parent
CLF = json.loads((REPO / "results/studies/classifier_comparison/summary.json").read_text(encoding="utf8"))
FZ = CLF["frozen"]["urban6"]
COV, FALSE, MISSED = FZ["coverage"]["rate"], FZ["false_outage_rate"]["rate"], FZ["missed_outage_rate"]["rate"]
FAIL = [("15-min\nreadings", 0.006, "CAD-4"), ("60-min\nreadings", 0.245, "CAD-4"),
        ("10 kW unmetered,\nload-shaped", 0.241, "C6-05")]


def err(m):
    return m["false_outage_rate"]["rate"] + m["missed_outage_rate"]["rate"]


class S05Results(Timed):
    DEFAULT = [14, 8, 17]
    SECTION = "Results"

    def construct(self):
        self.add(tag())
        self.lower_third()
        # ---- a: held-out network ----------------------------------------------------------------------
        cap = self.caption("held-out urban network · method frozen · evaluated once")
        stats_ = VGroup(*[VGroup(T(f"{v:.3f}", 72, TEXT, SEMIBOLD), T(l, 24, MUTED)).arrange(DOWN, buff=0.2)
                          for v, l in [(COV, "coverage: share decided"), (FALSE, "false-outage rate"),
                                       (MISSED, "missed-outage rate")]]).arrange(RIGHT, buff=1.3).move_to(UP * 0.9)
        w = 10.0
        dec = Rectangle(width=w * COV, height=0.5, stroke_width=0, fill_color=MUTED, fill_opacity=0.6)
        per = Rectangle(width=w * (1 - COV), height=0.5, stroke_width=0, fill_color=UNCERTAIN, fill_opacity=0.6)
        bar = VGroup(dec, per).arrange(RIGHT, buff=0).move_to(DOWN * 1.6)
        bl = VGroup(T(f"decided {100 * COV:.1f}%", 22, TEXT).next_to(dec, DOWN, buff=0.2),
                    T(f"to a person {100 * (1 - COV):.1f}%", 22, UNCERTAIN).next_to(per, DOWN, buff=0.2))
        self.play(FadeIn(cap, shift=DOWN * 0.2), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(s, shift=UP * 0.3) for s in stats_], lag_ratio=0.3), run_time=2.0)
        self.play(GrowFromEdge(dec, LEFT), run_time=1.0)
        self.play(GrowFromEdge(per, LEFT), FadeIn(bl), run_time=0.8)
        self.hold()
        # ---- b: coverage vs. error plane ----------------------------------------------------------------
        ax = Axes(x_range=[0, 1.0, 0.25], y_range=[0, 0.9, 0.3], x_length=8.5, y_length=4.4, tips=False,
                  axis_config={"color": LINE, "stroke_width": 2}).move_to([-0.6, 0.0, 0])
        ax.add(VGroup(*[T(f"{v:g}", 20, MUTED).next_to(ax.c2p(v, 0), DOWN, buff=0.15) for v in (0, 0.25, 0.5, 0.75, 1)]),
               VGroup(*[T(f"{v:g}", 20, MUTED).next_to(ax.c2p(0, v), LEFT, buff=0.15) for v in (0, 0.3, 0.6, 0.9)]))
        xl = T("coverage", 22, MUTED).next_to(ax.x_axis, DOWN, buff=0.55)
        yl = T("false + missed outages", 22, MUTED).rotate(PI / 2).next_to(ax.y_axis, LEFT, buff=0.6)
        base = VGroup()
        for name, v in CLF["baselines"]["urban6"].items():
            p = ax.c2p(v["coverage"], v["false_outage_rate"] + v["missed_outage_rate"])
            base.add(VGroup(Square(0.16, stroke_width=0, fill_color=MUTED, fill_opacity=1).move_to(p),
                            T(name, 18, MUTED).next_to(p, RIGHT if name == "naive" else LEFT, buff=0.15)))
        clf = VGroup(*[Circle(0.07, color=FAINT, stroke_width=2).move_to(ax.c2p(r["urban6"]["coverage"]["rate"], err(r["urban6"])))
                       for m in CLF["models"].values() for r in m["seeds"].values()])
        star = Star(5, outer_radius=0.2, color=COMMS, fill_opacity=1).move_to(ax.c2p(COV, err(FZ)))
        sl = T("SHAHID", 22, COMMS, SEMIBOLD).next_to(star, LEFT, buff=0.2)
        legend = VGroup(VGroup(Square(0.16, stroke_width=0, fill_color=MUTED, fill_opacity=1), T("simple rules", 18, MUTED)).arrange(RIGHT, buff=0.15),
                        VGroup(Circle(0.07, color=FAINT, stroke_width=2), T("trained classifiers", 18, MUTED)).arrange(RIGHT, buff=0.15)
                        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).next_to(ax, RIGHT, buff=0.5).align_to(ax, UP)
        better = T("better: right and low", 18, FAINT).next_to(legend, DOWN, buff=0.4).align_to(legend, LEFT)
        self.play(FadeOut(VGroup(stats_, bar, bl)), FadeOut(cap), FadeIn(ax), FadeIn(xl), FadeIn(yl), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(b, scale=0.5) for b in base], lag_ratio=0.2), FadeIn(legend), run_time=1.2)
        self.play(LaggedStart(*[GrowFromCenter(c) for c in clf], lag_ratio=0.05), run_time=1.2)
        self.play(GrowFromCenter(star), FadeIn(sl), FadeIn(better), run_time=0.8)
        self.play(Flash(star, color=COMMS, flash_radius=0.35), run_time=0.7)
        self.hold()
        # ---- c: where it fails ------------------------------------------------------------------------
        plane = VGroup(ax, xl, yl, base, clf, star, sl, legend, better)
        self.play(plane.animate.scale(0.55).to_edge(LEFT, buff=MARGIN).shift(UP * 0.4), run_time=1.0)
        fa = Axes(x_range=[0, 3, 1], y_range=[0, 0.3, 0.1], x_length=5.2, y_length=3.6, tips=False,
                  axis_config={"color": LINE, "stroke_width": 2}, x_axis_config={"include_ticks": False}).move_to([3.6, 0.3, 0])
        fa.add(VGroup(*[T(f"{v:g}", 18, MUTED).next_to(fa.c2p(0, v), LEFT, buff=0.12) for v in (0, 0.1, 0.2, 0.3)]))
        ttl = T("missed-outage rate", 22, MUTED).next_to(fa, UP, buff=0.35)
        lim = DashedLine(fa.c2p(0, 0.05), fa.c2p(3, 0.05), color=UNCERTAIN, stroke_width=2)
        liml = T("limit 0.05", 18, UNCERTAIN).next_to(fa.c2p(0.5, 0.05), UP, buff=0.1)
        bars = VGroup()
        for i, (lab, v, _) in enumerate(FAIL):
            b = Rectangle(width=0.9, height=max(fa.c2p(0, v)[1] - fa.c2p(0, 0)[1], 0.02), stroke_width=0,
                          fill_color=MUTED if i == 0 else OUTAGE, fill_opacity=0.8)
            b.move_to(fa.c2p(i + 0.5, 0), aligned_edge=DOWN)
            bars.add(VGroup(b, T(f"{v:.3f}", 22).next_to(b, UP, buff=0.1),
                            T(lab, 18, MUTED).next_to(fa.c2p(i + 0.5, 0), DOWN, buff=0.15)))
        foot = T("SIMULATED on German benchmark networks · no Tunisian data tested yet", 20, UNCERTAIN).to_edge(DOWN, buff=1.3)
        self.play(FadeIn(fa), FadeIn(ttl), Create(lim), FadeIn(liml), run_time=0.8)
        self.play(LaggedStart(*[GrowFromEdge(b[0], DOWN) for b in bars], lag_ratio=0.3),
                  LaggedStart(*[FadeIn(b[1:]) for b in bars], lag_ratio=0.3), run_time=1.8)
        self.play(FadeIn(foot, shift=UP * 0.2), run_time=0.8)
        self.hold()
