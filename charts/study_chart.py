from io import BytesIO
from datetime import datetime, timedelta
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import arabic_reshaper
from bidi.algorithm import get_display
import jdatetime
import os

# ---- فونت ----
_FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "Vazirmatn.ttf")
if os.path.exists(_FONT_PATH):
    fm.fontManager.addfont(_FONT_PATH)
    _prop = fm.FontProperties(fname=_FONT_PATH)
    _FONT_NAME = _prop.get_name()
else:
    _prop = fm.FontProperties()
    _FONT_NAME = "DejaVu Sans"

PALETTE = [
    "#01696f", "#4f98a3", "#6daa45", "#d19900", "#da7101",
    "#006494", "#7a39bb", "#a12c7b", "#a13544", "#437a22",
]

LIGHT_BG   = "#FFFFFF"
CARD_BG    = "#F8F9FA"
GRID_COLOR = "#E9ECEF"
TEXT_COLOR = "#212529"
MUTED      = "#6C757D"
ACCENT     = "#01696f"

WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]


def _fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(str(text)))


def _setup():
    plt.rcParams.update({
        "font.family":      _FONT_NAME,
        "axes.facecolor":   CARD_BG,
        "figure.facecolor": LIGHT_BG,
        "text.color":       TEXT_COLOR,
        "axes.labelcolor":  MUTED,
        "xtick.color":      MUTED,
        "ytick.color":      MUTED,
        "axes.edgecolor":   GRID_COLOR,
        "grid.color":       GRID_COLOR,
        "grid.linestyle":   "--",
        "grid.alpha":       0.6,
    })


def generate_weekly_bar_chart(sessions: list, user_name: str) -> BytesIO:
    _setup()

    today = datetime.now().date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    day_minutes = {d: 0 for d in days}
    for s in sessions:
        d = s.session_date.date() if hasattr(s.session_date, "date") else s.session_date
        if d in day_minutes:
            day_minutes[d] += s.duration_minutes

    labels = []
    for d in days:
        jd = jdatetime.date.fromgregorian(date=d)
        wd = _fa(WEEKDAYS_FA[d.weekday()])
        labels.append(_fa(jd.strftime("%m/%d")) + "\n" + wd)

    values = [day_minutes[d] for d in days]
    bar_colors = [PALETTE[0] if v > 0 else "#DEE2E6" for v in values]
    total_m = sum(values)
    avg = total_m / 7 if total_m else 0
    max_v = max(values) if max(values) > 0 else 1

    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor(LIGHT_BG)

    bars = ax.bar(
        range(len(labels)), values, color=bar_colors,
        width=0.6, edgecolor="white", linewidth=1.5, zorder=3,
    )

    for bar, val in zip(bars, values):
        if val > 0:
            h, m = divmod(val, 60)
            lbl = _fa(f"{h} ساعت {m} دقیقه") if h > 0 else _fa(f"{m} دقیقه")
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max_v * 0.02,
                lbl, ha="center", va="bottom",
                fontsize=8.5, color=ACCENT, fontweight="bold",
                fontproperties=_prop,
            )

    if avg > 0:
        ax.axhline(avg, color=PALETTE[3], linewidth=2,
                   linestyle="--", zorder=2, alpha=0.85)
        ax.text(
            len(labels) - 0.4,
            avg + max_v * 0.015,
            _fa(f"میانگین: {int(avg)} دقیقه"),
            color=PALETTE[3], fontsize=8.5, va="bottom",
            fontproperties=_prop,
        )

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontproperties=_prop, fontsize=9)
    ax.set_title(
        _fa(f"گزارش هفتگی مطالعه — {user_name}"),
        fontsize=15, fontweight="bold", color=TEXT_COLOR,
        fontproperties=_prop, pad=16,
    )
    ax.set_ylabel(_fa("دقیقه"), fontsize=10, color=MUTED, fontproperties=_prop)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)

    total_h, total_mn = divmod(total_m, 60)
    fig.text(
        0.5, -0.01,
        _fa(f"مجموع مطالعه: {total_h} ساعت و {total_mn} دقیقه  |  تعداد جلسات: {len(sessions)}"),
        ha="center", fontsize=9.5, color=MUTED, fontproperties=_prop,
    )

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=LIGHT_BG)
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_subject_pie_chart(sessions: list, user_name: str) -> BytesIO | None:
    if not sessions:
        return None
    _setup()

    subject_stats: dict = {}
    for s in sessions:
        subject_stats[s.subject] = subject_stats.get(s.subject, 0) + s.duration_minutes
    if not subject_stats:
        return None

    labels_pie = list(subject_stats.keys())
    sizes = list(subject_stats.values())
    clrs = PALETTE[: len(labels_pie)]
    total = sum(sizes)

    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor(LIGHT_BG)
    ax.set_facecolor(LIGHT_BG)

    _, _, autotexts = ax.pie(
        sizes, colors=clrs, autopct="%1.0f%%",
        startangle=140, pctdistance=0.72,
        wedgeprops=dict(width=0.6, edgecolor="white", linewidth=2.5),
        textprops={"fontproperties": _prop},
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_color("white")
        at.set_fontweight("bold")

    legend_labels = []
    for lbl, sz in zip(labels_pie, sizes):
        h, m = divmod(sz, 60)
        pct = round(sz / total * 100)
        time_str = f"{h} ساعت {m} دقیقه" if h > 0 else f"{m} دقیقه"
        legend_labels.append(_fa(f"{lbl}:  {time_str}  ({pct}%)"))

    patches = [mpatches.Patch(color=c, label=l)
               for c, l in zip(clrs, legend_labels)]
    ax.legend(
        handles=patches, loc="lower center",
        bbox_to_anchor=(0.5, -0.22),
        ncol=2, frameon=False, fontsize=9.5,
        prop=_prop,
    )
    ax.set_title(
        _fa(f"توزیع درس‌ها — {user_name}"),
        fontsize=15, fontweight="bold", color=TEXT_COLOR,
        fontproperties=_prop, pad=16,
    )

    total_h, total_mn = divmod(total, 60)
    fig.text(
        0.5, -0.02,
        _fa(f"مجموع: {total_h} ساعت و {total_mn} دقیقه"),
        ha="center", fontsize=9.5, color=MUTED, fontproperties=_prop,
    )

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=LIGHT_BG)
    plt.close(fig)
    buf.seek(0)
    return buf