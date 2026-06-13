"""
charts/chart_generator.py
تولید ۴ نوع نمودار فارسی با Matplotlib
"""
import io
from datetime import date, timedelta
from typing import Optional
import jdatetime
from loguru import logger
from .persian_font import reverse_persian, setup_matplotlib_persian

COLORS = {
    "primary":   "#2E86AB",
    "secondary": "#A23B72",
    "success":   "#3BB273",
    "accent":    "#C73E1D",
    "purple":    "#7B2FBE",
    "teal":      "#3BB273",
    "gradient":  ["#2E86AB","#A23B72","#F18F01","#C73E1D","#7B2FBE","#3BB273","#E84855","#FF9F1C"],
    "bg":        "#FFFFFF",
    "surface":   "#F8F9FA",
    "text":      "#2D2D2D",
    "muted":     "#6C757D",
    "grid":      "#E9ECEF",
}


def _jalali_date_label(d: date) -> str:
    j = jdatetime.date.fromgregorian(date=d)
    return j.strftime("%d/%m")


class ChartGenerator:
    """کلاس اصلی تولید نمودارهای مطالعه."""

    def __init__(self) -> None:
        setup_matplotlib_persian()

    # ── نمودار میله‌ای روزانه ─────────────────────────────────────────────
    def daily_bar_chart(
        self,
        day_data: dict[date, int],
        goal_minutes: int = 120,
        user_name: str = "کاربر",
    ) -> io.BytesIO:
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(12, 6), dpi=120)
        fig.patch.set_facecolor(COLORS["bg"])
        ax.set_facecolor(COLORS["surface"])

        dates = sorted(day_data.keys())
        minutes = [day_data[d] for d in dates]
        labels = [_jalali_date_label(d) for d in dates]
        x = np.arange(len(dates))

        bar_colors = [COLORS["teal"] if m >= goal_minutes else COLORS["primary"] for m in minutes]
        bars = ax.bar(x, minutes, color=bar_colors, width=0.6, edgecolor="white", linewidth=1.5, zorder=3)

        ax.axhline(y=goal_minutes, color=COLORS["accent"], linestyle="--", linewidth=2, alpha=0.8)

        for bar, val in zip(bars, minutes):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 2,
                    str(val), ha="center", va="bottom",
                    fontsize=9, color=COLORS["text"], fontweight="bold"
                )

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_ylabel(reverse_persian("دقیقه"), fontsize=11, color=COLORS["muted"])
        ax.set_ylim(0, max(max(minutes, default=0), goal_minutes) * 1.25)
        ax.yaxis.grid(True, color=COLORS["grid"], zorder=0)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_title(reverse_persian(f"مطالعه روزانه — {user_name}"),
                     fontsize=14, fontweight="bold", color=COLORS["text"], pad=15)

        goal_patch = mpatches.Patch(color=COLORS["accent"], label=reverse_persian(f"هدف: {goal_minutes} دق"))
        achieved_patch = mpatches.Patch(color=COLORS["teal"], label=reverse_persian("به هدف رسیدی ✓"))
        ax.legend(handles=[goal_patch, achieved_patch], loc="upper left", framealpha=0.9, fontsize=9)

        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=COLORS["bg"], dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf

    # ── نمودار دایره‌ای درس‌ها ────────────────────────────────────────────
    def subject_pie_chart(
        self,
        subject_data: list[dict],
        user_name: str = "کاربر",
    ) -> io.BytesIO:
        import matplotlib.pyplot as plt

        if not subject_data:
            return self._empty_chart(reverse_persian("داده‌ای برای نمایش وجود ندارد"))

        sorted_data = sorted(subject_data, key=lambda x: x["total_minutes"], reverse=True)
        if len(sorted_data) > 7:
            top_7 = sorted_data[:7]
            top_7.append({"subject": "سایر", "total_minutes": sum(d["total_minutes"] for d in sorted_data[7:])})
            data = top_7
        else:
            data = sorted_data

        labels = [reverse_persian(d["subject"]) for d in data]
        sizes = [d["total_minutes"] for d in data]
        colors = COLORS["gradient"][:len(data)]

        fig, ax = plt.subplots(figsize=(10, 7), dpi=120)
        fig.patch.set_facecolor(COLORS["bg"])

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors,
            autopct="%1.1f%%", startangle=140,
            wedgeprops={"linewidth": 2, "edgecolor": "white"},
            pctdistance=0.75, textprops={"fontsize": 9},
        )
        for at in autotexts:
            at.set_fontsize(8); at.set_color("white"); at.set_fontweight("bold")

        total = sum(sizes)
        ax.set_title(reverse_persian(f"توزیع مطالعه — {user_name}\nمجموع: {total} دقیقه"),
                     fontsize=13, fontweight="bold", color=COLORS["text"], pad=20)
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=COLORS["bg"], dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf

    # ── نمودار خطی ۳۰ روزه ───────────────────────────────────────────────
    def monthly_trend_chart(
        self,
        day_data: dict[date, int],
        goal_minutes: int = 120,
        user_name: str = "کاربر",
    ) -> io.BytesIO:
        import matplotlib.pyplot as plt
        import numpy as np
        from scipy.ndimage import uniform_filter1d

        if not day_data:
            return self._empty_chart(reverse_persian("داده‌ای برای نمایش وجود ندارد"))

        dates = sorted(day_data.keys())
        minutes = [day_data[d] for d in dates]
        labels = [_jalali_date_label(d) for d in dates]
        x = np.arange(len(dates))

        fig, ax = plt.subplots(figsize=(14, 6), dpi=120)
        fig.patch.set_facecolor(COLORS["bg"])
        ax.set_facecolor(COLORS["surface"])

        ax.fill_between(x, minutes, alpha=0.15, color=COLORS["primary"])
        ax.plot(x, minutes, color=COLORS["primary"], linewidth=2.5,
                marker="o", markersize=4, zorder=4,
                label=reverse_persian("مطالعه روزانه"))

        if len(minutes) >= 7:
            moving_avg = uniform_filter1d(minutes, size=7)
            ax.plot(x, moving_avg, color=COLORS["secondary"], linewidth=2,
                    linestyle="--", alpha=0.8,
                    label=reverse_persian("میانگین متحرک ۷ روزه"))

        ax.axhline(y=goal_minutes, color=COLORS["accent"], linestyle=":",
                   linewidth=1.5, alpha=0.7,
                   label=reverse_persian(f"هدف: {goal_minutes} دق"))

        step = max(1, len(dates) // 10)
        ax.set_xticks(x[::step])
        ax.set_xticklabels(labels[::step], fontsize=8, rotation=30)
        ax.set_ylabel(reverse_persian("دقیقه"), fontsize=10, color=COLORS["muted"])
        ax.yaxis.grid(True, color=COLORS["grid"], zorder=0)
        ax.set_axisbelow(True)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_title(reverse_persian(f"روند مطالعه ۳۰ روزه — {user_name}"),
                     fontsize=13, fontweight="bold", color=COLORS["text"], pad=15)
        ax.legend(loc="upper left", framealpha=0.9, fontsize=9)

        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=COLORS["bg"], dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf

    # ── نقشه گرمایی فعالیت ───────────────────────────────────────────────
    def study_heatmap(
        self,
        day_data: dict[date, int],
        user_name: str = "کاربر",
    ) -> io.BytesIO:
        import matplotlib.pyplot as plt
        import matplotlib.colors as mcolors
        import numpy as np

        if not day_data:
            return self._empty_chart(reverse_persian("داده‌ای وجود ندارد"))

        end = date.today()
        start = end - timedelta(days=83)
        all_dates = [start + timedelta(days=i) for i in range(84)]

        grid = np.zeros((7, 12))
        for i, d in enumerate(all_dates):
            week = i // 7
            if week < 12:
                grid[d.weekday(), week] = day_data.get(d, 0)

        fig, ax = plt.subplots(figsize=(13, 4), dpi=120)
        fig.patch.set_facecolor(COLORS["bg"])
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "study", ["#EBEDF0","#C6E48B","#40C463","#30A14E","#216E39"]
        )
        im = ax.imshow(grid, cmap=cmap, aspect="auto", vmin=0, vmax=240)
        day_labels = ["دوش","سه","چهار","پنج","جمع","شنبه","یکش"]
        ax.set_yticks(range(7))
        ax.set_yticklabels([reverse_persian(d) for d in day_labels], fontsize=8)
        ax.set_xticks([])
        plt.colorbar(im, ax=ax, label=reverse_persian("دقیقه"), shrink=0.8)
        ax.set_title(reverse_persian(f"نقشه فعالیت مطالعه — {user_name}"),
                     fontsize=13, fontweight="bold", color=COLORS["text"], pad=10)
        plt.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=COLORS["bg"], dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _empty_chart(self, message: str) -> io.BytesIO:
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        fig.patch.set_facecolor(COLORS["bg"])
        ax.text(0.5, 0.5, message, ha="center", va="center",
                fontsize=14, color=COLORS["muted"], transform=ax.transAxes)
        ax.axis("off")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        plt.close(fig)
        buf.seek(0)
        return buf