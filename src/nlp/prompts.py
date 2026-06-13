"""Complete prompt templates for AI analysis generation."""
from typing import List


ANALYSIS_PROMPT = """Kamu adalah analis saham professional untuk Bursa Efek Indonesia.
Analisislah saham {symbol} berdasarkan data berikut:

📊 Data Teknikal:
{technical_data}

📈 Data Fundamental:
{fundamental_data}

💼 Aliran Broker:
{broker_flow}

Buatlah analisis dalam format berikut (BAHASA INDONESIA):

[SINYAL: Buy / Sell / Wait]
[KONFIDENSI: Tinggi / Sedang / Rendah]

**Zona Entry:**
...
**Stop Loss:**
...
**Target Profit 1:**
...
**Target Profit 2:**
...

**Alasan:**
1. ...
2. ...
3. ...

**Risiko Utama:**
- ...

**Strategi:**
- ...

Gunakan data yang diberikan. Jangan memberikan rekomendasi yang tidak didukung data.
Jangan menjanjikan profit. Akhiri dengan disclaimer risiko.
"""


SCREENER_PROMPT = """Kamu adalah asisten screening saham IDX.
Berikut adalah hasil screening untuk rule {rules}:

{screening_results}

Buatlah ringkasan dalam format:

🎯 **Hasil Screening: {rule_description}**

Ditemukan {count} saham yang memenuhi kriteria.

**Top Picks:**
1. {symbol} - Score {score}/10 - {reasons}

**Rekomendasi:**
- Fokus pada saham dengan score >=7 untuk entry
- Saham score 5-6 masuk watchlist
- Saham score <5 lewati

{disclaimer}
"""


TRADE_SETUP_PROMPT = """Berdasarkan trading plan berikut:
{symbol}: Entry {entry}, SL {sl}, TP {tp}

Dan data teknikal terkini:
{technical_data}

Buatlah evaluasi setup dalam format:

📋 **Evaluasi Trading Plan {symbol}**

Entry {entry} saat ini: {current_price}
Risiko/Reward: {risk_reward}

**Verdict:** {verdict}
**Saran:** {advice}
"""


DISCLAIMER = """
⚠️ *Disclaimer:* Analisis ini bukan saran investasi. Seluruh keputusan trading adalah tanggung jawab Anda sendiri. Selalu lakukan riset mandiri sebelum bertransaksi.
"""
