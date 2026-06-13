"""
Professional landing page for Vilona Saham — IDX AI Trading Bot.
Serves at https://botidx.aitradepulse.com
"""
LANDING_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vilona Saham — AI Co-Pilot Trading IDX</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',system-ui,-apple-system,sans-serif;background:#0a0e17;color:#e2e8f0;line-height:1.6}
.container{max-width:1100px;margin:0 auto;padding:0 24px}
.hero{text-align:center;padding:100px 0 60px;background:linear-gradient(180deg,#0f172a 0%,#0a0e17 100%)}
.hero h1{font-size:48px;font-weight:800;background:linear-gradient(135deg,#3b82f6,#8b5cf6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:16px}
.hero p{font-size:20px;color:#94a3b8;max-width:700px;margin:0 auto 32px}
.cta{display:inline-block;padding:16px 40px;background:linear-gradient(135deg,#3b82f6,#6366f1);color:#fff;border-radius:12px;font-size:18px;font-weight:700;text-decoration:none;transition:transform .2s,box-shadow .2s}
.cta:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(59,130,246,.4)}
.stats{display:flex;justify-content:center;gap:60px;padding:60px 0;text-align:center}
.stat h3{font-size:36px;font-weight:800;color:#3b82f6}.stat p{color:#94a3b8;margin-top:4px}
.section{padding:80px 0;text-align:center}
.section h2{font-size:32px;font-weight:700;margin-bottom:12px;color:#f1f5f9}
.section .subtitle{color:#94a3b8;margin-bottom:48px;font-size:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px;text-align:left}
.card{background:#1e293b;border-radius:16px;padding:32px;border:1px solid #334155;transition:border-color .3s}
.card:hover{border-color:#3b82f6}
.card .icon{font-size:32px;margin-bottom:16px}
.card h3{font-size:20px;font-weight:700;margin-bottom:8px;color:#f1f5f9}
.card p{color:#94a3b8;font-size:15px}
.features{background:#0f172a}
.pricing{background:#0a0e17}
.price-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:24px;max-width:900px;margin:0 auto}
.price-card{background:#1e293b;border-radius:16px;padding:40px 24px;border:1px solid #334155;text-align:center;transition:border-color .3s,transform .2s}
.price-card:hover{border-color:#3b82f6;transform:translateY(-4px)}
.price-card.featured{border-color:#3b82f6;background:linear-gradient(180deg,#1e293b,#0f2744)}
.price-card h3{font-size:24px;margin-bottom:8px}
.price-card .price{font-size:40px;font-weight:800;color:#3b82f6;margin:16px 0}
.price-card .price span{font-size:16px;color:#94a3b8;font-weight:400}
.price-card ul{list-style:none;text-align:left;margin:24px 0}
.price-card ul li{padding:8px 0;color:#94a3b8;font-size:14px}
.price-card ul li:before{content:"✓ ";color:#10b981;font-weight:700}
.price-card .btn{display:inline-block;padding:12px 32px;background:#3b82f6;color:#fff;border-radius:8px;font-weight:700;text-decoration:none;margin-top:16px;transition:background .3s}
.price-card .btn:hover{background:#2563eb}
.footer{text-align:center;padding:40px 0;color:#64748b;font-size:14px;border-top:1px solid #1e293b}
.footer a{color:#3b82f6;text-decoration:none}
@media(max-width:768px){.hero h1{font-size:32px}.stats{gap:30px}.stat h3{font-size:28px}}
</style>
</head>
<body>

<section class="hero">
<div class="container">
<h1>AI Co-Pilot untuk Trader Saham IDX</h1>
<p>Satu-satunya platform yang menggabungkan TradingView chart, AI insight, dan Bandar Flow dalam 10 detik. Gak perlu hafal 300 command — cukup ketik natural.</p>
<a href="https://t.me/sahamidx_bot" class="cta">🚀 Coba Gratis di Telegram</a>
</div>
<div class="stats container">
<div class="stat"><h3>17</h3><p>Fitur AI</p></div>
<div class="stat"><h3>11</h3><p>Sektor Forecast</p></div>
<div class="stat"><h3>95.2%</h3><p>Akurasi Event AI</p></div>
<div class="stat"><h3>7.530</h3><p>Hari Data IHSG</p></div>
</div>
</section>

<section class="section features">
<div class="container">
<h2>Kenapa Vilona Saham?</h2>
<p class="subtitle">AI-powered analysis yang gak bisa lo dapetin di bot saham lain</p>
<div class="grid">
<div class="card">
<div class="icon">📊</div>
<h3>Analisa Multi-Dimensi</h3>
<p>Teknikal + Fundamental + Foreign Flow + News — semua dalam satu perintah natural. Cukup ketik "analisa TLKM".</p>
</div>
<div class="card">
<div class="icon">🎰</div>
<h3>Bandarmology Engine</h3>
<p>Deteksi akumulasi & distribusi bandar asing real-time. Lihat siapa yang lagi beli dan jual di pasar.</p>
</div>
<div class="card">
<div class="icon">🧠</div>
<h3>AI Event Classifier</h3>
<p>Klasifikasi otomatis berita korporat — 11 kategori event dengan akurasi 95.2%. Dividen, Buyback, M&A, IPO & more.</p>
</div>
<div class="card">
<div class="icon">📈</div>
<h3>Sector Forecast 7 Hari</h3>
<p>Prediksi volatilitas 11 sektor IDX untuk 7 hari ke depan. Model AI: TFT, NHITS, NBEATSx, LSTM.</p>
</div>
<div class="card">
<div class="icon">⏱</div>
<h3>Backtest Engine</h3>
<p>Validasi sinyal trading dengan data historis 3 tahun. Win Rate, Sharpe Ratio, Max Drawdown, Alpha vs Buy & Hold.</p>
</div>
<div class="card">
<div class="icon">🔔</div>
<h3>Smart Alerts</h3>
<p>Pantau hingga 200 saham sekaligus. Notifikasi real-time saat harga menyentuh level target lo.</p>
</div>
</div>
</div>
</section>

<section class="section pricing">
<div class="container">
<h2>Harga Transparan</h2>
<p class="subtitle">Mulai gratis. Upgrade kapan aja.</p>
<div class="price-grid">
<div class="price-card">
<h3>🆓 Free</h3>
<div class="price">Rp0<span>/bulan</span></div>
<ul>
<li>5 screening/hari</li>
<li>Watchlist 3 saham</li>
<li>Data delay 15 menit</li>
<li>5 alert aktif</li>
<li>Chart + AI basic</li>
</ul>
<a href="https://t.me/sahamidx_bot" class="btn">Mulai Gratis</a>
</div>
<div class="price-card">
<h3>💎 Pro</h3>
<div class="price">Rp49rb<span>/bulan</span></div>
<ul>
<li>Unlimited screening</li>
<li>Watchlist 10 saham</li>
<li>Real-time data</li>
<li>50 alert</li>
<li>AI trade setup</li>
<li>Unlimited analisa</li>
</ul>
<a href="https://t.me/sahamidx_bot" class="btn">Upgrade Pro</a>
</div>
<div class="price-card featured">
<h3>👑 Premium</h3>
<div class="price">Rp149rb<span>/bulan</span></div>
<ul>
<li>Semua fitur Pro</li>
<li>200 alert</li>
<li>Bandar View + Sentiment</li>
<li>Event Classifier AI</li>
<li>Sector Forecast 11 sektor</li>
<li>Auto-Report Mingguan</li>
<li>Priority AI response</li>
</ul>
<a href="https://t.me/sahamidx_bot" class="btn">Upgrade Premium</a>
</div>
</div>
</div>
</section>

<footer class="footer">
<div class="container">
<p>© 2025 Vilona Saham — AI Co-Pilot Trading IDX. All rights reserved.</p>
<p style="margin-top:8px"><a href="https://t.me/sahamidx_bot">@sahamidx_bot</a> · <a href="https://tripay.co.id">Powered by Tripay</a></p>
</div>
</footer>

</body>
</html>"""
