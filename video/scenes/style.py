"""Shared style for every scene: palette from ui/theme.py, Inter and JetBrains Mono, beat timing, and the
drawing helpers used by more than one scene (network, hypothesis curves, probability scale)."""
import json
import os
from pathlib import Path

import manimpango
import numpy as np
from manim import *
from manim.utils.rate_functions import ease_out_cubic
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"

# palette: ui/theme.py tokens
BG, CARD, RAISED, BORDER, LINE = "#0b1220", "#111a2e", "#16233a", "#1e293b", "#334155"
TEXT, MUTED, FAINT = "#e2e8f0", "#94a3b8", "#64748b"
OUTAGE, COMMS, UNCERTAIN, OK = "#ef4444", "#3b82f6", "#f59e0b", "#34d399"

config.background_color = BG

for f in (BUILD / "fonts").rglob("*.ttf"):
    if f.name in ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf", "JetBrainsMono-Regular.ttf"):
        manimpango.register_font(str(f))
FONT, MONO = "Inter", "JetBrains Mono"
MARGIN = 0.6

# detector constants (results/detector_params.json: fitted.t_df, thresholds.bayes.abstain_band)
NU, BAND = 4, 0.03


def T(s, size=30, color=TEXT, weight=NORMAL, font=FONT):
    return Text(s, font=font, font_size=size, color=color, weight=weight)


def chip(s, color=UNCERTAIN, size=18):
    t = T(s, size, color, weight=SEMIBOLD)
    box = RoundedRectangle(corner_radius=0.12, width=t.width + 0.4, height=t.height + 0.22,
                           stroke_color=color, stroke_width=2, fill_color=BG, fill_opacity=1)
    return VGroup(box, t.move_to(box))


def tag(s="SIMULATED", color=UNCERTAIN):
    """Amber outline chip, top-right."""
    return chip(s, color).to_corner(UR, buff=MARGIN)


class Timed(Scene):
    """A scene in beats. Each beat lasts as long as its narration clip (video/build/durations.json,
    written by build.py); without it, the storyboard targets in DEFAULT are used."""
    DEFAULT = []
    SECTION = ""

    def setup(self):
        f = Path(os.environ.get("SHAHID_DURATIONS", BUILD / "durations.json"))  # a cut sets its own
        d = json.loads(f.read_text()).get(type(self).__name__) if f.exists() else None
        self.beats, self.k, self.t0 = d or self.DEFAULT, 0, 0.0

    def hold(self):
        """End the current beat: wait out whatever is left of its duration."""
        end = self.t0 + self.beats[self.k]
        left = end - self.time
        if left < -0.05:  # build.py fails on this line: the voice would drift from the picture
            print(f"OVERRUN {type(self).__name__} beat {self.k}: {-left:.2f} s")
        if left >= 1 / config.frame_rate:
            self.wait(left)
        self.t0, self.k = max(end, self.time), self.k + 1

    def caption(self, s, color=MUTED):
        return T(s, 24, color).to_corner(UL, buff=MARGIN)

    def lower_third(self):
        """Section title, bottom-left: a blue rule and the section name, faded in and out over 2.8 s."""
        rule = Rectangle(width=0.06, height=0.42, stroke_width=0, fill_color=COMMS, fill_opacity=1)
        name = T(self.SECTION, 24, MUTED).next_to(rule, RIGHT, buff=0.2)
        lt = VGroup(rule, name).to_corner(DL, buff=MARGIN)
        lt.age = 0.0

        def fade(m, dt):
            m.age += dt
            m.set_opacity(max(0.0, min(1.0, (2.8 - m.age) / 0.4, m.age / 0.4)))
        lt.set_opacity(0).add_updater(fade)
        self.add(lt)
        return lt


def network():
    """Illustrative LV network: transformer, bus, five feeders, 54 meters (feeders 2 to 4, 34 meters, go silent)."""
    tr = VGroup(Circle(0.32, color=TEXT, stroke_width=3), Circle(0.32, color=TEXT, stroke_width=3).shift(RIGHT * 0.3))
    tr.move_to([-5.9, 0, 0])
    bus = Line([-5.25, 2.4, 0], [-5.25, -2.4, 0], color=LINE, stroke_width=3)
    feeders, meters = VGroup(), VGroup()
    for y, n in zip([2.4, 1.2, 0, -1.2, -2.4], [12, 12, 12, 10, 8]):
        feeders.add(Line([-5.25, y, 0], [-4.6 + 0.42 * n, y, 0], color=LINE, stroke_width=2))
        for i in range(n):
            meters.add(Circle(0.085, color=COMMS, stroke_width=2, fill_color=COMMS, fill_opacity=0.9)
                       .move_to([-4.6 + 0.42 * (i + 0.5), y, 0]))
    link = Line(tr.get_right(), [-5.25, 0, 0], color=LINE, stroke_width=3)
    return tr, VGroup(link, bus, feeders), meters


SILENT = slice(12, 46)  # feeders 2, 3, 4: 12 + 12 + 10 = 34 meters


def silence(m):
    return m.set_fill(BG, 1).set_stroke(FAINT)


def pdf(x, mu, s):
    """Student-t density with the detector's degrees of freedom (shahid/detect.py score())."""
    return stats.t.pdf((np.asarray(x) - mu) / s, NU) / s


class Hypotheses(VGroup):
    """Axis in kWh with the two hypothesis curves, the R marker and the two heights at R,
    driven by trackers M, R, sO, sC."""

    def __init__(self, case, center=(-2.0, 0.9, 0)):
        super().__init__()
        self.P = {k: ValueTracker(v) for k, v in case.items()}
        g = self.g
        ax = self.ax = Axes(x_range=[-0.5, 5.5, 1], y_range=[0, 3.0, 1], x_length=8.2, y_length=3.6, tips=False,
                            axis_config={"color": LINE, "stroke_width": 2},
                            y_axis_config={"include_ticks": False}).move_to(center)
        ax.add(VGroup(*[T(str(i), 22, MUTED).next_to(ax.c2p(i, 0), DOWN, buff=0.18) for i in range(6)]))
        self.xl = T("kWh the witness sees", 18, FAINT).next_to(ax.x_axis, DOWN, buff=0.5).align_to(ax.x_axis, RIGHT)
        xs = np.linspace(-0.5, 5.5, 241)

        def curve(mu, sk, col):
            """Curve and its fill built straight from points: fast enough to redraw every frame."""
            pts = [ax.c2p(x, min(y, 3.0)) for x, y in zip(xs, pdf(xs, mu, g(sk)))]
            line = VMobject(stroke_color=col, stroke_width=3).set_points_as_corners(pts)
            fill = Polygon(ax.c2p(-0.5, 0), *pts, ax.c2p(5.5, 0), stroke_width=0, fill_color=col, fill_opacity=0.15)
            return VGroup(fill, line)
        top = 2.85
        self.out = always_redraw(lambda: curve(0, "sO", OUTAGE))
        self.com = always_redraw(lambda: curve(g("M"), "sC", COMMS))
        self.rx = always_redraw(lambda: DashedLine(ax.c2p(g("R"), 0), ax.c2p(g("R"), top), color=TEXT, stroke_width=2))
        self.rlab = always_redraw(lambda: T(f"R = {g('R'):.2f}", 22).next_to(ax.c2p(g("R"), top), UP, buff=0.1))
        self.do = always_redraw(lambda: Dot(ax.c2p(g("R"), pdf(g("R"), 0, g("sO"))), 0.09, color=OUTAGE))
        self.dc = always_redraw(lambda: Dot(ax.c2p(g("R"), pdf(g("R"), g("M"), g("sC"))), 0.09, color=COMMS))

    def g(self, k):
        return self.P[k].get_value()


def fraction(pos=(4.4, 1.6, 0)):
    """p = blue / (blue + red): the two curve heights at R."""
    num = Dot(radius=0.13, color=COMMS)
    den = VGroup(Dot(radius=0.13, color=COMMS), T("+", 30), Dot(radius=0.13, color=OUTAGE)).arrange(RIGHT, buff=0.15)
    bar = Line(LEFT * 0.75, RIGHT * 0.75, color=TEXT, stroke_width=3)
    return VGroup(T("p =", 34), VGroup(num, bar, den).arrange(DOWN, buff=0.18)).arrange(RIGHT, buff=0.3).move_to(pos)


def pshow(p):
    """Never 1.000 on screen: above 0.999 it reads '> 0.999' (storyboard rule)."""
    return "> 0.999" if p > 0.999 else f"{p:.3f}"


class Scale(VGroup):
    """Probability scale 0..1 with the abstention band and a needle following tracker pt."""

    def __init__(self, pt, y=-2.55):
        super().__init__()
        sc = self.sc = NumberLine(x_range=[0, 1, 0.5], length=9.6, color=LINE, stroke_width=2).move_to([0, y, 0])
        sc.add(VGroup(*[T(s, 22, MUTED).next_to(sc.n2p(v), DOWN, buff=0.18) for s, v in [("0", 0), ("0.5", 0.5), ("1", 1)]]))
        self.band = Rectangle(width=sc.n2p(1 - BAND)[0] - sc.n2p(BAND)[0], height=0.42, stroke_width=0,
                              fill_color=UNCERTAIN, fill_opacity=0.22).move_to(sc.n2p(0.5))
        self.bl = T("between 0.03 and 0.97: a person decides", 22, UNCERTAIN).next_to(self.band, UP, buff=0.18)
        self.ends = VGroup(T("outage", 22, OUTAGE).next_to(sc.n2p(0), LEFT, buff=0.3),
                           T("data lost", 22, COMMS).next_to(sc.n2p(1), RIGHT, buff=0.3))
        self.needle = always_redraw(lambda: Triangle(color=TEXT, fill_opacity=1).scale(0.12).rotate(PI)
                                    .next_to(sc.n2p(pt.get_value()), UP, buff=0.02))
