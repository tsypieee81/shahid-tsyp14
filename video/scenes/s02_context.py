"""Scene 2, context. Paper references (Section I): [1] africanmanager2026compteurs and [2]
webdo2026compteurs for about 80,000 LV meters by end of March 2026 in a first phase of 450,000;
[4]-[6] newarab2026heatwave, africanmanager2026heat, webdo2026delestages for the summer 2026 rotating cuts."""
from style import *


def truck(color):
    body = Rectangle(width=1.1, height=0.55, stroke_color=color, stroke_width=3)
    cab = Rectangle(width=0.45, height=0.4, stroke_color=color, stroke_width=3).next_to(body, RIGHT, buff=0).align_to(body, DOWN)
    wheels = VGroup(*[Circle(0.12, color=color, stroke_width=3, fill_color=BG, fill_opacity=1)
                      .move_to(body.get_bottom() + RIGHT * x) for x in (-0.3, 0.75)])
    return VGroup(body, cab, wheels)


def source(s):
    return T(s, 18, FAINT).to_edge(DOWN, buff=MARGIN)


class S02Context(Timed):
    DEFAULT = [10, 5, 11]
    SECTION = "Context"

    def construct(self):
        self.lower_third()
        # ---- a: the rollout: 45 squares of 10,000 meters, 8 filled -----------------------------------
        grid = VGroup(*[Square(0.42, stroke_color=LINE, stroke_width=2) for _ in range(45)]).arrange_in_grid(5, 9, buff=0.12)
        grid.move_to([-2.2, 0.2, 0])
        key = T("each square: 10,000 meters", 18, FAINT).next_to(grid, DOWN, buff=0.3).align_to(grid, LEFT)
        n80 = VGroup(T("80,000", 48, COMMS, SEMIBOLD), T("LV meters by end of March 2026", 22, MUTED)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        n450 = VGroup(T("450,000", 48, TEXT, SEMIBOLD), T("first phase", 22, MUTED)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        nums = VGroup(n80, n450).arrange(DOWN, aligned_edge=LEFT, buff=0.6).next_to(grid, RIGHT, buff=0.9)
        title = self.caption("STEG is rolling out smart meters", TEXT)
        src = source("Press reports, paper refs [1], [2] (African Manager; Webdo, 2026)")
        self.play(FadeIn(title, shift=DOWN * 0.2), FadeIn(src), run_time=0.8)
        self.play(LaggedStart(*[Create(s) for s in grid], lag_ratio=0.02), FadeIn(n450), FadeIn(key), run_time=1.6)
        self.play(LaggedStart(*[s.animate.set_fill(COMMS, 0.85).set_stroke(COMMS) for s in grid[:8]], lag_ratio=0.15),
                  FadeIn(n80, shift=RIGHT * 0.2), run_time=1.6)
        self.hold()
        # ---- b: rotating cuts: four districts go dark in turn ------------------------------------------
        blocks = VGroup()
        for _ in range(4):
            houses = VGroup(*[Square(0.34, stroke_width=0, fill_color=TEXT, fill_opacity=0.85) for _ in range(9)]).arrange_in_grid(3, 3, buff=0.12)
            blocks.add(VGroup(RoundedRectangle(corner_radius=0.12, width=1.7, height=1.7, stroke_color=LINE, stroke_width=2), houses))
        blocks.arrange(RIGHT, buff=0.6).move_to([0, 0.2, 0])
        title2 = self.caption("summer 2026: rotating power cuts", TEXT)
        src2 = source("Press reports, paper refs [4]–[6] (The New Arab; African Manager; Webdo, 2026)")
        self.play(FadeOut(VGroup(grid, key, nums)), ReplacementTransform(title, title2), ReplacementTransform(src, src2),
                  FadeIn(blocks), run_time=0.8)
        for i in range(4):
            back = [blocks[i - 1][1].animate.set_fill(TEXT, 0.85)] if i else []
            self.play(blocks[i][1].animate.set_fill(FAINT, 0.15), *back, run_time=0.6)
        self.hold()
        # ---- c: two causes, opposite answers ------------------------------------------------------------
        left = VGroup(T("Outage", 34, OUTAGE, SEMIBOLD), T("send a crew", 24, MUTED)).arrange(DOWN, buff=0.15).move_to([-3.3, 1.6, 0])
        right = VGroup(T("Data lost", 34, COMMS, SEMIBOLD), T("no crew", 24, MUTED)).arrange(DOWN, buff=0.15).move_to([3.3, 1.6, 0]).align_to(left, UP)
        divider = DashedLine(UP * 2.6, DOWN * 2.2, color=LINE, stroke_width=2)
        tl, tr = truck(OUTAGE).move_to([-7.5, -0.8, 0]), truck(COMMS).move_to([1.2, -0.8, 0]).set_stroke(opacity=0)
        self.play(FadeOut(VGroup(blocks, title2, src2)), FadeIn(left), FadeIn(right), Create(divider), run_time=0.8)
        self.play(tl.animate.move_to([-3.3, -0.8, 0]), run_time=1.6, rate_func=ease_out_cubic)
        cross = VGroup(Line(UL, DR), Line(DL, UR)).scale(0.6).set_stroke(COMMS, 4).move_to([3.3, -0.8, 0])
        self.play(tr.animate.move_to([3.3, -0.8, 0]).set_stroke(opacity=0.4), run_time=1.2)
        self.play(Create(cross), run_time=0.6)
        self.hold()
