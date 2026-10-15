"""Scene 7, impact and deployment (ESTIMATES on SIMULATED rates). Read at render time from
results/business/business.json and configs/business.yaml:
- 149 transformer substations, Douz-sized district: configs/business.yaml, ledger BUS-02;
- 13.32 s per transformer-year (one laptop process; 13.36 s wall time): BUS-04;
- operator review cost, lower bound at the minimum wage, 5 min per item, rural2 rates: v1 120,486.23 and
  gate-escalate 51,046.66 TND per district-year: BUS-06;
- prerequisite (transformer meter): TN-H2.
"""
import json

import yaml

from style import *

REPO = ROOT.parent
BIZ = json.loads((REPO / "results/business/business.json").read_text(encoding="utf8"))
N_SUB = yaml.safe_load((REPO / "configs/business.yaml").read_text(encoding="utf8"))["facts"]["douz_transformer_substations"]["value"]
SECONDS = BIZ["compute"]["seconds_per_transformer_year"]
WL = BIZ["workload"]
COST = {k: WL[f"rural2/ff_1pct/{k}"]["by_review_minutes"]["5"]["district_cost"]["tnd"] for k in ("v1", "v1+gate-escalate")}


def glyph(r=0.09, color=MUTED):
    return VGroup(Circle(r, color=color, stroke_width=2), Circle(r, color=color, stroke_width=2).shift(RIGHT * r))


class S07Impact(Timed):
    DEFAULT = [9, 11, 4]
    SECTION = "Impact and deployment"

    def construct(self):
        self.add(tag())
        self.lower_third()
        # ---- a: the district and its compute ----------------------------------------------------------
        grid = VGroup(*[glyph() for _ in range(N_SUB)]).arrange_in_grid(cols=15, buff=0.18).move_to([-2.8, 0.2, 0])
        cap = self.caption(f"a Douz-sized district: {N_SUB} substations", TEXT)
        sw = VGroup(T(f"{SECONDS:.1f} s", 60, TEXT, SEMIBOLD), T("to score one transformer-year", 22, MUTED),
                    T("one laptop process", 18, FAINT)).arrange(DOWN, buff=0.15).move_to([4.2, 0.4, 0])
        self.play(FadeIn(cap, shift=DOWN * 0.2), run_time=0.6)
        self.play(LaggedStart(*[FadeIn(g, scale=0.5) for g in grid], lag_ratio=0.01), run_time=2.0)
        self.play(grid[0].animate.set_color(COMMS), FadeIn(sw, shift=LEFT * 0.2), run_time=0.8)
        self.hold()
        # ---- b: the cost is people ---------------------------------------------------------------------
        cap2 = self.caption("operator review: the main cost", TEXT)
        scale = 7.5 / COST["v1"]
        bars = VGroup()
        for key, lab in (("v1", "current rules"), ("v1+gate-escalate", "escalating gate, not yet wired in")):
            r = Rectangle(width=COST[key] * scale, height=0.6, stroke_width=0, fill_color=MUTED, fill_opacity=0.7)
            bars.add(VGroup(r, T(f"≥ {int(COST[key]):,} TND", 30, TEXT, SEMIBOLD).next_to(r, RIGHT, buff=0.25),
                            T(lab, 20, MUTED).next_to(r, UP, buff=0.12).align_to(r, LEFT)))
        bars.arrange(DOWN, aligned_edge=LEFT, buff=0.6).move_to([-0.6, 0.4, 0])
        note = T("lower bound per district-year: minimum wage, 5 min per item", 20, FAINT).next_to(bars, DOWN, buff=0.5).align_to(bars, LEFT)
        self.play(FadeOut(VGroup(grid, sw)), ReplacementTransform(cap, cap2), run_time=0.7)
        self.play(LaggedStart(*[GrowFromEdge(b[0], LEFT) for b in bars], lag_ratio=0.4),
                  LaggedStart(*[FadeIn(b[1:]) for b in bars], lag_ratio=0.4), run_time=1.8)
        self.play(FadeIn(note), run_time=0.6)
        self.hold()
        # ---- c: prerequisite ---------------------------------------------------------------------------
        tr = glyph(0.45, TEXT)
        meter = VGroup(Square(0.6, color=COMMS, stroke_width=3), T("kWh", 16, COMMS)).arrange(ORIGIN)
        pre = VGroup(tr, meter).arrange(DOWN, buff=0.3).move_to([0, 0.5, 0])
        ring = Circle(radius=1.4, color=UNCERTAIN, stroke_width=3).move_to(pre)
        lab = T("prerequisite: an energy meter at each transformer", 28, TEXT).next_to(ring, DOWN, buff=0.4)
        self.play(FadeOut(VGroup(bars, note, cap2)), FadeIn(pre), run_time=0.6)
        self.play(Create(ring), FadeIn(lab), run_time=0.9)
        self.hold()
