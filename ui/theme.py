"""Design tokens, formatters and the one stylesheet of the operator console (ISA-101 style: grey
surfaces, saturated colour only for verdict classes, green only for a verified chain).

Every numeral on screen goes through the fmt_* functions below (checked by tests/test_ui_panels.py).
"""
import math

import pandas as pd

# surfaces and text
BG, CARD, RAISED, BORDER, HOVER = "#0b1220", "#111a2e", "#16233a", "#1e293b", "#1c2a42"
TEXT, MUTED, FAINT = "#e2e8f0", "#94a3b8", "#64748b"
OK = "#34d399"  # ONLY for "chain intact" and verified states
COLORS = {"OUTAGE": "#ef4444", "UNCERTAIN": "#f59e0b", "COMMS_FAILURE": "#3b82f6",
          "REPORTING": FAINT, "PV": "#a3e635", "LINE": "#334155", "TRANSFORMER": TEXT, "ABSTAIN": "#475569"}
VERDICTS = ("OUTAGE", "UNCERTAIN", "COMMS_FAILURE")
GLOW = {"OUTAGE": "glow-red", "UNCERTAIN": "glow-amber", "COMMS_FAILURE": "glow-blue"}
SHORT = {"OUTAGE": "Outage", "UNCERTAIN": "Uncertain", "COMMS_FAILURE": "Comms failure"}
TABS = {"OUTAGE": "Outages awaiting approval", "UNCERTAIN": "Uncertain", "COMMS_FAILURE": "Comms unconfirmed",
        "AUDIT": "Audit sample"}
LABELS = TABS
ICONS = {"OUTAGE": ":material/power_off:", "UNCERTAIN": ":material/help:",
         "COMMS_FAILURE": ":material/signal_wifi_off:", "AUDIT": ":material/fact_check:"}
GLYPH = {"OUTAGE": "power_off", "UNCERTAIN": "help", "COMMS_FAILURE": "signal_wifi_off"}  # Material Symbols names
BANNER = "SIMULATED DATA — Phase 1/2 prototype, not a deployed system."
VIEWS = {"Situation": ":material/dashboard:", "Queues": ":material/inbox:", "Network": ":material/hub:",
         "Trace": ":material/show_chart:", "Audit": ":material/receipt_long:", "Trust": ":material/shield_person:"}

# Delta direction per KPI tile: "inverse" = an increase is bad (shown red), "normal" = an increase is
# good (green). Comparator for every delta: the same replay one hour (4 intervals) earlier.
DELTA = {"OUTAGE": "inverse", "UNCERTAIN": "inverse", "COMMS_FAILURE": "inverse", "reporting": "normal"}
DELTA_BACK = 4  # intervals
# ---- formatters --------------------------------------------------------------------------------------------
def _ok(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))


def fmt_kwh(x, unit=True, signed=False):
    if not _ok(x):
        return "—"
    s = f"{x:+.2f}" if signed else f"{x:.2f}"
    return f"{s} kWh" if unit else s


def fmt_p(x):
    """Three decimals; the ends read '>0.999' and '<0.001', never a rounded 1.000 or 0.000."""
    if not _ok(x):
        return "—"
    if x >= 0.9995:
        return ">0.999"
    if x <= 0.0005:
        return "<0.001"
    return f"{x:.3f}"


def fmt_hm(t):
    """24-hour HH:MM of a timestamp, an ISO string or an interval index of the day."""
    if isinstance(t, (int,)) and not isinstance(t, bool):
        return f"{(t * 15) // 60:02d}:{(t * 15) % 60:02d}"
    return pd.Timestamp(t).strftime("%H:%M")


def fmt_pct(x, n=None):
    """'43%' or, with a denominator n, '43% (3 of 7)' where x is the count."""
    if n is None:
        return f"{100 * x:.0f}%" if _ok(x) else "—"
    return f"{100 * x / n:.0f}% ({x} of {n})" if n else "—"


def fmt_int(x, unit=""):
    if not _ok(x):
        return "—"
    return f"{int(x)}{(' ' + unit) if unit else ''}"


def fmt_num(x, dp=2):
    return f"{x:.{dp}f}" if _ok(x) else "—"


def fmt_signed(x, unit=""):
    return f"{int(x):+d}{(' ' + unit) if unit else ''}" if _ok(x) else "—"


# ---- small HTML pieces (classes from CSS below) ------------------------------------------------------------
def chip(text, kind="", title=""):
    return f'<span class="chip {kind}" title="{title}">{text}</span>'


def icon(name, color=MUTED, size=18):
    return f'<span class="msym" style="color:{color};font-size:{size}px">{name}</span>'


CSS = """
<style>
:root{--card:#111a2e;--raised:#16233a;--border:#1e293b;--hover:#1c2a42;--text:#e2e8f0;--muted:#94a3b8;--faint:#64748b}
.block-container{padding-top:3.2rem;padding-bottom:1rem;max-width:100%}
[data-testid="stMetricValue"],.kpi-value,.hero-num,td,.tnum,[data-testid="stMetricDelta"]{font-variant-numeric:tabular-nums}
.msym{font-family:'Material Symbols Rounded';font-weight:400;line-height:1;vertical-align:middle;display:inline-block}
.chip{display:inline-flex;align-items:center;gap:4px;padding:2px 9px;border:1px solid var(--border);border-radius:999px;
 font-size:11px;letter-spacing:.04em;color:var(--muted);background:var(--raised);white-space:nowrap;margin:0 4px 2px 0}
.chip-active{border-color:#3b82f6;color:var(--text)}
.chip-amber{border-color:#f59e0b;color:#f59e0b;background:transparent}
.chip-ok{border-color:#34d399;color:#34d399;background:transparent}
.chip-bad{border-color:#ef4444;color:#ef4444;background:transparent}
.chip-OUTAGE{border-color:#ef4444;color:#fca5a5}.chip-UNCERTAIN{border-color:#f59e0b;color:#fcd34d}
.chip-COMMS_FAILURE{border-color:#3b82f6;color:#93c5fd}
.delta-up{color:#34d399}.delta-down{color:#ef4444}
.topbar{display:flex;align-items:center;gap:6px;flex-wrap:wrap;min-height:34px}
.mark{font-weight:700;letter-spacing:.12em;color:var(--text);margin-right:6px}
.clock{font-family:ui-monospace,Consolas,monospace;font-size:15px;color:var(--text);margin-right:6px}
.simline{font-size:11px;color:#f59e0b;letter-spacing:.04em;margin-top:2px}
.shows{margin:0 0 6px 0;padding-left:16px;font-size:12px;color:var(--muted)}.shows li{margin:2px 0}
.micro{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 4px 0}
.kpi-sub{font-size:11px;color:var(--muted);margin-top:-6px}
.kpi-value{font-size:28px;font-weight:650;color:var(--text)}
.unit{font-size:13px;color:var(--muted);font-weight:400;margin-left:3px}
.hero-num{font-size:26px;font-weight:650;color:var(--text);line-height:1.1}
.railcard{font-size:13px;color:var(--text)}
.feed-row{display:flex;gap:10px;align-items:center}
.feed-icon{width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;background:var(--raised)}
.meta-strip{display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid var(--border);margin-top:8px}
.meta-strip>div{padding:6px 8px;border-left:1px solid var(--border)}.meta-strip>div:first-child{border-left:none;padding-left:0}
.meta-strip b{display:block;font-size:13px;color:var(--text);font-weight:600}
.meta-strip span{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint)}
.tickbar{display:flex;gap:2px;align-items:flex-end;height:26px;flex-wrap:nowrap;overflow:hidden}
.tickbar i{display:block;width:3px;height:26px;border-radius:1px}
.probrow{display:grid;grid-template-columns:minmax(96px,1.1fr) 1fr 40px;gap:8px;align-items:center;font-size:12px;color:var(--muted);margin:5px 0}
.probrow .bar{height:8px;background:var(--raised);border-radius:4px;overflow:hidden}
.probrow .bar i{display:block;height:8px;border-radius:4px}
.probrow b{color:var(--text);font-weight:600;text-align:right}
.vm{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:4px;font-size:12px;color:var(--muted)}
.vm b{font-size:16px;color:var(--text);font-weight:650}
.scale{position:relative;height:14px;background:var(--raised);border-radius:7px;margin:6px 0 2px}
.scale .band{position:absolute;top:0;bottom:0;background:rgba(245,158,11,.30)}
.scale .mk{position:absolute;top:-3px;width:4px;height:20px;border-radius:2px;background:#f8fafc}
.scale-ends{display:flex;justify-content:space-between;font-size:10px;color:var(--faint)}
.glow-red{box-shadow:0 0 0 1px #ef4444,0 0 14px rgba(239,68,68,.35)}
.glow-amber{box-shadow:0 0 0 1px #f59e0b,0 0 14px rgba(245,158,11,.30)}
.glow-blue{box-shadow:0 0 0 1px #3b82f6,0 0 14px rgba(59,130,246,.35)}
/* bordered containers as cards */
[data-testid="stVerticalBlockBorderWrapper"],div[class*="st-key-card"]{border-radius:10px}
div[class*="st-key-card"]{background:var(--card);border:1px solid var(--border);padding:14px}
div[class*="st-key-kpi_"]{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 14px}
div.st-key-kpi_OUTAGE{border-left:3px solid #ef4444}div.st-key-kpi_UNCERTAIN{border-left:3px solid #f59e0b}
div.st-key-kpi_COMMS_FAILURE{border-left:3px solid #3b82f6}
div[class*="st-key-kpi_"] [data-testid="stMetric"]{padding:0;border:none;background:transparent}
div[class*="st-key-kpi_"] [data-testid="stMetricValue"]{font-size:28px;font-weight:650}
div[class*="st-key-kpi_"] [data-testid="stMetricLabel"] p{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
div.st-key-card_hero{border-width:1px}
div[class*="st-key-hero_OUTAGE"]{box-shadow:0 0 0 1px #ef4444,0 0 14px rgba(239,68,68,.25)}
div[class*="st-key-hero_UNCERTAIN"]{box-shadow:0 0 0 1px #f59e0b,0 0 14px rgba(245,158,11,.22)}
div[class*="st-key-hero_COMMS_FAILURE"]{box-shadow:0 0 0 1px #3b82f6,0 0 14px rgba(59,130,246,.25)}
/* icon rail */
div.st-key-rail button{width:44px;height:44px;border-radius:10px;justify-content:center}
div.st-key-rail button[kind="primary"]{background:#1e3a5f;border:1px solid #3b82f6;color:#e2e8f0}
div.st-key-rail button[kind="tertiary"]{color:var(--muted)}
div.st-key-rail button[kind="tertiary"]:hover{background:var(--hover);color:var(--text)}
/* event feed rows are buttons */
div[class*="st-key-feed"] button{width:100%;justify-content:flex-start;text-align:left;background:var(--raised);
 border:1px solid var(--border);border-radius:8px;padding:6px 10px;min-height:44px}
div[class*="st-key-feed"] button:hover{background:var(--hover);border-color:#334155}
div[class*="st-key-feed"] button div{justify-content:flex-start;text-align:left;width:100%}
div[class*="st-key-feed"] button p{font-size:13px;text-align:left}
div[class*="st-key-card"] .stMarkdown p{font-size:13px;line-height:1.5}
div[class*="st-key-card"] [data-testid="stAlert"] p{font-size:12px}
div.st-key-nav_Evaluation button{opacity:.5;position:relative}
div.st-key-nav_Evaluation button::after{content:"";position:absolute;top:7px;right:7px;width:6px;height:6px;border-radius:50%;background:#f59e0b}
div[class*="st-key-feedsel_"] button{border-color:#3b82f6;background:#15233d}
/* tables, scrollbars */
[data-testid="stDataFrame"] [role="columnheader"]{text-transform:uppercase;font-size:11px;letter-spacing:.06em}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-thumb{background:#1e293b;border-radius:4px}
.present [data-testid="stMetricValue"]{font-size:34px}
</style>
"""
