"""Visual card generator for IDX analysis — candlestick chart + analysis card image."""
import os
import logging
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Paths ──
OUTPUT_DIR = "/tmp/vilona_cards"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Colors ──
BG_DARK = (18, 18, 30)
CARD_BG = (25, 25, 45)
GREEN = (0, 200, 83)
RED = (255, 82, 82)
YELLOW = (255, 193, 7)
WHITE = (255, 255, 255)
LIGHT_GRAY = (180, 180, 200)
DIM = (120, 120, 150)
ACCENT = (64, 64, 144)

# ── Fonts ──
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def _font(size: int, bold=False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


# ── Candlestick Chart ──

def generate_chart(klines, symbol: str) -> str:
    """Generate candlestick chart, return file path."""
    if not klines or len(klines) < 10:
        return ""

    df = pd.DataFrame([
        {
            "Date": k.timestamp if hasattr(k, "timestamp") else datetime.now() - timedelta(days=len(klines) - i),
            "Open": float(k.open),
            "High": float(k.high),
            "Low": float(k.low),
            "Close": float(k.close),
            "Volume": int(k.volume),
        }
        for i, k in enumerate(klines[-60:])  # last 60 bars
    ])
    df.set_index("Date", inplace=True)
    df.sort_index(inplace=True)

    # Calculate EMAs
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()

    # Style
    mc = mpf.make_marketcolors(
        up="#00c853", down="#ff5252",
        edge="inherit", wick="inherit",
        volume="in", inherit=True,
    )
    s = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor="#12121e",
        figcolor="#12121e",
        gridcolor="#2a2a4a",
        gridstyle=":",
        y_on_right=False,
    )

    apds = [
        mpf.make_addplot(df["EMA9"], color="#64b5f6", width=0.7),
        mpf.make_addplot(df["EMA21"], color="#ffb74d", width=0.7),
    ]

    path = os.path.join(OUTPUT_DIR, f"{symbol}_chart.png")
    fig, axes = mpf.plot(
        df,
        type="candle",
        style=s,
        volume=True,
        addplot=apds,
        figsize=(6, 3.5),
        returnfig=True,
        savefig=dict(fname=path, dpi=130, bbox_inches="tight"),
        warn_too_much_data=200,
    )
    plt.close(fig)
    return path


# ── Analysis Card ──

def generate_card(
    symbol: str,
    price: float,
    change: float,
    tech_score: int,
    tech_reasons: list,
    funda_text: str,
    flow_text: str,
    signal_text: str,
    signal_emoji: str,
    final_score: int,
    chart_path: str = "",
) -> str:
    """Generate a full analysis card image, return file path."""
    W, H = 800, 1100
    img = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # ── Header bar ──
    draw.rectangle([0, 0, W, 85], fill=CARD_BG)
    draw.rectangle([0, 85, W, 88], fill=ACCENT)  # accent line

    change_color = GREEN if change >= 0 else RED
    change_sign = "+" if change >= 0 else ""

    font_lg = _font(32, bold=True)
    font_md = _font(18, bold=True)
    font_sm = _font(14)
    font_xs = _font(11)

    # Logo placeholder
    draw.ellipse([20, 22, 60, 62], fill=ACCENT)
    draw.text((25, 32), "V", fill=WHITE, font=_font(28, bold=True))

    # Symbol + price
    draw.text((75, 20), symbol.upper(), fill=WHITE, font=font_lg)
    draw.text((75, 55), f"Rp{price:,.0f}", fill=LIGHT_GRAY, font=_font(16))

    # Change %
    change_text = f"{change_sign}{change:.1f}%"
    draw.text((W - 160, 25), change_text, fill=change_color, font=_font(28, bold=True))

    # Arrow
    arrow = "▲" if change >= 0 else "▼"
    draw.text((W - 80, 50), arrow, fill=change_color, font=_font(24))

    # ── Chart ──
    y_chart_top = 105
    chart_y = y_chart_top

    if chart_path and os.path.exists(chart_path):
        try:
            chart_img = Image.open(chart_path).convert("RGB")
            chart_w, chart_h = chart_img.size
            # Scale to fit card width
            new_w = W - 40
            new_h = int(chart_h * (new_w / chart_w))
            chart_img = chart_img.resize((new_w, new_h), Image.LANCZOS)
            img.paste(chart_img, (20, chart_y))
            chart_y += new_h + 5
        except Exception as e:
            logger.warning(f"Chart paste failed: {e}")
            chart_y += 10

    y = chart_y + 10

    # ── Sections ──

    def section_header(text, y_pos):
        draw.rectangle([20, y_pos, W - 20, y_pos + 30], fill=CARD_BG)
        draw.text((30, y_pos + 5), text, fill=LIGHT_GRAY, font=_font(13, bold=True))
        return y_pos + 38

    def stat_row(text, y_pos, color=WHITE):
        draw.text((35, y_pos), f"• {text}", fill=color, font=font_sm)
        return y_pos + 22

    # 1. Technical
    y = section_header("📊 TEKNIKAL", y)
    for r in tech_reasons[:3]:
        y = stat_row(r, y, LIGHT_GRAY)

    # Score bar
    bar_x, bar_y = 35, y + 5
    bar_w = W - 80
    bar_h = 12
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=6, fill=(40, 40, 70))
    score_fill = GREEN if tech_score >= 7 else (YELLOW if tech_score >= 5 else RED)
    fill_w = int(bar_w * tech_score / 10)
    if fill_w > 0:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=6, fill=score_fill)
    draw.text((bar_x + bar_w + 8, bar_y - 2), f"{tech_score}/10", fill=score_fill, font=font_sm)
    y = bar_y + 20

    # 2. Fundamental
    y = section_header("🏢 FUNDAMENTAL", y + 5)
    for line in funda_text.split("\n")[:4]:
        line = line.strip()
        if line:
            y = stat_row(line, y, LIGHT_GRAY)

    # 3. Foreign Flow
    y = section_header("🏦 FOREIGN FLOW", y + 5)
    for line in flow_text.split("\n")[:3]:
        line = line.strip()
        if line:
            y = stat_row(line, y, LIGHT_GRAY)

    # 4. Signal Banner
    y += 10
    signal_bg = GREEN if final_score >= 7 else (YELLOW if final_score >= 5 else RED)
    draw.rounded_rectangle([30, y, W - 30, y + 60], radius=10, fill=(*CARD_BG, 0), outline=signal_bg, width=2)
    draw.text((50, y + 12), f"{signal_emoji} SIGNAL: {signal_text}", fill=signal_bg, font=_font(22, bold=True))
    draw.text((50, y + 38), f"Score: {final_score}/10", fill=LIGHT_GRAY, font=font_sm)
    y += 75

    # ── Footer ──
    draw.line([20, y, W - 20, y], fill=ACCENT, width=1)
    y += 8
    draw.text((25, y), "Powered by Vilona Saham AI", fill=DIM, font=font_xs)
    now_str = datetime.now().strftime("%d %b %Y %H:%M WIB")
    draw.text((W - 160, y), now_str, fill=DIM, font=font_xs)
    y += 16
    draw.text((25, y), "Disclaimer: Bukan saran investasi. Selalu lakukan riset sendiri.", fill=DIM, font=_font(10))

    # Save
    path = os.path.join(OUTPUT_DIR, f"{symbol}_card.png")
    img.save(path, quality=92)
    logger.info(f"Card saved: {path}")

    # Cleanup chart temp
    if chart_path and os.path.exists(chart_path):
        try:
            os.remove(chart_path)
        except Exception:
            pass

    return path
