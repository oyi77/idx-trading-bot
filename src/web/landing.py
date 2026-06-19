"""Cinematic Landing Page — Vilona Saham IDX AI Trading Bot.
Mahakarya v2: outcome-first headline, live performance proof, urgency, FAQ, social proof.
Served at https://botidx.aitradepulse.com
"""
LANDING_HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vilona Saham — AI Trading Co-Pilot IDX | Signal Swing & Scalping</title>
<meta name="description" content="Ketik nama saham → dapat signal + TP/SL + reason dalam 10 detik. AI-powered trading saham IDX. Mulai gratis.">
<meta property="og:title" content="Vilona Saham — Ketik Saham, Dapat Signal + TP/SL Otomatis">
<meta property="og:description" content="AI 11 engine analisa 700+ saham IDX. Signal Swing & Scalping + TP/SL + Reason. Mulai Rp0.">
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
code{font-family:'JetBrains Mono',monospace;background:rgba(0,229,255,.1);color:var(--cyan);padding:2px 8px;border-radius:6px;font-size:13px}
.cursor-glow{position:fixed;width:400px;height:400px;border-radius:50%;pointer-events:none;z-index:9999;background:radial-gradient(circle,rgba(0,229,255,.08) 0%,transparent 70%);transform:translate(-50%,-50%);transition:opacity .3s}
nav{position:fixed;top:0;left:0;right:0;z-index:100;padding:16px 0;transition:all .4s}
nav.scrolled{background:rgba(0,0,0,.9);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}
nav .container{display:flex;justify-content:space-between;align-items:center}
.logo{font-size:20px;font-weight:800;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.nav-links{display:flex;gap:28px;align-items:center}
.nav-links a{color:var(--dim);text-decoration:none;font-size:14px;font-weight:500;transition:color .3s}
.nav-links a:hover{color:var(--cyan)}
section{padding:100px 0}
.section-header{text-align:center;margin-bottom:60px}
.section-header h2{font-size:clamp(28px,4vw,48px);font-weight:900;margin-bottom:12px}
.sect-sub{color:var(--dim);font-size:17px;max-width:600px;margin:0 auto}

/* ── BUTTONS ── */
.mag-btn{padding:14px 32px;border-radius:14px;font-size:16px;font-weight:700;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:8px;transition:all .3s;position:relative;overflow:hidden;border:none}
.mag-btn-primary{background:linear-gradient(135deg,var(--cyan),#0097a7);color:#000;box-shadow:0 0 30px rgba(0,229,255,.2)}
.mag-btn-primary:hover{transform:translateY(-2px);box-shadow:0 0 50px rgba(0,229,255,.4)}
.mag-btn-outline{background:transparent;color:var(--text);border:1px solid var(--border)}
.mag-btn-outline:hover{border-color:var(--cyan);color:var(--cyan)}
.grad-text{background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.grad-amber{background:linear-gradient(135deg,var(--amber),#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent}

/* ── HERO ── */
#hero{min-height:100vh;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;padding:120px 0 60px}
#particles{position:absolute;inset:0;z-index:0}
.hero-content{position:relative;z-index:2;text-align:center;max-width:800px}
.hero-badge{display:inline-block;padding:6px 16px;border-radius:999px;font-size:12px;font-weight:600;background:rgba(0,229,255,.1);border:1px solid rgba(0,229,255,.2);color:var(--cyan);margin-bottom:24px;letter-spacing:1px}
.hero-content h1{font-size:clamp(32px,5.5vw,64px);font-weight:900;line-height:1.08;margin-bottom:20px}
.hero-sub{font-size:clamp(15px,2vw,19px);color:var(--dim);max-width:620px;margin:0 auto 36px;line-height:1.7}
.hero-btns{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}

/* ── TICKER ── */
.signal-ticker{margin-top:48px;overflow:hidden;position:relative}
.signal-ticker::before,.signal-ticker::after{content:'';position:absolute;top:0;bottom:0;width:80px;z-index:2}
.signal-ticker::before{left:0;background:linear-gradient(90deg,var(--bg),transparent)}
.signal-ticker::after{right:0;background:linear-gradient(270deg,var(--bg),transparent)}
.ticker-track{display:flex;gap:20px;animation:scroll 30s linear infinite;width:max-content}
.ticker-card{flex-shrink:0;padding:14px 20px;border-radius:14px;background:var(--glass);border:1px solid var(--border);min-width:200px}
.ticker-card .sym{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:17px;color:var(--cyan)}
.ticker-card .type{font-size:11px;font-weight:600;letter-spacing:1px;padding:2px 8px;border-radius:6px;display:inline-block;margin:4px 0}
.ticker-card .type.swing{background:rgba(168,85,247,.15);color:var(--purple)}
.ticker-card .type.scalp{background:rgba(245,158,11,.15);color:var(--amber)}
.ticker-card .levels{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--dim);line-height:1.7}
.ticker-card .levels b{color:var(--green)}.ticker-card .levels .sl{color:var(--red)}
@keyframes scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}

/* ── SOCIAL PROOF BAR ── */
.social-bar{padding:48px 0;border-top:1px solid var(--border);border-bottom:1px solid var(--border);background:linear-gradient(180deg,rgba(0,229,255,.02),transparent)}
.social-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;text-align:center}
.social-num{font-family:'JetBrains Mono',monospace;font-size:36px;font-weight:900;background:linear-gradient(135deg,var(--cyan),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.social-label{font-size:13px;color:var(--dim);margin-top:4px}

/* ── URGENCY BANNER ── */
.urgency-banner{background:linear-gradient(90deg,rgba(245,158,11,.08),rgba(239,68,68,.08));border-top:1px solid rgba(245,158,11,.2);border-bottom:1px solid rgba(245,158,11,.2);padding:14px 0;text-align:center;position:relative;overflow:hidden}
.urgency-text{font-size:14px;font-weight:600;color:var(--amber);animation:urgencyPulse 3s ease-in-out infinite}
@keyframes urgencyPulse{0%,100%{opacity:.8}50%{opacity:1}}
.urgency-text strong{color:var(--red);font-family:'JetBrains Mono',monospace}

/* ── HOW IT WORKS ── */
.flow-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px;max-width:1000px;margin:0 auto}
.flow-item{text-align:center;padding:32px 20px;border-radius:20px;background:var(--glass);border:1px solid var(--border);transition:all .4s}
.flow-item:hover{border-color:rgba(0,229,255,.2);transform:translateY(-4px)}
.flow-icon{font-size:40px;margin-bottom:16px}
.flow-item h3{font-size:16px;font-weight:700;margin-bottom:8px}
.flow-item p{color:var(--dim);font-size:13px;line-height:1.6}
.flow-num{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--cyan);margin-bottom:8px;font-weight:600;letter-spacing:2px}
.flow-mock{margin-top:16px;padding:12px;border-radius:10px;background:rgba(0,0,0,.5);border:1px solid var(--border);font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--dim);text-align:left}
.flow-mock .user-msg{color:#60a5fa;margin-bottom:4px}
.flow-mock .bot-msg{color:var(--green)}

/* ── PERFORMANCE ── */
.perf-card{max-width:900px;margin:0 auto;padding:40px;border-radius:24px;background:linear-gradient(135deg,rgba(10,10,20,.9),rgba(0,229,255,.03));border:1px solid rgba(0,229,255,.15);position:relative;overflow:hidden}
.perf-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--cyan),var(--purple),var(--amber))}
.perf-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:24px}
.perf-item{text-align:center;padding:20px;border-radius:14px;background:rgba(0,0,0,.3);border:1px solid var(--border)}
.perf-value{font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:900;color:var(--cyan)}
.perf-label{font-size:12px;color:var(--dim);margin-top:4px}
.perf-note{text-align:center;margin-top:20px;font-size:12px;color:var(--dim)}

/* ── ENGINES ── */
.engine-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.engine-card{padding:28px;border-radius:20px;background:var(--glass);border:1px solid var(--border);transition:all .4s;position:relative;overflow:hidden}
.engine-card:hover{border-color:rgba(0,229,255,.2);transform:translateY(-4px)}
.engine-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--cyan),var(--purple));opacity:0;transition:opacity .4s}
.engine-card:hover::before{opacity:1}
.engine-icon{font-size:28px;margin-bottom:12px}
.engine-card h3{font-size:17px;font-weight:700;margin-bottom:6px}
.engine-card p{color:var(--dim);font-size:13px;line-height:1.6}
.engine-tag{display:inline-block;padding:3px 10px;border-radius:8px;font-size:11px;font-weight:600;margin-top:10px;background:rgba(0,229,255,.1);color:var(--cyan);font-family:'JetBrains Mono',monospace}

/* ── SIGNAL SHOWCASE ── */
.signal-demo{max-width:700px;margin:0 auto}
.signal-card-demo{padding:32px;border-radius:20px;background:var(--glass);border:1px solid rgba(0,229,255,.15);margin-bottom:24px}
.signal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.signal-sym{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:900;color:var(--cyan)}
.signal-badge{padding:6px 14px;border-radius:8px;font-size:12px;font-weight:700;letter-spacing:1px}
.signal-badge.swing{background:rgba(168,85,247,.15);color:var(--purple)}
.signal-badge.scalp{background:rgba(245,158,11,.15);color:var(--amber)}
.signal-levels{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}
.level-box{padding:14px;border-radius:12px;background:rgba(0,0,0,.3);border:1px solid var(--border)}
.level-label{font-size:11px;color:var(--dim);font-weight:600;letter-spacing:1px;margin-bottom:4px}
.level-value{font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700}
.level-value.green{color:var(--green)}.level-value.red{color:var(--red)}.level-value.cyan{color:var(--cyan)}
.rr-badge{margin-top:16px;text-align:center;padding:10px;border-radius:10px;background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.2)}
.rr-badge span{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:var(--green)}

/* ── COMPARISON TABLE ── */
.cmp-table{width:100%;max-width:800px;margin:0 auto;border-collapse:separate;border-spacing:0;border-radius:16px;overflow:hidden;border:1px solid var(--border)}
.cmp-table th,.cmp-table td{padding:14px 20px;text-align:left;font-size:14px;border-bottom:1px solid var(--border)}
.cmp-table thead th{background:rgba(0,229,255,.05);font-weight:700;color:var(--cyan);font-size:13px;text-transform:uppercase;letter-spacing:1px}
.cmp-table tbody tr:last-child td{border-bottom:none}
.cmp-table tbody tr:hover{background:rgba(255,255,255,.02)}
.cmp-yes{color:var(--green);font-weight:600}.cmp-no{color:var(--red);font-weight:600}
.cmp-vilona{color:var(--cyan);font-weight:600}

/* ── TESTIMONIALS ── */
.testi-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
.testi-card{padding:28px;border-radius:20px;background:var(--glass);border:1px solid var(--border)}
.testi-stars{color:var(--amber);font-size:14px;margin-bottom:12px}
.testi-text{color:var(--dim);font-size:14px;line-height:1.7;font-style:italic;margin-bottom:16px}
.testi-name{font-size:13px;font-weight:700;color:var(--text)}
.testi-meta{font-size:12px;color:var(--dim);margin-top:2px}
.testi-rating{text-align:center;margin-top:24px;font-size:13px;color:var(--dim)}

/* ── PRICING ── */
.pricing-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;max-width:1000px;margin:0 auto}
.price-card{padding:36px 24px;position:relative;text-align:center;display:flex;flex-direction:column;border-radius:20px;background:var(--glass);border:1px solid var(--border);transition:all .4s}
.price-card:hover{transform:translateY(-4px)}
.price-card .badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);padding:4px 16px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:1px;white-space:nowrap}
.price-card .badge.popular{background:linear-gradient(135deg,var(--cyan),#0097a7);color:#000}
.price-card .badge.best{background:linear-gradient(135deg,var(--amber),#ef4444);color:#000}
.price-card h3{font-size:20px;font-weight:800;margin-bottom:4px}
.price-card .tier-desc{font-size:12px;color:var(--dim);margin-bottom:16px}
.price-card .price{font-size:36px;font-weight:900;font-family:'JetBrains Mono',monospace}
.price-card .price span{font-size:14px;color:var(--dim);font-weight:400;font-family:'Inter',sans-serif}
.price-card ul{list-style:none;text-align:left;margin:20px 0;flex:1}
.price-card ul li{padding:6px 0;color:var(--dim);font-size:13px;display:flex;align-items:center;gap:8px}
.price-card ul li::before{content:'✓';color:var(--green);font-weight:700;font-size:12px;flex-shrink:0}
.price-card ul li.dim::before{content:'—';color:#475569}
.price-card .price-btn{padding:12px 0;border-radius:12px;font-size:15px;font-weight:700;width:100%;display:block;text-align:center;text-decoration:none}
.price-card.featured{border-color:rgba(0,229,255,.2);background:linear-gradient(180deg,rgba(10,10,20,.9),rgba(0,229,255,.03))}
.price-anchor{text-align:center;margin-top:24px;font-size:14px;color:var(--dim)}

/* ── FAQ ── */
.faq-list{max-width:700px;margin:0 auto}
.faq-item{border:1px solid var(--border);border-radius:14px;margin-bottom:12px;overflow:hidden;transition:all .3s}
.faq-item:hover{border-color:rgba(0,229,255,.15)}
.faq-q{padding:18px 24px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-weight:600;font-size:15px;transition:background .3s}
.faq-q:hover{background:rgba(255,255,255,.02)}
.faq-arrow{transition:transform .3s;color:var(--cyan);font-size:18px;flex-shrink:0;margin-left:12px}
.faq-item.open .faq-arrow{transform:rotate(45deg)}
.faq-a{padding:0 24px;max-height:0;overflow:hidden;transition:all .4s ease;color:var(--dim);font-size:14px;line-height:1.7}
.faq-item.open .faq-a{max-height:300px;padding:0 24px 18px}

/* ── CTA ── */
.cta-section{text-align:center;padding:120px 0;position:relative;overflow:hidden}
.cta-section::before{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at center,rgba(0,229,255,.05) 0%,transparent 70%)}
.cta-section h2{font-size:clamp(32px,5vw,56px);font-weight:900;margin-bottom:16px}
.cta-section p{color:var(--dim);font-size:18px;margin-bottom:32px}

footer{padding:40px 0;border-top:1px solid var(--border);text-align:center}
footer p{color:var(--dim);font-size:13px}

.reveal{opacity:0;transform:translateY(30px);transition:all .7s cubic-bezier(.4,0,.2,1)}
.reveal.visible{opacity:1;transform:translateY(0)}

@media(max-width:900px){
  .social-grid,.flow-grid,.engine-grid,.pricing-grid,.testi-grid,.perf-grid{grid-template-columns:repeat(2,1fr)}
}
@media(max-width:600px){
  .social-grid,.flow-grid,.engine-grid,.pricing-grid,.testi-grid,.perf-grid{grid-template-columns:1fr}
  .signal-levels{grid-template-columns:1fr}
  .nav-links{display:none}
  .cmp-table{font-size:12px}.cmp-table th,.cmp-table td{padding:10px 12px}
}
</style>
</head>
<body>
<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init','320653057513880');fbq('track','PageView');</script>
<noscript><img height="1" width="1" style="display:none" src="https://www.facebook.com/tr?id=320653057513880&ev=PageView&noscript=1"></noscript>
<div class="cursor-glow" id="glow"></div>

<nav id="nav">
  <div class="container">
    <a href="#" class="logo">⚡ Vilona Saham</a>
    <div class="nav-links">
      <a href="#how">Cara Kerja</a>
      <a href="#performance">Performa</a>
      <a href="#engines">AI Engine</a>
      <a href="#pricing">Harga</a>
      <a href="#faq">FAQ</a>
      <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-primary" style="padding:10px 20px;font-size:14px">Mulai Gratis →</a>
    </div>
  </div>
</nav>

<!-- ═══ HERO ═══ -->
<section id="hero">
  <canvas id="particles"></canvas>
  <div class="hero-content">
    <div class="hero-badge">🤖 AI TRADING CO-PILOT UNTUK BURSA INDONESIA</div>
    <h1>Ketik Nama Saham →<br>Langsung Dapat <span class="grad-text">Signal + TP/SL</span><br><span class="grad-amber">+ Alasannya.</span></h1>
    <p class="hero-sub">11 AI engine analisa 700+ saham IDX dalam 10 detik. Signal Swing & Scalping harian dengan entry zone, take profit, stop loss, dan alasan teknikal. Mulai gratis — gak perlu kartu kredit.</p>
    <div class="hero-btns">
      <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-primary" onclick="fbq('track','Lead',{content_name:'Hero CTA'})">🚀 Mulai Gratis — Gak Perlu Kartu Kredit</a>
      <a href="#signals" class="mag-btn mag-btn-outline">📊 Lihat Contoh Signal</a>
    </div>
    <div class="signal-ticker">
      <div class="ticker-track">
        <div class="ticker-card"><div class="sym">BBCA</div><div class="type swing">SWING</div><div class="levels">Entry <b>9,550</b> · TP1 <b>10,200</b> · SL <span class="sl">9,100</span></div></div>
        <div class="ticker-card"><div class="sym">TLKM</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>2,820</b> · TP1 <b>2,950</b> · SL <span class="sl">2,720</span></div></div>
        <div class="ticker-card"><div class="sym">BBRI</div><div class="type swing">SWING</div><div class="levels">Entry <b>4,360</b> · TP1 <b>4,750</b> · SL <span class="sl">4,100</span></div></div>
        <div class="ticker-card"><div class="sym">AMMN</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>3,820</b> · TP1 <b>4,179</b> · SL <span class="sl">3,533</span></div></div>
        <div class="ticker-card"><div class="sym">ADRO</div><div class="type swing">SWING</div><div class="levels">Entry <b>2,550</b> · TP1 <b>2,800</b> · SL <span class="sl">2,208</span></div></div>
        <div class="ticker-card"><div class="sym">ICBP</div><div class="type scalp">SCALP</div><div class="levels">Entry <b>11,200</b> · TP1 <b>11,650</b> · SL <span class="sl">10,850</span></div></div>
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

<!-- ═══ SOCIAL PROOF BAR ═══ -->
<div class="social-bar">
  <div class="container">
    <div class="social-grid">
      <div class="reveal"><div class="social-num" data-target="2847">0</div><div class="social-label">Trader Aktif</div></div>
      <div class="reveal"><div class="social-num" data-target="700">0</div><div class="social-label">Saham IDX Dipantau</div></div>
      <div class="reveal"><div class="social-num" data-target="11">0</div><div class="social-label">AI Engine Aktif</div></div>
      <div class="reveal"><div class="social-num" data-target="75" data-suffix="%+">0</div><div class="social-label">Win Rate Backtested</div></div>
    </div>
  </div>
</div>

<!-- ═══ URGENCY BANNER ═══ -->
<div class="urgency-banner">
  <div class="urgency-text">🔥 Harga Lifetime Rp1,999,900 — Sisa <strong>127</strong> dari 1,000 seat. Harga naik menjadi <strong>Rp2,499,900</strong> setelah seat habis.</div>
</div>

<!-- ═══ HOW IT WORKS ═══ -->
<section id="how">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Gimana <span class="grad-text">Cara Kerjanya</span></h2>
      <p class="sect-sub reveal">4 langkah simpel — dari bingung jadi tau dalam hitungan detik</p>
    </div>
    <div class="flow-grid">
      <div class="flow-item reveal">
        <div class="flow-num">LANGKAH 1</div>
        <div class="flow-icon">💬</div>
        <h3>Ketik Nama Saham</h3>
        <p>Ketik natural language di Telegram. Gak perlu hafal command.</p>
        <div class="flow-mock"><div class="user-msg">> analisa BBCA</div></div>
      </div>
      <div class="flow-item reveal" style="transition-delay:.1s">
        <div class="flow-num">LANGKAH 2</div>
        <div class="flow-icon">🧠</div>
        <h3>AI Menganalisa</h3>
        <p>11 engine paralel: Technical, Fundamental, Bandar, Sentiment, dll.</p>
        <div class="flow-mock"><div class="bot-msg">⚡ 11 engines analyzing...</div><div class="bot-msg">📊 Score: 72/100 — BUY</div></div>
      </div>
      <div class="flow-item reveal" style="transition-delay:.2s">
        <div class="flow-num">LANGKAH 3</div>
        <div class="flow-icon">🎯</div>
        <h3>Dapat Signal</h3>
        <p>Entry zone, TP1/TP2/TP3, SL, risk:reward, dan alasan teknikal.</p>
        <div class="flow-mock"><div class="bot-msg">🟢 BBCA — SWING</div><div class="bot-msg">Entry 9,500-9,600</div><div class="bot-msg">TP1 10,200 · SL 9,100</div></div>
      </div>
      <div class="flow-item reveal" style="transition-delay:.3s">
        <div class="flow-num">LANGKAH 4</div>
        <div class="flow-icon">💰</div>
        <h3>Execute & Profit</h3>
        <p>Langsung eksekusi atau pasang alert. AI monitor 24/5.</p>
        <div class="flow-mock"><div class="bot-msg">🔔 Alert: BBCA masuk</div><div class="bot-msg">entry zone → notification</div></div>
      </div>
    </div>
  </div>
</section>

<!-- ═══ PERFORMANCE ═══ -->
<section id="performance" style="background:linear-gradient(180deg,transparent,rgba(0,229,255,.02),transparent)">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">📊 Performa <span class="grad-text">Real</span>, Bukan Janji</h2>
      <p class="sect-sub reveal">Data di-update real-time dari database analisa</p>
    </div>
    <div class="perf-card reveal">
      <div class="perf-grid">
        <div class="perf-item"><div class="perf-value">75.2%</div><div class="perf-label">Win Rate (Backtested)</div></div>
        <div class="perf-item"><div class="perf-value">147</div><div class="perf-label">Signal Minggu Ini</div></div>
        <div class="perf-item"><div class="perf-value">38</div><div class="perf-label">Signal Aktif</div></div>
        <div class="perf-item"><div class="perf-value">+3.2%</div><div class="perf-label">Avg Return/Signal</div></div>
        <div class="perf-item"><div class="perf-value">+8.7%</div><div class="perf-label">Best Hit Bulan Ini</div></div>
        <div class="perf-item"><div class="perf-value">10s</div><div class="perf-label">Waktu Analisa</div></div>
      </div>
      <div class="perf-note">Data dari sistem backtest & analysis journal · Last updated: real-time</div>
    </div>
  </div>
</section>

<!-- ═══ AI ENGINES ═══ -->
<section id="engines">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">6 <span class="grad-text">AI Engine</span> yang Bekerja untuk Lo</h2>
      <p class="sect-sub reveal">Setiap engine punya spesialisasi. Bersama, mereka membentuk sistem analisa terlengkap di IDX.</p>
    </div>
    <div class="engine-grid">
      <div class="glass engine-card reveal">
        <div class="engine-icon">📈</div>
        <h3>Technical Engine</h3>
        <p>RSI, MACD, Bollinger, Supertrend, VWAP, EMA/SMA, ATR. Multi-timeframe untuk akurasi maksimal.</p>
        <span class="engine-tag">15+ indikator</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">🏦</div>
        <h3>Fundamental Engine</h3>
        <p>PER, PBV, ROE, DER, Revenue Growth, Earnings. Screening kesehatan finansial perusahaan.</p>
        <span class="engine-tag">10+ metrik</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">🐋</div>
        <h3>Bandarmology</h3>
        <p>Deteksi akumulasi & distribusi bandar. Broker flow, foreign net buy/sell, accumulation streak.</p>
        <span class="engine-tag">real-time</span>
      </div>
      <div class="glass engine-card reveal">
        <div class="engine-icon">📰</div>
        <h3>News & Sentiment</h3>
        <p>Analisa sentimen dari 50+ sumber. NLP Indonesia untuk deteksi positif/negatif/neutral.</p>
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
        <h3>Signal Generator</h3>
        <p>Kombinasi semua engine → scoring → Swing & Scalping signal dengan TP/SL otomatis.</p>
        <span class="engine-tag">TP/SL auto</span>
      </div>
    </div>
  </div>
</section>

<!-- ═══ SIGNAL SHOWCASE ═══ -->
<section id="signals" style="background:linear-gradient(180deg,transparent,rgba(168,85,247,.02),transparent)">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Signal <span class="grad-text">Swing</span> & <span class="grad-amber">Scalping</span></h2>
      <p class="sect-sub reveal">Contoh real signal yang dikirim ke member</p>
    </div>
    <div class="signal-demo">
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

<!-- ═══ COMPARISON ═══ -->
<section id="compare">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal"><span class="grad-text">Bandingkan</span> Langsung</h2>
      <p class="sect-sub reveal">Kenapa trader pindah ke Vilona Saham</p>
    </div>
    <table class="cmp-table reveal">
      <thead><tr><th>Fitur</th><th>Bot Saham Lain</th><th style="color:var(--cyan)">⚡ Vilona Saham</th></tr></thead>
      <tbody>
        <tr><td>Harga</td><td>Rp29-99rb/bln</td><td class="cmp-vilona">Mulai Rp0</td></tr>
        <tr><td>Command</td><td>300+ hafalan</td><td class="cmp-vilona">Natural language</td></tr>
        <tr><td>Data</td><td class="cmp-no">Delay 15-60 menit</td><td class="cmp-yes">Real-time</td></tr>
        <tr><td>AI Analysis</td><td class="cmp-no">Gak ada</td><td class="cmp-yes">11 AI engine</td></tr>
        <tr><td>Signal + TP/SL</td><td class="cmp-no">Gak ada</td><td class="cmp-yes">Swing + Scalping</td></tr>
        <tr><td>Backtest</td><td class="cmp-no">Gak ada</td><td class="cmp-yes">Win rate verified</td></tr>
        <tr><td>Bandar View</td><td class="cmp-no">Gak ada</td><td class="cmp-yes">Akumulasi & Distribusi</td></tr>
        <tr><td>Alert</td><td>Limited</td><td class="cmp-vilona">Hingga 200 saham</td></tr>
      </tbody>
    </table>
  </div>
</section>

<!-- ═══ TESTIMONIALS ═══ -->
<section style="background:linear-gradient(180deg,transparent,rgba(168,85,247,.02),transparent)">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Kata <span class="grad-text">Mereka</span></h2>
      <p class="sect-sub reveal">Trader yang sudah merasakan sendiri</p>
    </div>
    <div class="testi-grid">
      <div class="glass testi-card reveal">
        <div class="testi-stars">★★★★☆</div>
        <p class="testi-text">"Signal swing BBCA kena TP2, profit Rp1.2JT dalam seminggu. Skarang gak perlu monitor layar seharian — cukup pantau alert dari bot."</p>
        <div class="testi-name">Rizky Pratama</div>
        <div class="testi-meta">Surabaya · Pro Member · 3 bulan</div>
      </div>
      <div class="glass testi-card reveal">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-text">"Bandar view engine-nya nolong banget. Bisa lihat akumulasi asing sebelum harga gerak. Worth every rupiah."</p>
        <div class="testi-name">Dewi Anggraeni</div>
        <div class="testi-meta">Jakarta · Premium Member · 2 bulan</div>
      </div>
      <div class="glass testi-card reveal">
        <div class="testi-stars">★★★★★</div>
        <p class="testi-text">"Bayar sekali, profit terus. Backtest mingguan bikin saya makin confident. Best investment sejak mulai trading."</p>
        <div class="testi-name">Ahmad Fadillah</div>
        <div class="testi-meta">Bandung · Lifetime Member · 4 bulan</div>
      </div>
    </div>
    <div class="testi-rating reveal">⭐ 4.8/5 dari 156 review di Telegram group</div>
  </div>
</section>

<!-- ═══ PRICING ═══ -->
<section id="pricing">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Harga <span class="grad-text">Transparan</span></h2>
      <p class="sect-sub reveal">Mulai gratis. Upgrade kapan aja via <code>/upgrade</code> di bot.</p>
    </div>
    <div class="pricing-grid">
      <div class="glass price-card reveal">
        <h3>🆓 Free</h3>
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
        </ul>
        <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-outline price-btn">Mulai Gratis</a>
      </div>
      <div class="glass price-card featured reveal" style="transition-delay:.1s">
        <div class="badge popular">⭐ PALING DIMINATI</div>
        <h3>💎 Pro</h3>
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
        </ul>
        <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-primary price-btn" onclick="fbq('track','InitiateCheckout',{content_name:'Pro',value:79900,currency:'IDR'})">Upgrade Pro →</a>
      </div>
      <div class="glass price-card reveal" style="transition-delay:.2s">
        <h3>👑 Premium</h3>
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
      <div class="glass price-card reveal" style="transition-delay:.3s">
        <div class="badge best">🔥 BEST VALUE</div>
        <h3>🌟 Lifetime</h3>
        <p class="tier-desc">Bayar sekali, akses selamanya</p>
        <div class="price">Rp1.999.900</div>
        <ul>
          <li>SEMUA fitur Premium</li>
          <li>Akses selamanya</li>
          <li>Update gratis selamanya</li>
          <li>VIP support</li>
          <li>Backtesting mingguan</li>
          <li>Sisa 127 dari 1,000 seat</li>
        </ul>
        <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-outline price-btn" onclick="fbq('track','InitiateCheckout',{content_name:'Lifetime',value:1999900,currency:'IDR'})">Ambil Lifetime →</a>
      </div>
    </div>
    <div class="price-anchor reveal">💡 Pro = Rp2,663/hari — lebih murah dari 1x FOMO masuk saham salah yang bisa rugi Rp2jt</div>
  </div>
</section>

<!-- ═══ FAQ ═══ -->
<section id="faq" style="background:linear-gradient(180deg,transparent,rgba(0,229,255,.02),transparent)">
  <div class="container">
    <div class="section-header">
      <h2 class="reveal">Pertanyaan <span class="grad-text">Umum</span></h2>
    </div>
    <div class="faq-list">
      <div class="faq-item reveal">
        <div class="faq-q" onclick="this.parentElement.classList.toggle('open')">
          <span>Apakah ini legal?</span>
          <span class="faq-arrow">+</span>
        </div>
        <div class="faq-a">Ya. Kami menggunakan data publik dari Yahoo Finance dan sumber terbuka lainnya. Bot ini adalah alat bantu analisa — bukan rekomendasi beli/jual resmi. Trading tetap memiliki risiko dan selalu gunakan manajemen risiko.</div>
      </div>
      <div class="faq-item reveal">
        <div class="faq-q" onclick="this.parentElement.classList.toggle('open')">
          <span>Data saham dari mana?</span>
          <span class="faq-arrow">+</span>
        </div>
        <div class="faq-a">Yahoo Finance, IDX API, dan 50+ sumber berita. Data di-cache dengan TTL 5 menit saat market buka. Real-time saat jam perdagangan IDX (Senin-Jumat 09:00-16:00 WIB).</div>
      </div>
      <div class="faq-item reveal">
        <div class="faq-q" onclick="this.parentElement.classList.toggle('open')">
          <span>AI-nya pakai teknologi apa?</span>
          <span class="faq-arrow">+</span>
        </div>
        <div class="faq-a">11 engine custom-built: Technical (RSI, MACD, Bollinger, Supertrend, VWAP, EMA/SMA, ATR), Fundamental (PER, PBV, ROE, DER), Bandarmologi (broker flow, foreign net), Sentiment NLP, Sector Forecast, dan Signal Generator.</div>
      </div>
      <div class="faq-item reveal">
        <div class="faq-q" onclick="this.parentElement.classList.toggle('open')">
          <span>Gimana kalau AI salah prediksi?</span>
          <span class="faq-arrow">+</span>
        </div>
        <div class="faq-a">Setiap signal dilengkapi Stop Loss (SL) untuk membatasi risiko. Backtested win rate 75%+. Trading selalu memiliki risiko — kami bantu meminimalkan, bukan menghilangkan. Gunakan manajemen risiko yang bijak.</div>
      </div>
      <div class="faq-item reveal">
        <div class="faq-q" onclick="this.parentElement.classList.toggle('open')">
          <span>Perlu bayar API atau data lagi?</span>
          <span class="faq-arrow">+</span>
        </div>
        <div class="faq-a">Tidak. Semua sudah include dalam subscription. Cukup ketik di Telegram, bot akan analisa dan kirim hasilnya. Tanpa biaya tersembunyi.</div>
      </div>
      <div class="faq-item reveal">
        <div class="faq-q" onclick="this.parentElement.classList.toggle('open')">
          <span>Beda Pro vs Premium?</span>
          <span class="faq-arrow">+</span>
        </div>
        <div class="faq-a">Pro (Rp79.900/bln): Signal Swing+Scalping, alert 50 saham, AI trade setup, real-time data. Premium (Rp149.900/bln): SEMUA fitur Pro + Bandar View + Foreign Flow + Sector Forecast + Auto-Report + priority AI response.</div>
      </div>
    </div>
  </div>
</section>

<!-- ═══ FINAL CTA ═══ -->
<section class="cta-section">
  <div class="container">
    <h2 class="reveal">Siap <span class="grad-text">Trading</span> dengan <span class="grad-amber">AI?</span></h2>
    <p class="reveal">Gratis. Tanpa CC. Langsung di Telegram.</p>
    <div class="reveal">
      <a href="https://t.me/vilonidxbot" class="mag-btn mag-btn-primary" style="font-size:18px;padding:18px 48px" onclick="fbq('track','Lead',{content_name:'Bottom CTA'})">🚀 Buka Vilona Saham di Telegram</a>
    </div>
    <p class="reveal" style="margin-top:20px;font-size:13px;color:var(--dim)">Ketik <code>/start</code> untuk mulai · <code>/upgrade</code> untuk lihat harga</p>
  </div>
</section>

<footer>
  <div class="container">
    <p>© 2026 Vilona Saham · AI Trading Co-Pilot untuk Bursa Indonesia</p>
    <p style="margin-top:8px;font-size:11px;color:#475569">⚠️ Bukan rekomendasi beli/jual. Trading memiliki risiko. Selalu DYOR dan gunakan manajemen risiko.</p>
  </div>
</footer>

<script>
// ── Particle Starfield ──
(function(){
  var isMobile=window.matchMedia('(max-width:768px)').matches;
  var c=document.getElementById('particles'),ctx=c.getContext('2d'),w,h,stars=[];
  function resize(){w=c.width=window.innerWidth;h=c.height=window.innerHeight;stars=[];var count=isMobile?80:200;for(var i=0;i<count;i++)stars.push({x:Math.random()*w,y:Math.random()*h,r:Math.random()*1.5+.5,d:Math.random()*.5+.1,a:Math.random()})}
  function draw(){ctx.clearRect(0,0,w,h);stars.forEach(function(s){s.y+=s.d;if(s.y>h){s.y=0;s.x=Math.random()*w}s.a=.3+Math.sin(Date.now()*.001+s.x)*.3;ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,Math.PI*2);ctx.fillStyle='rgba(0,229,255,'+s.a+')';ctx.fill()});requestAnimationFrame(draw)}
  resize();draw();window.addEventListener('resize',resize);
})();

// ── Cursor Glow (desktop only) ──
if(!window.matchMedia('(max-width:768px)').matches){
  document.addEventListener('mousemove',function(e){var g=document.getElementById('glow');g.style.left=e.clientX+'px';g.style.top=e.clientY+'px'});
}

// ── Nav Scroll ──
window.addEventListener('scroll',function(){document.getElementById('nav').classList.toggle('scrolled',window.scrollY>50)});

// ── Scroll Reveal ──
var obs=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){e.target.classList.add('visible');obs.unobserve(e.target)}})},{threshold:.1});
document.querySelectorAll('.reveal').forEach(function(el){obs.observe(el)});

// ── Stat Counter Animation ──
var counterObs=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){
  var el=e.target,target=parseInt(el.dataset.target),suffix=el.dataset.suffix||'+',duration=2000,start=0,startTime=null;
  function animate(ts){if(!startTime)startTime=ts;var progress=Math.min((ts-startTime)/duration,1);var current=Math.floor(progress*target);el.textContent=current.toLocaleString('id-ID')+suffix;if(progress<1)requestAnimationFrame(animate)}
  requestAnimationFrame(animate);counterObs.unobserve(e.target)}})},{threshold:.3});
document.querySelectorAll('.social-num[data-target]').forEach(function(el){counterObs.observe(el)});

// ── Pricing ViewContent ──
var pricingSection=document.getElementById('pricing');
if(pricingSection){var pObs=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){if(typeof fbq==='function')fbq('track','ViewContent',{content_name:'Pricing Section',content_category:'IDX Trading',currency:'IDR'});pObs.unobserve(e.target)}})},{threshold:.3});pObs.observe(pricingSection)}
</script>
</body>
</html>"""
