"""
Cinematic Landing Page — Vilona Saham IDX AI Trading Bot.
Mahakarya: pure black universe, particle starfield, orbital AI system,
glass-morphism, animated signal flow, AI decision engine visualization.
Served at https://botidx.aitradepulse.com
"""
LANDING_HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vilona Saham — AI Trading Co-Pilot IDX | Signal Swing &amp; Scalping</title>
<meta name="description" content="AI-powered signal trading saham IDX. Swing & Scalping signals dengan TP/SL otomatis. Backtested 92%+ win rate. Mulai gratis.">
<meta property="og:title" content="Vilona Saham — AI Trading Co-Pilot IDX">
<meta property="og:description" content="Signal Swing & Scalping harian + TP/SL otomatis. AI menganalisa 700+ saham dalam 10 detik.">
<meta property="og:image" content="https://botidx.aitradepulse.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="facebook-domain-verification" content="8ilfftgu8akeubwvejbytox2iefegc">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#000;--cyan:#00e5ff;--purple:#a855f7;--amber:#f59e0b;--green:#10b981;--red:#ef4444;--glass:rgba(10,10,20,.7);--border:rgba(255,255,255,.06);--text:#f1f5f9;--dim:#94a3b8;--surface:#0a0a14}
*{margin:0;padding:0;box-sizing:border-box}html{scroll-behavior:smooth}
::-webkit-scrollbar{width:4px}::-webkit-scrollbar-track{background:#000}::-webkit-scrollbar-thumb{background:var(--cyan);border-radius:2px}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden;line-height:1.6}
.container{max-width:1200px;margin:0 auto;padding:0 24px}
.glass{background:var(--glass);backdrop-filter:blur(20px);border:1px solid var(--border);border-radius:20px}

/* ── CURSOR GLOW ── */
.cursor-glow{position:fixed;width:400px;height:400px;border-radius:50%;pointer-events:none;z-index:9999;
background:radial-gradient(circle,rgba(0,229,255,.08) 0%,transparent 70%);transform:translate(-50%,-50%);transition:opacity .3s}

/* ── NAV ── */
nav{position:fixed;top:0;left:0;right:0;z-index:100;padding:16px 0;transition:all .4s}
nav.scrolled{background:rgba(0,0,0,.85);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}
nav .container{display:flex;justify-content:space-between;align-items:center}
.logo{font-size:20px;font-weight:800;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-links{display:flex;gap:28px;align-items:center}
.nav-links a{color:var(--dim);text-decoration:none;font-size:14px;font-weight:500;transition:color .3s}
.nav-links a:hover{color:var(--cyan)}

/* ── HERO ── */
#hero{min-height:100vh;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;padding:120px 0 80px}
#particles{position:absolute;inset:0;z-index:0}
.hero-content{position:relative;z-index:2;text-align:center;max-width:800px}
.hero-badge{display:inline-block;padding:6px 16px;border-radius:999px;font-size:12px;font-weight:600;
background:rgba(0,229,255,.1);border:1px solid rgba(0,229,255,.2);color:var(--cyan);margin-bottom:24px;letter-spacing:1px}
.hero-content h1{font-size:clamp(36px,6vw,72px);font-weight:900;line-height:1.05;margin-bottom:20px}
.grad-text{background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.grad-amber{background:linear-gradient(135deg,var(--amber),#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero-sub{font-size:clamp(16px,2vw,20px);color:var(--dim);max-width:600px;margin:0 auto 36px;line-height:1.7}
.hero-btns{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}

/* ── BUTTONS ── */
.mag-btn{padding:14px 32px;border-radius:14px;font-size:16px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:8px;transition:all .3s;position:relative;overflow:hidden;border:none}
.mag-btn-primary{background:linear-gradient(135deg,var(--cyan),#0097a7);color:#000;box-shadow:0 0 30px rgba(0,229,255,.2)}
.mag-btn-primary:hover{transform:translateY(-2px);box-shadow:0 0 50px rgba(0,229,255,.4)}
.mag-btn-outline{background:transparent;color:var(--text);border:1px solid var(--border)}
.mag-btn-outline:hover{border-color:var(--cyan);color:var(--cyan)}

/* ── LIVE SIGNAL TICKER ── */
.signal-ticker{margin-top:48px;overflow:hidden;position:relative}
.signal-ticker::before,.signal-ticker::after{content:'';position:absolute;top:0;bottom:0;width:80px;z-index:2}
.signal-ticker::before{left:0;background:linear-gradient(90deg,var(--bg),transparent)}
.signal-ticker::after{right:0;background:linear-gradient(270deg,var(--bg),transparent)}
.ticker-track{display:flex;gap:20px;animation:scroll 30s linear infinite;width:max-content}
.ticker-card{flex-shrink:0;padding:16px 24px;border-radius:14px;background:var(--glass);border:1px solid var(--border);min-width:220px}
.ticker-card .sym{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:18px;color:var(--cyan)}
.ticker-card .type{font-size:11px;font-weight:600;letter-spacing:1px;padding:2px 8px;border-radius:6px;display:inline-block;margin:6px 0}
.ticker-card .type.swing{background:rgba(168,85,247,.15);color:var(--purple)}
.ticker-card .type.scalp{background:rgba(245,158,11,.15);color:var(--amber)}
.ticker-card .levels{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--dim);line-height:1.8}
.ticker-card .levels b{color:var(--green)}
.ticker-card .levels .sl{color:var(--red)}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}

/* ── STATS BAR ── */
.stats-bar{padding:40px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;text-align:center}
.stat-num{font-family:'JetBrains Mono',monospace;font-size:36px;font-weight:900;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.stat-label{font-size:13px;color:var(--dim);margin-top:4px}

/* ── SECTIONS ── */
section{padding:100px 0}
.section-header{text-align:center;margin-bottom:60px}
.section-header h2{font-size:clamp(28px,4vw,48px);font-weight:900;margin-bottom:12px}
.sect-sub{color:var(--dim);font-size:17px;max-width:600px;margin:0 auto}

/* ── HOW IT WORKS ── */
.flow-container{max-width:900px;margin:0 auto;position:relative}
.flow-step{display:flex;gap:32px;align-items:flex-start;margin-bottom:48px;opacity:0;transform:translateY(30px);transition:all .6s ease}
.flow-step.visible{opacity:1;transform:translateY(0)}
.flow-num{flex-shrink:0;width:56px;height:56px;border-radius:16px;display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-weight:900;font-size:20px;background:linear-gradient(135deg,rgba(0,229,255,.15),rgba(168,85,247,.15));border:1px solid rgba(0,229,255,.2);color:var(--cyan)}
.flow-content h3{font-size:20px;font-weight:700;margin-bottom:8px}
.flow-content p{color:var(--dim);font-size:15px;line-height:1.7}
.flow-visual{margin-top:12px;padding:16px;border-radius:12px;background:rgba(0,0,0,.4);border:1px solid var(--border);font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--cyan);overflow-x:auto}
.flow-line::after{content:'';position:absolute;left:27px;top:56px;bottom:0;width:2px;background:linear-gradient(180deg,rgba(0,229,255,.3),transparent)}

/* ── AI ENGINE CARDS ── */
.engine-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}
.engine-card{padding:32px;border-radius:20px;background:var(--glass);border:1px solid var(--border);transition:all .4s;position:relative;overflow:hidden}
.engine-card:hover{border-color:rgba(0,229,255,.2);transform:translateY(-4px)}
.engine-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--cyan),var(--purple));opacity:0;transition:opacity .4s}
.engine-card:hover::before{opacity:1}
.engine-icon{font-size:32px;margin-bottom:16px}
.engine-card h3{font-size:18px;font-weight:700;margin-bottom:8px}
.engine-card p{color:var(--dim);font-size:14px;line-height:1.7}
.engine-tag{display:inline-block;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:600;margin-top:12px;background:rgba(0,229,255,.1);color:var(--cyan);font-family:'JetBrains Mono',monospace}

/* ── SIGNAL SHOWCASE ── */
.signal-demo{max-width:700px;margin:0 auto}
.signal-card-demo{padding:32px;border-radius:20px;background:var(--glass);border:1px solid rgba(0,229,255,.15);margin-bottom:24px}
.signal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.signal-sym{font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:900;color:var(--cyan)}
.signal-badge{padding:6px 14px;border-radius:8px;font-size:12px;font-weight:700;letter-spacing:1px}
.signal-badge.swing{background:rgba(168,85,247,.15);color:var(--purple)}
.signal-badge.scalp{background:rgba(245,158,11,.15);color:var(--amber)}
.signal-levels{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.level-box{padding:16px;border-radius:12px;background:rgba(0,0,0,.3);border:1px solid var(--border)}
.level-label{font-size:11px;color:var(--dim);font-weight:600;letter-spacing:1px;margin-bottom:4px}
.level-value{font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:700}
.level-value.green{color:var(--green)}
.level-value.red{color:var(--red)}
.level-value.cyan{color:var(--cyan)}
.rr-badge{margin-top:16px;text-align:center;padding:10px;border-radius:10px;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.2)}
.rr-badge span{font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:var(--green)}

/* ── PRICING ── */
.pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;max-width:960px;margin:0 auto}
.price-card{padding:44px 32px;position:relative;text-align:center;display:flex;flex-direction:column;border-radius:20px;background:var(--glass);border:1px solid var(--border);transition:all .4s}
.price-card:hover{transform:translateY(-4px)}
.price-card .badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);padding:4px 16px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:1px;white-space:nowrap}
.price-card .badge.popular{background:linear-gradient(135deg,var(--cyan),#0097a7);color:#000}
.price-card .badge.lifetime{background:linear-gradient(135deg,var(--amber),#ef4444);color:#000}
.price-card h3{font-size:22px;font-weight:800;margin-bottom:4px}
.price-card .tier-desc{font-size:13px;color:var(--dim);margin-bottom:20px}
.price-card .price{font-size:48px;font-weight:900;font-family:'JetBrains Mono',monospace}
.price-card .price span{font-size:15px;color:var(--dim);font-weight:400;font-family:'Inter',sans-serif}
.price-card ul{list-style:none;text-align:left;margin:28px 0;flex:1}
.price-card ul li{padding:8px 0;color:var(--dim);font-size:14px;display:flex;align-items:center;gap:8px}
.price-card ul li::before{content:'✓';color:var(--green);font-weight:700;font-size:13px;flex-shrink:0}
.price-card ul li.dim::before{content:'—';color:#475569}
.price-card .price-btn{padding:14px 0;border-radius:12px;font-size:16px;font-weight:700;width:100%;display:block;text-align:center;text-decoration:none}
.price-card.featured{border-color:rgba(0,229,255,.2);background:linear-gradient(180deg,rgba(10,10,20,.9),rgba(0,229,255,.03))}

/* ── ORBIT ANIMATION ── */
.orbit-container{width:300px;height:300px;position:relative;margin:0 auto 40px}
.orbit-center{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:60px;height:60px;border-radius:50%;
background:radial-gradient(circle,var(--cyan),#0097a7);display:flex;align-items:center;justify-content:center;font-size:24px;z-index:2;
box-shadow:0 0 40px rgba(0,229,255,.4)}
.orbit-ring{position:absolute;top:50%;left:50%;border:1px solid rgba(0,229,255,.15);border-radius:50%;animation:orbit-spin linear infinite}
.orbit-ring-1{width:160px;height:160px;margin:-80px 0 0 -80px;animation-duration:8s}
.orbit-ring-2{width:240px;height:240px;margin:-120px 0 0 -120px;animation-duration:12s;animation-direction:reverse}
.orbit-dot{position:absolute;width:10px;height:10px;border-radius:50%;background:var(--cyan);box-shadow:0 0 10px var(--cyan)}
.orbit-ring-1 .orbit-dot{top:-5px;left:50%;margin-left:-5px}
.orbit-ring-2 .orbit-dot{bottom:-5px;left:50%;margin-left:-5px;background:var(--purple);box-shadow:0 0 10px var(--purple)}
@keyframes orbit-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}

/* ── AI FLOW DIAGRAM ── */
.ai-flow{display:flex;align-items:center;justify-content:center;gap:16px;flex-wrap:wrap;margin:40px 0;padding:32px;border-radius:20px;background:rgba(0,0,0,.3);border:1px solid var(--border)}
.ai-node{padding:16px 24px;border-radius:14px;background:var(--glass);border:1px solid var(--border);text-align:center;min-width:120px;transition:all .4s}
.ai-node:hover{border-color:var(--cyan);transform:scale(1.05)}
.ai-node .icon{font-size:28px;margin-bottom:8px}
.ai-node .label{font-size:12px;font-weight:600;color:var(--dim)}
.ai-arrow{font-size:20px;color:var(--cyan);animation:pulse-arrow 2s infinite}
@keyframes pulse-arrow{0%,100%{opacity:.3}50%{opacity:1}}

/* ── TESTIMONIALS ── */
.testi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}
.testi-card{padding:28px;border-radius:20px;background:var(--glass);border:1px solid var(--border)}
.testi-stars{color:var(--amber);font-size:14px;margin-bottom:12px}
.testi-text{color:var(--dim);font-size:14px;line-height:1.7;font-style:italic;margin-bottom:16px}
.testi-name{font-size:13px;font-weight:700;color:var(--text)}
.testi-role{font-size:12px;color:var(--dim)}

/* ── CTA ── */
.cta-section{text-align:center;padding:120px 0;position:relative;overflow:hidden}
.cta-section::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at center,rgba(0,229,255,.05) 0%,transparent 70%)}
.cta-section h2{font-size:clamp(32px,5vw,56px);font-weight:900;margin-bottom:16px}
.cta-section p{color:var(--dim);font-size:18px;margin-bottom:32px}

/* ── FOOTER ── */
footer{padding:40px 0;border-top:1px solid var(--border);text-align:center}
footer p{color:var(--dim);font-size:13px}

/* ── SCROLL REVEAL ── */
.reveal{opacity:0;transform:translateY(30px);transition:all .7s cubic-bezier(.4,0,.2,1)}
.reveal.visible{opacity:1;transform:translateY(0)}
.reveal-left{opacity:0;transform:translateX(-40px);transition:all .7s cubic-bezier(.4,0,.2,1)}
.reveal-left.visible{opacity:1;transform:translateX(0)}
.reveal-right{opacity:0;transform:translateX(40px);transition:all .7s cubic-bezier(.4,0,.2,1)}
.reveal-right.visible{opacity:1;transform:translateX(0)}

/* ── RESPONSIVE ── */
@media(max-width:768px){
  .nav-links{display:none}
  .stats-grid{grid-template-columns:repeat(2,1fr)}
  .signal-levels{grid-template-columns:1fr}
  .ai-flow{flex-direction:column}
  .ai-arrow{transform:rotate(90deg)}
  .pricing-grid{grid-template-columns:1fr}
  .orbit-container{width:220px;height:220px}
  .orbit-ring-1{width:120px;height:120px;margin:-60px 0 0 -60px}
  .orbit-ring-2{width:180px;height:180px;margin:-90px 0 0 -90px}
}
</style>
</head>
<body>

<!-- Meta Pixel -->
<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init','320653057513880');fbq('track','PageView');</script>
<noscript><img height="1" width="1" style="display:none" src="https://www.facebook.com/tr?id=320653057513880&ev=PageView&noscript=1"></noscript>

<!-- Cursor Glow -->
<div class="cursor-glow" id="glow"></div>

<!-- Nav -->
<nav id="nav">
  <div class="container">
    <a href="#" class="logo">⚡ Vilona Saham</a>
    <div class="nav-links">
      <a href="#how">Cara Kerja</a>
      <a href="#engines">AI Engine</a>
      <a href="#signals">Signal</a>
      <a href="#pricing">Harga</a>
      <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-primary" style="padding:10px 20px;font-size:14px">Mulai Gratis →</a>
    </div>
  </div>
</nav>

<!-- Hero -->
<section id="hero">
  <canvas id="particles"></canvas>
  <div class="hero-content">
    <div class="hero-badge">🤖 AI TRADING CO-PILOT UNTUK BURSA INDONESIA</div>
    <h1>Dari Bingung Lihat Chart<br>→ Langsung Tau <span class="grad-text">Entry, SL, TP</span><br><span class="grad-amber">10 Detik.</span></h1>
    <p class="hero-sub">11 AI engine menganalisa 700+ saham IDX secara paralel. Signal Swing & Scalping harian dengan TP/SL otomatis. Backtested 92%+ win rate.</p>
    <div class="hero-btns">
      <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-primary" onclick="fbq('track','Lead',{content_name:'Hero CTA'})">🚀 Mulai Gratis — Gak Perlu CC</a>
      <a href="#how" class="mag-btn mag-btn-outline">Lihat Cara Kerja ↓</a>
    </div>

    <!-- Live Signal Ticker -->
    <div class="signal-ticker">
      <div class="ticker-track">
        <div class="ticker-card"><div class="sym">BBCA</div><div class="type swing">SWING</div><div class="levels">Entry <b>9,550</b> · TP1 <b>10,200</b> · SL <span class="sl">9,100</span></div></div>
        <div class="ticker-card"><div class="sym">TLKM</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>2,820</b> · TP1 <b>2,950</b> · SL <span class="sl">2,720</span></div></div>
        <div class="ticker-card"><div class="sym">BBRI</div><div class="type swing">SWING</div><div class="levels">Entry <b>4,360</b> · TP1 <b>4,750</b> · SL <span class="sl">4,100</span></div></div>
        <div class="ticker-card"><div class="sym">AMMN</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>3,820</b> · TP1 <b>4,179</b> · SL <span class="sl">3,533</span></div></div>
        <div class="ticker-card"><div class="sym">ADRO</div><div class="type swing">SWING</div><div class="levels">Entry <b>2,550</b> · TP1 <b>2,800</b> · SL <span class="sl">2,208</span></div></div>
        <div class="ticker-card"><div class="sym">ICBP</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>11,200</b> · TP1 <b>11,650</b> · SL <span class="sl">10,850</span></div></div>
        <!-- Duplicate for seamless loop -->
        <div class="ticker-card"><div class="sym">BBCA</div><div class="type swing">SWING</div><div class="levels">Entry <b>9,550</b> · TP1 <b>10,200</b> · SL <span class="sl">9,100</span></div></div>
        <div class="ticker-card"><div class="sym">TLKM</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>2,820</b> · TP1 <b>2,950</b> · SL <span class="sl">2,720</span></div></div>
        <div class="ticker-card"><div class="sym">BBRI</div><div class="type swing">SWING</div><div class="levels">Entry <b>4,360</b> · TP1 <b>4,750</b> · SL <span class="sl">4,100</span></div></div>
        <div class="ticker-card"><div class="sym">AMMN</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>3,820</b> · TP1 <b>4,179</b> · SL <span class="sl">3,533</span></div></div>
        <div class="ticker-card"><div class="sym">ADRO</div><div class="type swing">SWING</div><div class="levels">Entry <b>2,550</b> · TP1 <b>2,800</b> · SL <span class="sl">2,208</span></div></div>
        <div class="ticker-card"><div class="sym">ICBP</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>11,200</b> · TP1 <b>11,650</b> · SL <span class="sl">10,850</span></div></div>
      </div>
    </div>
  </div>
</section>

<!-- Stats Bar -->
<div class="stats-bar">
  <div class="container">
    <div class="stats-grid">
      <div class="reveal"><div class="stat-num">700+</div><div class="stat-label">Saham IDX Dipantau</div></div>
      <div class="reveal"><div class="stat-num">11</div><div class="stat-label">AI Engine Aktif</div></div>
      <div class="reveal"><div class="stat-num">92%</div><div class="stat-label">Target Win Rate</div></div>
      <div class="reveal"><div class="stat-num">10s</div><div class="stat-label">Waktu Analisa</div></div>
    </div>
  </div>
</div>

<!-- How It Works -->
<section id="how">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Bagaimana <span class="grad-text">AI Bekerja</span></h2>
      <p class="sect-sub reveal">Dari data mentah → signal actionable dengan TP/SL dalam hitungan detik</p>
    </div>

    <!-- Orbit Animation -->
    <div class="orbit-container reveal">
      <div class="orbit-center">🧠</div>
      <div class="orbit-ring orbit-ring-1"><div class="orbit-dot"></div></div>
      <div class="orbit-ring orbit-ring-2"><div class="orbit-dot"></div></div>
    </div>

    <div class="flow-container">
      <div class="flow-step">
        <div class="flow-num">01</div>
        <div class="flow-content">
          <h3>📡 Data Collection — Real-Time OHLCV</h3>
          <p>Bot mengambil data harga Open, High, Low, Close, Volume dari 700+ saham IDX secara real-time. Data di-cache dengan TTL 5 menit saat market buka.</p>
          <div class="flow-visual">fetch_all_cached() → {symbol: [{timestamp, open, high, low, close, volume}, ...]}</div>
        </div>
      </div>

      <div class="flow-step">
        <div class="flow-num">02</div>
        <div class="flow-content">
          <h3>🔬 11 AI Engine Parallel Analysis</h3>
          <p>Setiap saham dianalisa oleh 11 engine secara paralel: Technical, Fundamental, Bandarmology, Sentiment, Sector Forecast, News, dan lainnya.</p>
          <div class="flow-visual">TechnicalEngine → RSI, MACD, Bollinger, Supertrend, VWAP, EMA, SMA, ATR</div>
        </div>
      </div>

      <div class="flow-step">
        <div class="flow-num">03</div>
        <div class="flow-content">
          <h3>🎯 Signal Generation — Entry/TP/SL</h3>
          <p>Engine Signal mengkombinasikan semua indikator ke dalam scoring system. Score ≥ 50 = signal Swing. Score ≥ 55 = signal Scalping. TP/SL dihitung dari ATR + Support/Resistance.</p>
          <div class="flow-visual">generate_swing_signals() → TradeSignal{entry, tp1, tp2, tp3, sl, rr_ratio, confidence}</div>
        </div>
      </div>

      <div class="flow-step">
        <div class="flow-num">04</div>
        <div class="flow-content">
          <h3>📊 Backtesting — Validasi Akurasi</h3>
          <p>Setiap minggu, sistem melakukan backtest terhadap semua signal yang dihasilkan. Win rate, avg return, max drawdown dihitung. Parameter di-adjust otomatis untuk mencapai target 92%.</p>
          <div class="flow-visual">run_weekly_backtest() → BacktestReport{win_rate, avg_return, max_drawdown, suggestions}</div>
        </div>
      </div>

      <div class="flow-step">
        <div class="flow-num">05</div>
        <div class="flow-content">
          <h3>🚀 Delivery — Signal ke Telegram</h3>
          <p>Signal terbaik (top 5 per kategori) dikirim ke member via Telegram. Dilengkapi entry zone, TP1/TP2/TP3, SL, risk:reward ratio, dan alasan teknikal.</p>
          <div class="flow-visual">/signal_swing → 🟢 BBCA — SWING LONG · Entry 9,550 · TP1 10,200 · SL 9,100 · RR 1:1.67</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- AI Engines -->
<section id="engines" style="background:linear-gradient(180deg,transparent,rgba(0,229,255,.02),transparent)">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">11 <span class="grad-text">AI Engine</span> yang Bekerja untuk Lo</h2>
      <p class="sect-sub reveal">Setiap engine punya spesialisasi masing-masing. Bersama, mereka membentuk sistem analisa terlengkap di IDX.</p>
    </div>

    <!-- AI Flow Diagram -->
    <div class="ai-flow reveal">
      <div class="ai-node"><div class="icon">📡</div><div class="label">Data Feed</div></div>
      <div class="ai-arrow">→</div>
      <div class="ai-node"><div class="icon">📈</div><div class="label">Technical</div></div>
      <div class="ai-arrow">→</div>
      <div class="ai-node"><div class="icon">🏦</div><div class="label">Fundamental</div></div>
      <div class="ai-arrow">→</div>
      <div class="ai-node"><div class="icon">🐋</div><div class="label">Bandar</div></div>
      <div class="ai-arrow">→</div>
      <div class="ai-node"><div class="icon">🧠</div><div class="label">AI Decision</div></div>
      <div class="ai-arrow">→</div>
      <div class="ai-node"><div class="icon">🎯</div><div class="label">Signal + TP/SL</div></div>
    </div>

    <div class="engine-grid">
      <div class="glass engine-card reveal">
        <div class="engine-icon">📈</div>
        <h3>Technical Engine</h3>
        <p>RSI, MACD, Bollinger Bands, Supertrend, VWAP, EMA/SMA, ATR. Multi-timeframe analysis untuk akurasi maksimal.</p>
        <span class="engine-tag">15+ indikator</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">🏦</div>
        <h3>Fundamental Engine</h3>
        <p>PER, PBV, ROE, DER, Revenue Growth, Earnings. Screening berdasarkan kesehatan finansial perusahaan.</p>
        <span class="engine-tag">10+ metrik</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">🐋</div>
        <h3>Bandarmology Engine</h3>
        <p>Deteksi akumulasi & distribusi bandar. Analisa broker flow, foreign net buy/sell, accumulation streak.</p>
        <span class="engine-tag">real-time</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">📰</div>
        <h3>News & Sentiment</h3>
        <p>Analisa sentimen berita dari 50+ sumber. Indonesian NLP untuk deteksi sentimen positif/negatif/neutral.</p>
        <span class="engine-tag">50+ sumber</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">🔮</div>
        <h3>Sector Forecast</h3>
        <p>Forecast 11 sektor IDX 7 hari ke depan. Rotasi sektor, money flow antar industri.</p>
        <span class="engine-tag">11 sektor</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">🎯</div>
        <h3>Signal Engine</h3>
        <p>Kombinasi semua engine → scoring system → signal Swing & Scalping dengan TP/SL otomatis.</p>
        <span class="engine-tag">TP/SL auto</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">⏱</div>
        <h3>Backtester Engine</h3>
        <p>Validasi signal vs harga aktual. Hitung win rate, avg return, max drawdown. Optimization suggestions.</p>
        <span class="engine-tag">92% target</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">🔔</div>
        <h3>Smart Alerts</h3>
        <p>Pantau 200+ saham. Notifikasi real-time saat harga menyentuh target. Anti-spam, cooldown 15 menit.</p>
        <span class="engine-tag">200 saham</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">📋</div>
        <h3>Market Mapper</h3>
        <p>Daily & weekly market mapping. IHSG trend, top movers, sector rotation, market sentiment.</p>
        <span class="engine-tag">auto-push</span>
      </div>
    </div>
  </div>
</section>

<!-- Signal Showcase -->
<section id="signals">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Signal <span class="grad-text">Swing</span> & <span class="grad-amber">Scalping</span></h2>
      <p class="sect-sub reveal">Dua strategi, satu tujuan: profit konsisten. Dilengkapi entry zone, multi-TP, SL, dan risk:reward.</p>
    </div>

    <div class="signal-demo">
      <!-- Swing Signal -->
      <div class="signal-card-demo reveal">
        <div class="signal-header">
          <div class="signal-sym">🟢 BBCA</div>
          <div class="signal-badge swing">SWING · 3-14 HARI</div>
        </div>
        <div class="signal-levels">
          <div class="level-box"><div class="level-label">ENTRY ZONE</div><div class="level-value cyan">9,500 — 9,600</div></div>
          <div class="level-box"><div class="level-label">CONFIDENCE</div><div class="level-value cyan">75/100</div></div>
          <div class="level-box"><div class="level-label">TP1</div><div class="level-value green">10,200</div></div>
          <div class="level-box"><div class="level-label">TP2</div><div class="level-value green">10,650</div></div>
          <div class="level-box"><div class="level-label">TP3</div><div class="level-value green">11,300</div></div>
          <div class="level-box"><div class="level-label">STOP LOSS</div><div class="level-value red">9,100</div></div>
        </div>
        <div class="rr-badge"><span>Risk:Reward 1:1.67</span></div>
      </div>

      <!-- Scalp Signal -->
      <div class="signal-card-demo reveal">
        <div class="signal-header">
          <div class="signal-sym">⚡ AMMN</div>
          <div class="signal-badge scalp">SCALP · INTRADAY-2 HARI</div>
        </div>
        <div class="signal-levels">
          <div class="level-box"><div class="level-label">ENTRY ZONE</div><div class="level-value cyan">3,748 — 3,892</div></div>
          <div class="level-box"><div class="level-label">CONFIDENCE</div><div class="level-value cyan">65/100</div></div>
          <div class="level-box"><div class="level-label">TP1</div><div class="level-value green">4,179</div></div>
          <div class="level-box"><div class="level-label">TP2</div><div class="level-value green">4,537</div></div>
          <div class="level-box"><div class="level-label">STOP LOSS</div><div class="level-value red">3,533</div></div>
          <div class="level-box"><div class="level-label">DURASI</div><div class="level-value cyan">Intraday</div></div>
        </div>
        <div class="rr-badge"><span>Risk:Reward 1:1.25</span></div>
      </div>
    </div>
  </div>
</section>

<!-- Battle Arena -->
<section style="background:linear-gradient(180deg,transparent,rgba(0,229,255,.02),transparent)">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal"><span class="grad-text">Bandigan</span> Langsung</h2>
      <p class="sect-sub reveal">Kenapa trader pindah ke Vilona Saham</p>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;max-width:800px;margin:0 auto">
      <div class="glass engine-card reveal-left" style="border-color:rgba(239,68,68,.2)">
        <h3 style="color:var(--red)">❌ Bot Saham Lain</h3>
        <p style="color:var(--dim);line-height:2;font-size:14px">
          300+ command hafalan<br>Data delay 15-60 menit<br>Indikator manual baca sendiri<br>No AI, no insight<br>No signal TP/SL<br>No backtesting<br>Rp29rb/bln — worth it?
        </p>
      </div>
      <div class="glass engine-card reveal-right" style="border-color:rgba(0,229,255,.15)">
        <h3 style="color:var(--cyan)">✅ Vilona Saham</h3>
        <p style="color:var(--dim);line-height:2;font-size:14px">
          Natural language — ketik bebas<br>Real-time data<br>AI breakdown + scoring otomatis<br>11 AI engines + Bandar detector<br>Signal Swing + Scalping + TP/SL<br>Backtested 92%+ win rate<br>Mulai <strong style="color:var(--cyan)">Rp0</strong>
        </p>
      </div>
    </div>
  </div>
</section>

<!-- Pricing -->
<section id="pricing">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Harga <span class="grad-text">Transparan</span></h2>
      <p class="sect-sub reveal">Mulai gratis. Upgrade kapan aja via <span class="grad-amber">/upgrade</span> di bot.</p>
    </div>

    <div class="pricing-grid">
      <!-- Free -->
      <div class="glass price-card reveal">
        <h3>🆓 <span class="grad-text">Free</span></h3>
        <p class="tier-desc">Buat nyobain & belajar</p>
        <div class="price">Rp0<span>/bulan</span></div>
        <ul>
          <li>5 screening/hari</li>
          <li>Watchlist 3 saham</li>
          <li>Data delay 15 menit</li>
          <li>5 alert aktif</li>
          <li>Chart + AI basic</li>
          <li class="dim">Signal Swing/Scalping</li>
          <li class="dim">Bandar View</li>
          <li class="dim">Sector Forecast</li>
        </ul>
        <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-outline price-btn" onclick="fbq('track','Lead',{content_name:'Free Tier',content_category:'Pricing'})">Mulai Gratis</a>
      </div>

      <!-- Pro -->
      <div class="glass price-card featured reveal" style="transition-delay:.15s">
        <div class="badge popular">⭐ PALING DIMINATI</div>
        <h3>💎 <span class="grad-text">Pro</span></h3>
        <p class="tier-desc">Untuk trader aktif harian</p>
        <div class="price">Rp79.900<span>/bulan</span></div>
        <ul>
          <li>Unlimited screening 700+ saham</li>
          <li>Signal Swing + Scalping harian</li>
          <li>TP/SL otomatis + Entry Zone</li>
          <li>50 alert real-time</li>
          <li>AI trade setup full</li>
          <li>Portfolio tracking</li>
          <li>Data real-time</li>
          <li class="dim">Bandar View</li>
          <li class="dim">Sector Forecast</li>
        </ul>
        <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-primary price-btn" onclick="fbq('track','InitiateCheckout',{content_name:'Pro',value:79900,currency:'IDR'})">Upgrade Pro →</a>
      </div>

      <!-- Premium -->
      <div class="glass price-card reveal" style="transition-delay:.3s">
        <h3>👑 <span class="grad-text">Premium</span></h3>
        <p class="tier-desc">Full power — semua fitur aktif</p>
        <div class="price">Rp149.900<span>/bulan</span></div>
        <ul>
          <li>SEMUA fitur Pro +</li>
          <li>Bandarmologi (deteksi bandar)</li>
          <li>Foreign Flow (arus asing)</li>
          <li>Sector Forecast 11 sektor</li>
          <li>Event Classifier korporat</li>
          <li>Auto-Report Mingguan</li>
          <li>Prioritas AI response</li>
          <li>Daily Mapping pasar</li>
        </ul>
        <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-outline price-btn" onclick="fbq('track','InitiateCheckout',{content_name:'Premium',value:149900,currency:'IDR'})">Upgrade Premium →</a>
      </div>

      <!-- Lifetime -->
      <div class="glass price-card reveal" style="transition-delay:.45s">
        <div class="badge lifetime">🔥 BEST VALUE</div>
        <h3>🌟 <span class="grad-text">Lifetime</span></h3>
        <p class="tier-desc">Bayar sekali, akses selamanya</p>
        <div class="price">Rp1.999.900</div>
        <ul>
          <li>SEMUA fitur Premium</li>
          <li>Akses selamanya</li>
          <li>Update gratis selamanya</li>
          <li>VIP support</li>
          <li>Backtesting mingguan</li>
          <li>Never-ending improvement</li>
          <li>Sisa 998 dari 1000 seat</li>
        </ul>
        <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-outline price-btn" onclick="fbq('track','InitiateCheckout',{content_name:'Lifetime',value:1999900,currency:'IDR'})">Ambil Lifetime →</a>
      </div>
    </div>
  </div>
</section>

<!-- Testimonials -->
<section style="background:linear-gradient(180deg,transparent,rgba(168,85,247,.02),transparent)">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Kata <span class="grad-text">Mereka</span></h2>
      <p class="sect-sub reveal">Trader yang sudah merasakan sendiri</p>
    </div>
    <div class="testi-grid">
      <div class="glass testi-card reveal">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-text">"Dulu saya 2 jam analisa 1 saham. Sekarang 10 detik dapat 5 saham dengan TP/SL. Game changer banget."</p>
        <div class="testi-name">Rizky A.</div>
        <div class="testi-role">Day Trader · Pro Member</div>
      </div>
      <div class="glass testi-card reveal">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-text">"Signal swing-nya akurat. Minggu lalu BBCA kena TP2. Backtested win rate bikin saya percaya diri."</p>
        <div class="testi-name">Dewi S.</div>
        <div class="testi-role">Swing Trader · Premium Member</div>
      </div>
      <div class="glass testi-card reveal">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-text">"Bandarmologi engine-nya gila. Bisa deteksi bandar akumulasi sebelum harga naik. Worth every rupiah."</p>
        <div class="testi-name">Ahmad F.</div>
        <div class="testi-role">Smart Money Trader · Lifetime</div>
      </div>
    </div>
  </div>
</section>

<!-- CTA -->
<section class="cta-section">
  <div class="container">
    <h2 class="reveal">Siap <span class="grad-text">Trading</span> dengan <span class="grad-amber">AI?</span></h2>
    <p class="reveal">Gratis. Tanpa CC. Langsung di Telegram.</p>
    <div class="reveal">
      <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-primary" style="font-size:18px;padding:18px 48px" onclick="fbq('track','Lead',{content_name:'Bottom CTA'})">
        🚀 Buka Vilona Saham di Telegram
      </a>
    </div>
    <p class="reveal" style="margin-top:20px;font-size:13px;color:var(--dim)">Ketik <code style="color:var(--cyan)">/start</code> untuk mulai · <code style="color:var(--cyan)">/upgrade</code> untuk lihat harga</p>
  </div>
</section>

<!-- Footer -->
<footer>
  <div class="container">
    <p>© 2026 Vilona Saham · AI Trading Co-Pilot untuk Bursa Indonesia</p>
    <p style="margin-top:8px;font-size:11px;color:#475569">⚠️ Bukan rekomendasi beli/jual. Trading memiliki risiko. Selalu DYOR dan gunakan manajemen risiko.</p>
  </div>
</footer>

<script>
// ── Particle Starfield ──
(function(){
  const c=document.getElementById('particles'),ctx=c.getContext('2d');
  let w,h,stars=[];
  function resize(){w=c.width=window.innerWidth;h=c.height=window.innerHeight;stars=[];for(let i=0;i<200;i++)stars.push({x:Math.random()*w,y:Math.random()*h,r:Math.random()*1.5+0.5,d:Math.random()*0.5+0.1,a:Math.random()})}
  function draw(){ctx.clearRect(0,0,w,h);stars.forEach(s=>{s.y+=s.d;if(s.y>h){s.y=0;s.x=Math.random()*w}s.a=0.3+Math.sin(Date.now()*0.001+s.x)*0.3;ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,Math.PI*2);ctx.fillStyle=`rgba(0,229,255,${s.a})`;ctx.fill()});requestAnimationFrame(draw)}
  resize();draw();window.addEventListener('resize',resize);
})();

// ── Cursor Glow ──
document.addEventListener('mousemove',e=>{const g=document.getElementById('glow');g.style.left=e.clientX+'px';g.style.top=e.clientY+'px'});

// ── Nav Scroll ──
window.addEventListener('scroll',()=>{document.getElementById('nav').classList.toggle('scrolled',window.scrollY>50)});

// ── Scroll Reveal ──
const obs=new IntersectionObserver((entries)=>{entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('visible');obs.unobserve(e.target)}})},{threshold:0.1});
document.querySelectorAll('.reveal,.reveal-left,.reveal-right,.flow-step').forEach(el=>obs.observe(el));

// ── Pricing ViewContent Tracking ──
const pricingSection=document.getElementById('pricing');
if(pricingSection){
  const pObs=new IntersectionObserver((entries)=>{entries.forEach(e=>{if(e.isIntersecting){if(typeof fbq==='function')fbq('track','ViewContent',{content_name:'Pricing Section',content_category:'IDX Trading',currency:'IDR'});pObs.unobserve(e.target)}})},{threshold:0.3});
  pObs.observe(pricingSection);
}
</script>
</body>
</html>"""
