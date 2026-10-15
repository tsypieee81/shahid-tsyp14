"""Scene 8, how we work: terminal cards built from the real command output captured by build.py
(video/build/cards.json: pytest, check_numbers, check_tables, and protocol commits from git log), then the title."""
import json

from style import *


def card(cmd, lines, width=6.4):
    body = VGroup(T("$ " + cmd, 20, TEXT, font=MONO),
                  *[T(l, 17, OK if ok else MUTED, font=MONO) for l, ok in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
    if body.width > width - 0.5:
        body.scale_to_fit_width(width - 0.5)
    box = RoundedRectangle(corner_radius=0.14, width=width, height=body.height + 0.55, stroke_color=BORDER,
                           stroke_width=2, fill_color=CARD, fill_opacity=1)
    return VGroup(box, body.move_to(box).align_to(box, LEFT).shift(RIGHT * 0.25))


class S08Work(Timed):
    DEFAULT = [7, 3]
    SECTION = "How we work"

    def construct(self):
        data = json.loads((BUILD / "cards.json").read_text(encoding="utf8"))
        self.lower_third()
        cards = VGroup(*[card(c["cmd"], c["lines"]) for c in data["checks"]],
                       card("git log  (protocols, committed before their runs)", [(l, False) for l in data["commits"]]))
        cards.arrange_in_grid(2, 2, buff=0.35).scale_to_fit_width(config.frame_width - 2 * MARGIN)
        if cards.height > config.frame_height - 2.2:
            cards.scale_to_fit_height(config.frame_height - 2.2)
        cards.move_to(UP * 0.2)
        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.3) for c in cards], lag_ratio=0.25), run_time=2.4)
        self.hold()
        title = VGroup(T("SHAHID", 80, TEXT, BOLD), T("the witness layer", 36, MUTED)).arrange(DOWN, buff=0.3)
        sub = T("SIMULATED Phase 1 prototype · IEEE TSYP14 EnergyMind challenge", 20, FAINT).to_edge(DOWN, buff=MARGIN)
        self.play(FadeOut(cards), FadeIn(title, scale=0.95), FadeIn(sub), run_time=1.0)
        self.hold()
