from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import jdatetime
import os

_FONT = "Helvetica"
try:
    _fp = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "Vazirmatn.ttf")
    if os.path.exists(_fp):
        pdfmetrics.registerFont(TTFont("Vazirmatn", _fp))
        _FONT = "Vazirmatn"
except Exception:
    pass


def _fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(str(text)))


def generate_weekly_pdf(sessions: list, user_name: str) -> BytesIO:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2.5 * cm, leftMargin=2.5 * cm,
        topMargin=2.5 * cm, bottomMargin=2 * cm,
    )

    def st(name, size, align=TA_RIGHT, color="#212529", space_after=6):
        return ParagraphStyle(
            name, fontName=_FONT, fontSize=size,
            alignment=align, textColor=colors.HexColor(color),
            spaceAfter=space_after, leading=size * 1.7,
        )

    title_s   = st("title",   20, TA_CENTER, "#01696f", 4)
    sub_s     = st("sub",     10, TA_CENTER, "#6C757D", 14)
    section_s = st("section", 12, TA_RIGHT,  "#01696f", 6)
    row_s     = st("row",      9, TA_RIGHT,  "#333333", 3)
    footer_s  = st("footer",   8, TA_CENTER, "#6C757D", 0)

    week_num  = jdatetime.date.today().isocalendar()[1]
    today_str = jdatetime.date.today().strftime("%Y/%m/%d")
    total_m   = sum(s.duration_minutes for s in sessions)
    hours, mins = divmod(total_m, 60)

    HR = HRFlowable(width="100%", thickness=1,
                    color=colors.HexColor("#E9ECEF"), spaceAfter=10)

    story = [
        Paragraph(_fa("StudyBot Pro"), title_s),
        Paragraph(_fa(f"گزارش هفتگی  |  هفته {week_num}  |  {today_str}"), sub_s),
        HR,
        Paragraph(_fa(f"کاربر:  {user_name}"), row_s),
        Paragraph(_fa(f"مجموع مطالعه:  {hours} ساعت و {mins} دقیقه"), row_s),
        Paragraph(_fa(f"تعداد جلسات:  {len(sessions)}"), row_s),
        Spacer(1, 0.5 * cm),
        HR,
        Paragraph(_fa("خلاصه درس‌ها"), section_s),
        Spacer(1, 0.15 * cm),
    ]

    subject_stats: dict = {}
    for sess in sessions:
        subject_stats[sess.subject] = subject_stats.get(sess.subject, 0) + sess.duration_minutes

    for subject, m in sorted(subject_stats.items(), key=lambda x: x[1], reverse=True):
        h, mn = divmod(m, 60)
        pct = round(m / total_m * 100) if total_m else 0
        bar_str = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        time_str = f"{h} ساعت {mn} دقیقه" if h > 0 else f"{mn} دقیقه"
        story.append(
            Paragraph(_fa(f"{subject}  :  {time_str}  ({pct}%)   {bar_str}"), row_s)
        )

    story += [
        Spacer(1, 0.5 * cm),
        HR,
        Paragraph(_fa("جزئیات جلسات"), section_s),
        Spacer(1, 0.15 * cm),
    ]

    for sess in sessions:
        try:
            jdate = jdatetime.datetime.fromgregorian(
                datetime=sess.session_date).strftime("%Y/%m/%d")
        except Exception:
            jdate = str(sess.session_date)[:10]
        notes = (sess.notes or "---")[:45]
        h2, mn2 = divmod(sess.duration_minutes, 60)
        dur_str = f"{h2} ساعت {mn2} دقیقه" if h2 > 0 else f"{mn2} دقیقه"
        story.append(
            Paragraph(_fa(f"[{jdate}]   {sess.subject}   —   {dur_str}   |   {notes}"), row_s)
        )

    story += [
        Spacer(1, 1 * cm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#DEE2E6")),
        Spacer(1, 0.2 * cm),
        Paragraph(_fa(f"این گزارش توسط StudyBot Pro تولید شده است  |  {today_str}"), footer_s),
    ]

    doc.build(story)
    buf.seek(0)
    return buf