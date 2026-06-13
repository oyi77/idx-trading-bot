"""
Event Classification Engine — classifies Indonesian financial news into 
11 corporate event categories.

Uses TF-IDF + LogisticRegression trained on tuntun-news dataset.
95.19% test accuracy across 11 classes.

Labels:
  0: Delistings
  1: Dividend Announcements
  2: Expansion (New Factory, Stores, etc)
  3: IPOs
  4: Mergers & Acquisitions
  5: Private Placements
  6: Rights Issues
  7: Share Buybacks
  8: Spin-offs
  9: Stock Splits
  10: Tender Offers
"""
import json
import pickle
import re
from pathlib import Path
from typing import Optional

MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "models" / "event_classifier"

_model = None
_labels = None
_id_to_label = None

# Market impact mapping — how each event typically affects stock price
EVENT_IMPACT = {
    "Dividend Announcements": "🟢 Bullish — sinyal profit & cash flow sehat",
    "Share Buybacks": "🟢 Bullish — manajemen percaya saham undervalued",
    "Expansion (New Factory, Stores, Distribution Center, etc)": "🟢 Bullish — ekspansi bisnis, potensi growth",
    "Stock Splits": "🟡 Neutral — lebih likuid, harga lebih terjangkau retail",
    "Mergers and Acquisitions": "🟢 Bullish — sinergi & efisiensi (tergantung harga akuisisi)",
    "Initial Public Offerings (IPOs)": "🟡 Mixed — peluang vs valuasi mahal",
    "Rights Issues": "🟡 Cenderung Bearish — dilusi kepemilikan existing",
    "Private Placements": "🟡 Mixed — fresh capital tapi potensi dilusi",
    "Tender Offers": "🟢 Bullish — biasanya premium di atas harga pasar",
    "Delistings": "🔴 Bearish — keluar bursa, likuiditas hilang",
    "Spin-offs": "🟡 Mixed — unlock value tapi restrukturisasi",
}

# Class ID to market signal (bullish=1, neutral=0, bearish=-1)
EVENT_SIGNAL = {
    "Dividend Announcements": 1,
    "Share Buybacks": 1,
    "Expansion (New Factory, Stores, Distribution Center, etc)": 1,
    "Mergers and Acquisitions": 1,
    "Tender Offers": 1,
    "Stock Splits": 0,
    "Initial Public Offerings (IPOs)": 0,
    "Private Placements": 0,
    "Spin-offs": 0,
    "Rights Issues": -1,
    "Delistings": -1,
}


def _load_model():
    """Lazy-load the classifier pipeline."""
    global _model, _labels, _id_to_label
    if _model is not None:
        return
    
    model_path = MODEL_DIR / "event_classifier.pkl"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found at {model_path}. Run scripts/train_event_classifier.py first."
        )
    
    with open(model_path, 'rb') as f:
        _model = pickle.load(f)
    
    with open(MODEL_DIR / "labels.json") as f:
        _labels = json.load(f)
    
    with open(MODEL_DIR / "id_to_label.json") as f:
        _id_to_label = json.load(f)


def classify_news(text: str) -> dict:
    """
    Classify a financial news text into one of 11 corporate event categories.
    
    Returns:
        {
            "event": str,          # Event label (e.g., "Dividend Announcements")
            "event_id": int,       # Numeric class ID
            "confidence": float,   # Prediction confidence (0-100)
            "impact": str,         # Market impact description
            "signal": int,         # -1 (bearish), 0 (neutral), 1 (bullish)
            "all_probas": dict     # All class probabilities
        }
    """
    _load_model()
    
    # Clean text
    text = str(text).lower().strip()
    text = re.sub(r'\s+', ' ', text)
    
    # Predict
    event_id = int(_model.predict([text])[0])
    probas = _model.predict_proba([text])[0]
    confidence = max(probas) * 100
    
    event_label = _id_to_label[str(event_id)]
    
    # Get all probabilities
    all_probas = {}
    for i, prob in enumerate(probas):
        all_probas[_id_to_label[str(i)]] = round(prob * 100, 1)
    
    return {
        "event": event_label,
        "event_id": event_id,
        "confidence": round(confidence, 1),
        "impact": EVENT_IMPACT.get(event_label, "Unknown"),
        "signal": EVENT_SIGNAL.get(event_label, 0),
        "all_probas": all_probas,
    }


def classify_batch(texts: list[str]) -> list[dict]:
    """Classify multiple news texts."""
    return [classify_news(t) for t in texts]


def format_event_card(result: dict, headline: str = "") -> str:
    """Format a classification result into a Telegram-friendly card."""
    emoji_map = {1: "🟢", 0: "🟡", -1: "🔴"}
    sig = result["signal"]
    emoji = emoji_map[sig]
    
    lines = [
        f"{emoji} **{result['event']}**",
        f"├ Confidence: {result['confidence']:.0f}%",
        f"├ Impact: {result['impact']}",
    ]
    if headline:
        # Truncate long headlines
        h = headline[:150] + "..." if len(headline) > 150 else headline
        lines.insert(0, f"📰 {h}")
    
    # Top 3 classifications
    sorted_probas = sorted(result["all_probas"].items(), key=lambda x: x[1], reverse=True)
    if len(sorted_probas) > 1:
        alt = [f"{label} ({conf:.0f}%)" for label, conf in sorted_probas[1:4] if conf > 5]
        if alt:
            lines.append(f"├ Alternatif: {' | '.join(alt)}")
    
    lines.append(f"└ Signal: {'Bullish' if sig > 0 else 'Bearish' if sig < 0 else 'Neutral'}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    _load_model()
    demos = [
        "PT Astra Agro Lestari mengumumkan dividen final Rp 250 per saham untuk tahun buku 2025",
        "Bursa Efek Indonesia resmi menghapus pencatatan saham PT Hanson International",
        "Bukalapak akan melakukan IPO dengan target dana Rp 21 triliun",
        "PT Bumi Resources melakukan rights issue 10:1 untuk restrukturisasi utang",
        "Telkomsel akuisisi startup AI senilai Rp 2 triliun",
    ]
    for d in demos:
        r = classify_news(d)
        print(format_event_card(r, d))
        print()
