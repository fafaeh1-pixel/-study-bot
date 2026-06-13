"""
charts/persian_font.py
مدیریت فونت فارسی برای نمودارها — دانلود و کش Vazirmatn
"""
import urllib.request
from pathlib import Path
from loguru import logger

FONTS_DIR = Path(__file__).parent / "fonts"
FONT_PATH = FONTS_DIR / "Vazirmatn-Regular.ttf"
FONT_BOLD_PATH = FONTS_DIR / "Vazirmatn-Bold.ttf"

FONT_URLS = {
    "Vazirmatn-Regular.ttf": (
        "https://github.com/rastikerdar/vazirmatn/raw/master/"
        "fonts/ttf/Vazirmatn-Regular.ttf"
    ),
    "Vazirmatn-Bold.ttf": (
        "https://github.com/rastikerdar/vazirmatn/raw/master/"
        "fonts/ttf/Vazirmatn-Bold.ttf"
    ),
}


def ensure_persian_fonts() -> bool:
    """اطمینان از وجود فونت فارسی؛ در صورت نبود دانلود می‌کند."""
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True
    for filename, url in FONT_URLS.items():
        dest = FONTS_DIR / filename
        if dest.exists():
            continue
        try:
            logger.info(f"دانلود فونت {filename}...")
            urllib.request.urlretrieve(url, dest)
            logger.info(f"✅ {filename} دانلود شد.")
        except Exception as exc:
            logger.warning(f"⚠️ دانلود {filename} ناموفق: {exc}")
            all_ok = False
    return all_ok


def setup_matplotlib_persian() -> None:
    """پیکربندی Matplotlib برای نمایش صحیح فارسی."""
    import matplotlib
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")

    if FONT_PATH.exists():
        fm.fontManager.addfont(str(FONT_PATH))
        if FONT_BOLD_PATH.exists():
            fm.fontManager.addfont(str(FONT_BOLD_PATH))
        plt.rcParams.update({
            "font.family": "Vazirmatn",
            "axes.unicode_minus": False,
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#F8F9FA",
            "grid.color": "#E0E0E0",
            "grid.linestyle": "--",
            "grid.alpha": 0.7,
        })
    else:
        plt.rcParams.update({"axes.unicode_minus": False})


def reverse_persian(text: str) -> str:
    """آماده‌سازی متن فارسی برای Matplotlib."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        return " ".join(text.split()[::-1])