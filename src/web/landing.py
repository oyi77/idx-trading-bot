"""
Premium Cinematic Landing Page — Vilona Saham IDX AI Trading Bot.
Design: pure black, particle starfield, orbital system, glass-morphism, cursor glow.
Served at https://botidx.aitradepulse.com
"""
LANDING_HTML = r"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vilona Saham — AI Trading Co-Pilot untuk Bursa Indonesia</title>
<meta name="description" content="Platform analisa saham IDX berbasis AI. Technical analysis, fundamental, bandarmology, event classifier, sector forecast — dalam 10 detik.">
<meta property="og:title" content="Vilona Saham — AI Trading Co-Pilot IDX">
<meta property="og:description" content="AI-powered analysis untuk trader saham Indonesia. Cukup ketik natural — gak perlu hafal command.">
<meta property="og:image" content="https://botidx.aitradepulse.com/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="facebook-domain-verification" content="8ilfftgu8akeubwvejbytox2iefegc" />
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #000000;
    --cyan: #00e5ff;
    --purple: #a855f7;
    --amber: #f59e0b;
    --green: #10b981;
    --red: #ef4444;
    --glass-bg: rgba(10,10,20,0.7);
    --glass-border: rgba(255,255,255,0.06);
    --text: #f1f5f9;
    --text-dim: #94a3b8;
    --surface: #0a0a14;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  html{scroll-behavior:smooth}
  ::-webkit-scrollbar{width:4px}
  ::-webkit-scrollbar-track{background:#000}
  ::-webkit-scrollbar-thumb{background:var(--cyan);border-radius:2px}

  body{
    font-family:'Inter',system-ui,sans-serif;
    background:var(--bg);
    color:var(--text);
    overflow-x:hidden;
    /* cursor tetap muncul, glow sebagai tambahan */
  }

  /* ── Canvas Layers ── */
  canvas#starfield{position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none}
  canvas#grain{position:fixed;top:0;left:0;width:100%;height:100%;z-index:1;pointer-events:none;opacity:0.03}
  .scanlines{
    position:fixed;top:0;left:0;width:100%;height:100%;z-index:2;pointer-events:none;
    background:repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.15) 2px, rgba(0,0,0,0.15) 4px);
    opacity:0.3;
  }

  /* ── Cursor Glow ── */
  #cursor-glow{
    position:fixed;width:350px;height:350px;z-index:3;pointer-events:none;
    background:radial-gradient(circle, rgba(0,229,255,0.08) 0%, rgba(168,85,247,0.04) 40%, transparent 70%);
    border-radius:50%;transform:translate(-50%,-50%);transition:opacity 1.5s;
    opacity:0;
  }

  /* ── Floating Orbs ── */
  .orb{
    position:fixed;z-index:0;pointer-events:none;border-radius:50%;
    filter:blur(80px);opacity:0.15;
  }
  .orb-cyan{width:500px;height:500px;background:var(--cyan);top:20%;left:-20%;transition:transform 0.1s linear}
  .orb-purple{width:400px;height:400px;background:var(--purple);top:50%;right:-15%;transition:transform 0.15s linear}
  .orb-amber{width:350px;height:350px;background:var(--amber);bottom:10%;left:30%;transition:transform 0.12s linear}

  /* ── Content ── */
  .content-wrapper{position:relative;z-index:10}
  .container{max-width:1200px;margin:0 auto;padding:0 24px}
  a{text-decoration:none;color:inherit}

  /* ── Typography ── */
  .grad-text{
    background:linear-gradient(135deg, var(--cyan) 0%, var(--purple) 50%, var(--amber) 100%);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;
  }
  .grad-amber{
    background:linear-gradient(135deg, var(--amber), #fbbf24);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;
  }
  .mono{font-family:'JetBrains Mono',monospace}

  /* ── Glass Cards ── */
  .glass{
    background:rgba(10,10,20,0.7);
    backdrop-filter:blur(24px);
    border:1px solid rgba(255,255,255,0.06);
    border-radius:20px;
  }
  .glass-hover{transition:all .4s cubic-bezier(.25,.46,.45,.94)}
  .glass-hover:hover{
    border-color:var(--cyan);
    transform:translateY(-4px);
    box-shadow:0 0 40px rgba(0,229,255,0.08),0 20px 60px rgba(0,0,0,0.4);
  }

  /* ── Magnetic Buttons ── */
  .magnetic{position:relative;display:inline-flex;align-items:center;gap:10px;border:none}
  .mag-btn{
    padding:18px 44px;border-radius:14px;font-size:18px;font-weight:700;color:#000;
    background:linear-gradient(135deg, var(--cyan), var(--purple));
    position:relative;overflow:hidden;transition:box-shadow .3s;
  }
  .mag-btn::after{
    content:'';position:absolute;inset:0;
    background:linear-gradient(135deg, #fff 0%, transparent 60%);
    opacity:0;transition:opacity .3s;
  }
  .mag-btn:hover{box-shadow:0 0 60px rgba(0,229,255,0.3),0 0 120px rgba(168,85,247,0.15)}
  .mag-btn:hover::after{opacity:0.15}

  .mag-btn-outline{
    padding:16px 40px;border-radius:14px;font-size:17px;font-weight:600;color:var(--cyan);
    background:transparent;border:1.5px solid rgba(0,229,255,0.3);
    transition:all .3s;
  }
  .mag-btn-outline:hover{
    border-color:var(--cyan);
    background:rgba(0,229,255,0.08);
    box-shadow:0 0 30px rgba(0,229,255,0.15);
  }

  /* ── Hero ── */
  .hero{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative}
  .hero-badge{
    display:inline-flex;align-items:center;gap:8px;
    padding:8px 20px;border-radius:50px;
    border:1px solid rgba(0,229,255,0.2);
    background:rgba(0,229,255,0.05);
    font-size:14px;color:var(--cyan);margin-bottom:24px;
  }
  .hero-badge .dot{width:8px;height:8px;background:var(--green);border-radius:50%;animation:pulse-dot 2s infinite}
  @keyframes pulse-dot{0%,100%{opacity:1;box-shadow:0 0 8px var(--green)}50%{opacity:.5;box-shadow:0 0 2px var(--green)}}

  .hero h1{
    font-size:clamp(42px,8vw,88px);font-weight:900;line-height:1.05;
    text-align:center;margin-bottom:20px;letter-spacing:-0.02em;
  }
  .hero h1 .line{display:block}
  .hero .subtitle{
    font-size:clamp(16px,2.5vw,22px);color:var(--text-dim);
    text-align:center;max-width:680px;margin:0 auto 40px;line-height:1.5;
  }

  /* ── Stats ── */
  .hero-stats{display:flex;gap:60px;justify-content:center;margin-top:20px;flex-wrap:wrap}
  .hero-stat{text-align:center}
  .hero-stat .num{font-size:44px;font-weight:900;font-family:'JetBrains Mono',monospace;color:var(--cyan)}
  .hero-stat .label{font-size:14px;color:var(--text-dim);margin-top:4px;letter-spacing:0.05em;text-transform:uppercase}

  /* ── Scroll indicator ── */
  .scroll-ind{margin-top:60px;text-align:center}
  .scroll-ind .mouse{
    width:26px;height:40px;border:2px solid rgba(255,255,255,0.2);border-radius:14px;
    margin:0 auto;position:relative;
  }
  .scroll-ind .mouse::after{
    content:'';width:4px;height:8px;background:var(--cyan);border-radius:2px;
    position:absolute;top:8px;left:50%;transform:translateX(-50%);
    animation:scroll-wheel 1.5s infinite;
  }
  @keyframes scroll-wheel{0%{opacity:1;transform:translate(-50%,0)}100%{opacity:0;transform:translate(-50%,16px)}}

  /* ── Sections ── */
  section{padding:100px 0;position:relative}
  section h2{
    font-size:clamp(28px,5vw,48px);font-weight:800;text-align:center;
    margin-bottom:16px;letter-spacing:-0.02em;
  }
  section .sect-sub{text-align:center;color:var(--text-dim);font-size:18px;margin-bottom:64px;max-width:600px;margin-left:auto;margin-right:auto}

  /* ── Features Grid ── */
  .features-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px}
  .feat-card{padding:36px;position:relative;overflow:hidden}
  .feat-card .feat-icon{font-size:28px;margin-bottom:16px;width:56px;height:56px;display:flex;align-items:center;justify-content:center;border-radius:14px;background:rgba(0,229,255,0.06);border:1px solid rgba(0,229,255,0.1)}
  .feat-card h3{font-size:20px;font-weight:700;margin-bottom:8px}
  .feat-card p{color:var(--text-dim);font-size:15px;line-height:1.6}
  .feat-card .feat-hl{
    display:inline-block;padding:3px 10px;border-radius:6px;
    font-size:11px;font-weight:600;font-family:'JetBrains Mono',monospace;
    margin-top:12px;
  }
  .hl-cyan{background:rgba(0,229,255,0.1);color:var(--cyan)}
  .hl-purple{background:rgba(168,85,247,0.1);color:var(--purple)}
  .hl-amber{background:rgba(245,158,11,0.1);color:var(--amber)}

  /* ── Battle Arena ── */
  .arena{display:grid;grid-template-columns:1fr auto 1fr;gap:40px;align-items:center;max-width:1000px;margin:0 auto;text-align:center}
  .arena-col{padding:40px 28px}
  .arena-col h3{font-size:22px;font-weight:800;margin-bottom:12px}
  .arena-col p{color:var(--text-dim);font-size:15px;line-height:1.7}
  .arena-vs{
    font-size:32px;font-weight:900;
    background:linear-gradient(135deg, var(--cyan), var(--purple));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;
  }
  @media(max-width:768px){
    .arena{grid-template-columns:1fr}
    .arena-vs{transform:rotate(90deg)}
  }

  /* ── Terminal ── */
  .term-container{max-width:750px;margin:0 auto}
  .term{
    background:#0a0a0f;border:1px solid rgba(255,255,255,0.08);
    border-radius:16px;overflow:hidden;
  }
  .term-header{
    padding:12px 16px;background:#0d0d15;
    border-bottom:1px solid rgba(255,255,255,0.06);
    display:flex;align-items:center;gap:8px;
  }
  .term-dot{width:10px;height:10px;border-radius:50%}
  .term-dot.r{background:var(--red)}.term-dot.y{background:var(--amber)}.term-dot.g{background:var(--green)}
  .term-body{padding:20px 24px;font-family:'JetBrains Mono',monospace;font-size:13px;line-height:1.8;color:var(--text-dim);min-height:140px}
  .term-body .prompt{color:var(--cyan)}.term-body .cmd{color:var(--text)}
  .term-body .out{color:var(--green)}.term-body .dim{color:#475569}
  .term-body .hl{color:var(--purple)}.term-body .warn{color:var(--amber)}
  .term-cursor{display:inline-block;width:8px;height:15px;background:var(--cyan);animation:blink 1s infinite;vertical-align:text-bottom;margin-left:2px}
  @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}

  /* ── Pricing ── */
  .pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px;max-width:960px;margin:0 auto}
  .price-card{padding:44px 32px;position:relative;text-align:center;display:flex;flex-direction:column}
  .price-card .badge{
    position:absolute;top:-12px;left:50%;transform:translateX(-50%);
    padding:6px 20px;border-radius:50px;font-size:12px;font-weight:700;
    background:linear-gradient(135deg, var(--cyan), var(--purple));color:#000;
  }
  .price-card h3{font-size:22px;font-weight:800;margin-bottom:4px}
  .price-card .tier-desc{font-size:13px;color:var(--text-dim);margin-bottom:20px}
  .price-card .price{font-size:48px;font-weight:900;font-family:'JetBrains Mono',monospace}
  .price-card .price span{font-size:15px;color:var(--text-dim);font-weight:400;font-family:'Inter',sans-serif}
  .price-card ul{list-style:none;text-align:left;margin:28px 0;flex:1}
  .price-card ul li{padding:8px 0;color:var(--text-dim);font-size:14px;display:flex;align-items:center;gap:8px}
  .price-card ul li::before{content:'✓';color:var(--green);font-weight:700;font-size:13px;flex-shrink:0}
  .price-card ul li.dim::before{content:'—';color:#475569}
  .price-card .price-btn{padding:14px 0;border-radius:12px;font-size:16px;font-weight:700;width:100%}
  .price-card.featured{border-color:rgba(0,229,255,0.2);background:linear-gradient(180deg, rgba(10,10,20,0.9), rgba(0,229,255,0.03))}

  /* ── Ticker ── */
  .ticker-wrap{overflow:hidden;border-top:1px solid rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.04);padding:12px 0;margin:80px 0}
  .ticker{
    display:flex;gap:60px;animation:ticker-scroll 30s linear infinite;
    font-family:'JetBrains Mono',monospace;font-size:12px;
  }
  @keyframes ticker-scroll{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}
  .ticker-item{white-space:nowrap;color:var(--text-dim)}
  .ticker-item .symbol{color:var(--cyan)}.ticker-item .up{color:var(--green)}.ticker-item .down{color:var(--red)}

  /* ── Footer ── */
  footer{padding:60px 0;text-align:center;border-top:1px solid rgba(255,255,255,0.04);color:var(--text-dim);font-size:14px}
  footer a{color:var(--cyan)}
  footer a:hover{text-decoration:underline}

  /* ── Animations on scroll ── */
  .reveal{opacity:0;transform:translateY(30px);transition:all .8s cubic-bezier(.25,.46,.45,.94)}
  .reveal.visible{opacity:1;transform:translateY(0)}
  .reveal-left{opacity:0;transform:translateX(-30px);transition:all .8s cubic-bezier(.25,.46,.45,.94)}
  .reveal-left.visible{opacity:1;transform:translateX(0)}
  .reveal-right{opacity:0;transform:translateX(30px);transition:all .8s cubic-bezier(.25,.46,.45,.94)}
  .reveal-right.visible{opacity:1;transform:translateX(0)}

  /* ── Mobile ── */
  @media(max-width:768px){
    section{padding:60px 0}
    .hero-stats{gap:30px}
    .hero-stat .num{font-size:32px}
    .features-grid{grid-template-columns:1fr}
    .pricing-grid{grid-template-columns:1fr}
    body{cursor:auto}
    #cursor-glow{display:none}
  }
</style>
<!-- ═══ Meta Pixel + CAPI ═══ -->
<script>!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');fbq('init', '320653057513880');fbq('track','PageView');</script>
<noscript><img height="1" width="1" style="display:none" src="https://www.facebook.com/tr?id=320653057513880&ev=PageView&noscript=1"/></noscript>
<script>
(function(){
  var U='https://botidx.aitradepulse.com/api/capi';
  function S(e,d){
    fetch(U,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({event_name:e,source_url:location.href,event_data:d||{}})}).catch(function(){});
  }
  S('PageView');
  window._capi=function(e,d){S(e,d)};
})();
</script>
</head>
<body>

  <!-- === Background Layers === -->
  <canvas id="starfield"></canvas>
  <canvas id="grain"></canvas>
  <div class="scanlines"></div>
  <div id="cursor-glow"></div>
  <div class="orb orb-cyan"></div>
  <div class="orb orb-purple"></div>
  <div class="orb orb-amber"></div>

  <div class="content-wrapper">

    <!-- === HERO === -->
    <section class="hero" style="padding-bottom:40px">
      <div class="container" style="text-align:center">
        <div class="hero-badge reveal">
          <span class="dot"></span> Live di Telegram — @vilonidxbot
        </div>
        <h1 class="reveal" style="transition-delay:0.1s">
          <span class="line grad-text">AI Co-Pilot</span>
          <span class="line">untuk Trader Saham IDX</span>
        </h1>
        <p class="subtitle reveal" style="transition-delay:0.2s">
          Satu-satunya platform yang menggabungkan <span class="grad-amber">TradingView-grade chart</span>,
          <span class="grad-amber">AI insight real-time</span>, dan
          <span class="grad-amber">Bandar Flow detection</span> dalam satu perintah natural.
          Gak perlu hafal 300 command — cukup ketik apa yang lo butuhin.
        </p>

        <div class="reveal" style="transition-delay:0.3s;display:flex;gap:16px;justify-content:center;flex-wrap:wrap">
          <a href="https://t.me/vilonidxbot" class="mag-btn magnetic">🚀 Coba Gratis Sekarang</a>
          <a href="#pricing" class="mag-btn-outline magnetic">Lihat Harga ↓</a>
        </div>

        <div class="hero-stats reveal" style="transition-delay:0.4s">
          <div class="hero-stat">
            <div class="num" data-count="17">0</div>
            <div class="label">Fitur AI</div>
          </div>
          <div class="hero-stat">
            <div class="num" data-count="11">0</div>
            <div class="label">Sektor Forecast</div>
          </div>
          <div class="hero-stat">
            <div class="num" data-count="95.2" is-float="true">0</div>
            <div class="label">% Akurasi Event AI</div>
          </div>
          <div class="hero-stat">
            <div class="num" data-count="7530">0</div>
            <div class="label">Hari Data IHSG</div>
          </div>
        </div>
      </div>

      <div class="scroll-ind">
        <div class="mouse"></div>
        <p style="font-size:11px;color:var(--text-dim);margin-top:10px;letter-spacing:.1em;text-transform:uppercase">Scroll</p>
      </div>
    </section>

    <!-- === TICKER === -->
    <div class="ticker-wrap">
      <div class="ticker" id="ticker-bar">
        <!-- populated by JS -->
      </div>
    </div>

    <!-- === FEATURES === -->
    <section id="features">
      <div class="container">
        <h2 class="reveal">Kenapa <span class="grad-text">Vilona Saham</span>?</h2>
        <p class="sect-sub reveal">AI-powered analysis yang gak bisa lo dapetin di bot saham lain. Ini bukan sekadar bot — ini co-pilot trading lo.</p>

        <div class="features-grid">
          <div class="glass glass-hover feat-card reveal">
            <div class="feat-icon">📊</div>
            <h3>Analisa Multi-Dimensi</h3>
            <p>Teknikal + Fundamental + Foreign Flow + News — semua dalam satu perintah natural. Cukup ketik <span class="mono" style="color:var(--cyan)">analisa TLKM</span> dan dapet full breakdown.</p>
            <span class="feat-hl hl-cyan">avail: /analisa &lt;symbol&gt;</span>
          </div>
          <div class="glass glass-hover feat-card reveal">
            <div class="feat-icon">🎰</div>
            <h3>Bandarmology Engine</h3>
            <p>Deteksi akumulasi & distribusi bandar asing <strong>real-time</strong>. Lihat siapa yang lagi beli dan jual di pasar sebelum harga gerak.</p>
            <span class="feat-hl hl-purple">PREMIUM: /bandarmology &lt;symbol&gt;</span>
          </div>
          <div class="glass glass-hover feat-card reveal">
            <div class="feat-icon">🧠</div>
            <h3>AI Event Classifier</h3>
            <p>Klasifikasi otomatis berita korporat — <strong>11 kategori event</strong> dengan akurasi 95.2%. Dividen, Buyback, M&A, IPO, RUPS & more.</p>
            <span class="feat-hl hl-amber">PREMIUM: /event &lt;symbol&gt;</span>
          </div>
          <div class="glass glass-hover feat-card reveal">
            <div class="feat-icon">📈</div>
            <h3>Sector Forecast 7 Hari</h3>
            <p>Prediksi volatilitas <strong>11 sektor IDX</strong> untuk 7 hari ke depan. Model AI: TFT, NHITS, NBEATSx, LSTM — ensemble terbaik.</p>
            <span class="feat-hl hl-purple">PREMIUM: /sector &lt;nama sektor&gt;</span>
          </div>
          <div class="glass glass-hover feat-card reveal">
            <div class="feat-icon">⏱</div>
            <h3>Backtest Engine</h3>
            <p>Validasi sinyal trading dengan data historis <strong>3 tahun</strong>. Win Rate, Sharpe Ratio, Max Drawdown, Alpha vs Buy &amp; Hold.</p>
            <span class="feat-hl hl-cyan">avail: /backtest &lt;symbol&gt;</span>
          </div>
          <div class="glass glass-hover feat-card reveal">
            <div class="feat-icon">🔔</div>
            <h3>Smart Alerts</h3>
            <p>Pantau hingga <strong>200 saham</strong> sekaligus. Notifikasi real-time saat harga menyentuh level target lo — gak ketinggalan momentum.</p>
            <span class="feat-hl hl-cyan">avail: /alert &lt;symbol&gt; &lt;harga&gt;</span>
          </div>
        </div>
      </div>
    </section>

    <!-- === BATTLE ARENA === -->
    <section style="background:linear-gradient(180deg, transparent 0%, rgba(0,229,255,0.02) 50%, transparent 100%)">
      <div class="container">
        <h2 class="reveal"><span class="grad-text">Battle Arena</span></h2>
        <p class="sect-sub reveal">Bandigan langsung — kenapa trader pindah ke Vilona Saham</p>

        <div class="arena">
          <div class="glass feat-card reveal-left">
            <h3 style="color:var(--red)">Bot Saham Lain</h3>
            <p>300+ command hafalan<br>Data delay 15-60 menit<br>Indikator manual baca sendiri<br>No AI, no insight<br>Telegram only<br>Rp29rb/bln</p>
          </div>
          <div class="arena-vs">VS</div>
          <div class="glass feat-card reveal-right" style="border-color:rgba(0,229,255,0.15)">
            <h3 style="color:var(--cyan)">Vilona Saham</h3>
            <p>Natural language — <span class="grad-amber">ketik bebas</span><br>Real-time via WebSocket<br>AI breakdown + scoring otomatis<br>11 AI engines + Bandar detector<br>Telegram + Web Dashboard<br>Mulai <strong>Rp0</strong></p>
          </div>
        </div>
      </div>
    </section>

    <!-- === LIVE TERMINAL === -->
    <section>
      <div class="container">
        <h2 class="reveal">Lihat Langsung <span class="grad-text">Cara Kerjanya</span></h2>
        <p class="sect-sub reveal">Buka Telegram, ketik <span class="mono" style="color:var(--cyan)">@vilonidxbot</span> — gak ribet.</p>

        <div class="term-container reveal">
          <div class="term">
            <div class="term-header">
              <span class="term-dot r"></span><span class="term-dot y"></span><span class="term-dot g"></span>
              <span style="font-size:12px;color:var(--text-dim);margin-left:8px">@vilonidxbot — Telegram</span>
            </div>
            <div class="term-body" id="terminal-body">
              <span class="dim">// Ketik di Telegram ⚡</span><br>
              <span class="prompt">YOU</span> <span class="cmd">analisa BBCA</span><br>
              <span class="dim">...</span><br>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- === PRICING === -->
    <section id="pricing">
      <div class="container">
        <h2 class="reveal">Harga <span class="grad-text">Transparan</span></h2>
        <p class="sect-sub reveal">Mulai gratis. Upgrade kapan aja via <span class="grad-amber">/upgrade</span> di bot.</p>

        <div class="pricing-grid">
          <!-- Free -->
          <div class="glass glass-hover price-card reveal">
            <h3>🆓 <span class="grad-text">Free</span></h3>
            <p class="tier-desc">Buat nyobain & belajar</p>
            <div class="price">Rp0<span>/bulan</span></div>
            <ul>
              <li>5 screening/hari</li>
              <li>Watchlist 3 saham</li>
              <li>Data delay 15 menit</li>
              <li>5 alert aktif</li>
              <li>Chart + AI basic</li>
              <li class="dim">Bandar View</li>
              <li class="dim">Event Classifier</li>
              <li class="dim">Sector Forecast</li>
            </ul>
            <a href="https://t.me/vilonidxbot" class="mag-btn price-btn magnetic" style="display:block;text-align:center">Mulai Gratis</a>
          </div>

          <!-- Pro -->
          <div class="glass glass-hover price-card reveal" style="transition-delay:0.15s">
            <h3>💎 <span class="grad-text">Pro</span></h3>
            <p class="tier-desc">Untuk trader aktif harian</p>
            <div class="price">Rp49rb<span>/bulan</span></div>
            <ul>
              <li>Unlimited screening</li>
              <li>Watchlist 10 saham</li>
              <li>Real-time data</li>
              <li>50 alert</li>
              <li>AI trade setup full</li>
              <li>Unlimited analisa</li>
              <li class="dim">Bandar View</li>
              <li class="dim">Event Classifier</li>
            </ul>
            <a href="https://t.me/vilonidxbot" class="mag-btn price-btn magnetic" style="display:block;text-align:center;background:linear-gradient(135deg,var(--purple),var(--cyan))">Upgrade Pro</a>
          </div>

          <!-- Premium -->
          <div class="glass glass-hover price-card featured reveal" style="transition-delay:0.3s">
            <div class="badge">✨ PALING POPULER</div>
            <h3>👑 <span class="grad-amber">Premium</span></h3>
            <p class="tier-desc">Untuk trader serius & profesional</p>
            <div class="price" style="color:var(--amber)">Rp149rb<span>/bulan</span></div>
            <ul>
              <li>Semua fitur Pro ✓</li>
              <li>Watchlist unlimited</li>
              <li>200 alert</li>
              <li>🎰 Bandar View + Sentiment</li>
              <li>🧠 Event Classifier AI</li>
              <li>📈 Sector Forecast 11 sektor</li>
              <li>📊 Auto-Report Mingguan</li>
              <li>⚡ Priority AI response</li>
            </ul>
            <a href="https://t.me/vilonidxbot" class="mag-btn price-btn magnetic" style="display:block;text-align:center;background:linear-gradient(135deg,var(--amber),#fbbf24);color:#000">Upgrade Premium</a>
          </div>
        </div>
      </div>
    </section>

    <!-- === FOOTER === -->
    <footer>
      <div class="container">
        <p style="font-size:24px;font-weight:800;margin-bottom:8px"><span class="grad-text">Vilona Saham</span></p>
        <p>AI Co-Pilot Trading untuk Bursa Efek Indonesia</p>
        <p style="margin-top:16px">
          <a href="https://t.me/vilonidxbot">@vilonidxbot</a> ·
          <a href="#pricing">Pricing</a> ·
          <a href="https://jasahub.id/p/vilona-saham">Powered by Jasahub/Scalev</a>
        </p>
        <p style="margin-top:24px;color:#475569;font-size:12px">© 2025 Vilona Saham. All rights reserved.</p>
      </div>
    </footer>

  </div>

  <!-- === SCRIPTS === -->
  <script>
  // ── Starfield with connection mesh ──
  (()=>{
    const c=document.getElementById('starfield'),ctx=c.getContext('2d');
    let w,h,stars=[],CONN_DIST=120,STAR_COUNT=200;
    function resize(){w=c.width=window.innerWidth;h=c.height=window.innerHeight}
    resize();window.addEventListener('resize',resize);

    for(let i=0;i<STAR_COUNT;i++){
      stars.push({
        x:Math.random()*w,y:Math.random()*h,
        r:Math.random()*1.8+0.3,o:Math.random()*0.6+0.3,
        vx:(Math.random()-0.5)*0.15,vy:(Math.random()-0.5)*0.15,
        twinkle:Math.random()*Math.PI*2
      });
    }

    function draw(t){
      ctx.clearRect(0,0,w,h);
      // Update & draw stars
      for(let s of stars){
        s.x+=s.vx;s.y+=s.vy;
        if(s.x<0)s.x=w;if(s.x>w)s.x=0;
        if(s.y<0)s.y=h;if(s.y>h)s.y=0;
        let tw=0.5+0.5*Math.sin(t*0.002+s.twinkle);
        ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,Math.PI*2);
        ctx.fillStyle=`rgba(255,255,255,${s.o*tw})`;ctx.fill();
      }
      // Connection lines
      for(let i=0;i<stars.length;i++){
        for(let j=i+1;j<stars.length;j++){
          let dx=stars[i].x-stars[j].x,dy=stars[i].y-stars[j].y,dist=Math.sqrt(dx*dx+dy*dy);
          if(dist<CONN_DIST){
            let alpha=0.06*(1-dist/CONN_DIST);
            ctx.beginPath();ctx.moveTo(stars[i].x,stars[i].y);ctx.lineTo(stars[j].x,stars[j].y);
            ctx.strokeStyle=`rgba(0,229,255,${alpha})`;ctx.stroke();
          }
        }
      }
      requestAnimationFrame(draw);
    }
    requestAnimationFrame(draw);
  })();

  // ── Film Grain ──
  (()=>{
    const c=document.getElementById('grain'),ctx=c.getContext('2d');
    let w,h;function resize(){w=c.width=window.innerWidth;h=c.height=window.innerHeight}
    resize();window.addEventListener('resize',resize);
    function grain(){
      let img=ctx.createImageData(w,h),d=img.data;
      for(let i=0;i<d.length;i+=4){
        let v=Math.random()*50;
        d[i]=v;d[i+1]=v;d[i+2]=v;d[i+3]=255;
      }
      ctx.putImageData(img,0,0);
    }
    setInterval(grain,200);
  })();

  // ── Cursor Glow ──
  (()=>{
    const g=document.getElementById('cursor-glow');
    let hiding=null;
    document.addEventListener('mousemove',e=>{
      g.style.left=e.clientX+'px';g.style.top=e.clientY+'px';
      g.style.opacity='1';
      clearTimeout(hiding);
      hiding=setTimeout(()=>{g.style.opacity='0'},2000);
    });
  })();

  // ── Floating Orbs ──
  (()=>{
    const orbs=document.querySelectorAll('.orb');
    document.addEventListener('mousemove',e=>{
      let x=(e.clientX/window.innerWidth-0.5)*30;
      let y=(e.clientY/window.innerHeight-0.5)*30;
      orbs[0].style.transform=`translate(${x}px,${y}px)`;
      orbs[1].style.transform=`translate(${-x*0.7}px,${-y*0.7}px)`;
      orbs[2].style.transform=`translate(${x*0.5}px,${-y*0.5}px)`;
    });
  })();

  // ── Animated Counters ──
  (()=>{
    const nums=document.querySelectorAll('.num[data-count]');
    const obs=new IntersectionObserver((entries)=>{
      entries.forEach(e=>{
        if(!e.isIntersecting)return;
        let el=e.target,target=parseFloat(el.dataset.count),
        isFloat=el.dataset.float==='true',dur=1500,start=null;
        function anim(ts){
          if(!start)start=ts;
          let p=Math.min((ts-start)/dur,1),ease=1-Math.pow(1-p,3),
          cur=isFloat?(target*ease).toFixed(1):Math.floor(target*ease);
          el.textContent=isFloat?cur:cur.toLocaleString();
          if(p<1)requestAnimationFrame(anim);
          else el.textContent=isFloat?target.toFixed(1):target.toLocaleString();
        }
        requestAnimationFrame(anim);
        obs.unobserve(el);
      });
    },{threshold:0.5});
    nums.forEach(n=>obs.observe(n));
  })();

  // ── Ticker ──
  (()=>{
    const symbols=['BBCA','BBRI','TLKM','BMRI','BBNI','UNVR','ASII','ADRO','ICBP','PGAS'];
    const t=document.getElementById('ticker-bar');
    let html='';
    for(let i=0;i<3;i++){ // 3x for seamless loop
      symbols.forEach(s=>{
        let r=Math.random()*4-2;
        html+=`<span class="ticker-item"><span class="symbol">${s}</span> <span class="${r>=0?'up':'down'}">${r>=0?'+':''}${r.toFixed(2)}%</span></span>`;
      });
    }
    t.innerHTML=html;
  })();

  // ── Terminal Typing ──
  (()=>{
    const term=document.getElementById('terminal-body');
    const lines=[
      {type:'dim',text:'// Ketik di Telegram ⚡'},
      {type:'prompt',text:'YOU'},
      {type:'cmd',text:' analisa BBCA',pause:800},
      {type:'out',text:'\n✅ BBCA — PT Bank Central Asia Tbk',pause:400},
      {type:'out',text:'\n📊 Harga: 9.875 | +1.2%',pause:300},
      {type:'out',text:'\n🎯 Entry Zone: 9.750 – 9.825',pause:300},
      {type:'out',text:'\n🛑 Stop Loss: 9.625 (-1.5%)',pause:300},
      {type:'out',text:'\n💰 TP1: 10.100 (+2.3%) | TP2: 10.350',pause:300},
      {type:'out',text:'\n📈 Signal Score: 87/100 ✅ STRONG BUY',pause:500},
      {type:'hl',text:'\n🎰 Bandar: Asing net buy Rp 124M (akumulasi)'},
      {type:'','text':'<span class="term-cursor"></span>'},
    ];
    let li=0,ci=0,chars=lines[0].text;
    function type(){
      if(li>=lines.length){
        setTimeout(()=>{
          term.innerHTML='<span class="dim">// Ketik di Telegram ⚡</span><br><span class="prompt">YOU</span> <span class="cmd">analisa BBCA</span><br><span class="dim">...</span><br><span class="term-cursor"></span>';
          li=0;ci=0;chars=lines[0].text;type();
        },4000);
        return;
      }
      if(ci===0){
        term.innerHTML=''; // clear for start
        for(let i=0;i<li;i++){
          let l=lines[i];
          term.innerHTML+=l.type?`<span class="${l.type}">${l.text}</span>`:l.text;
        }
      }
      if(ci<chars.length){
        let l=lines[li];
        term.innerHTML+=(l.type?`<span class="${l.type}">`:'')+chars[ci]+(l.type?'</span>':'');
        ci++;
        setTimeout(type,25+Math.random()*15);
      }else{
        if(lines[li].pause){setTimeout(()=>{li++;ci=0;chars=lines[li]?lines[li].text:'';type()},lines[li].pause)}
        else{li++;ci=0;chars=lines[li]?lines[li].text:'';type();}
      }
    }
    // Start typing when terminal is visible
    const obs=new IntersectionObserver((entries)=>{
      if(entries[0].isIntersecting){type();obs.disconnect();}
    },{threshold:0.3});
    obs.observe(term);
  })();

  // ── Scroll Reveal ──
  (()=>{
    const reveals=document.querySelectorAll('.reveal,.reveal-left,.reveal-right');
    const obs=new IntersectionObserver((entries)=>{
      entries.forEach(e=>{
        if(e.isIntersecting){e.target.classList.add('visible');obs.unobserve(e.target)}
      });
    },{threshold:0.15,rootMargin:'0px 0px -40px 0px'});
    reveals.forEach(r=>obs.observe(r));
  })();

  // ── Magnetic Buttons ──
  (()=>{
    document.querySelectorAll('.magnetic').forEach(btn=>{
      btn.addEventListener('mousemove',e=>{
        let r=btn.getBoundingClientRect(),
        x=e.clientX-r.left-r.width/2,y=e.clientY-r.top-r.height/2;
        btn.style.transform=`translate(${x*0.2}px,${y*0.2}px)`;
      });
      btn.addEventListener('mouseleave',()=>{btn.style.transform=''});
    });
  })();

  // ── Feature Card 3D Tilt ──
  (()=>{
    document.querySelectorAll('.feat-card').forEach(card=>{
      card.addEventListener('mousemove',e=>{
        let r=card.getBoundingClientRect(),
        x=(e.clientX-r.left)/r.width-0.5,y=(e.clientY-r.top)/r.height-0.5;
        card.style.transform=`perspective(1000px) rotateY(${x*6}deg) rotateX(${-y*4}deg) translateY(-2px)`;
      });
      card.addEventListener('mouseleave',()=>{
        card.style.transform='perspective(1000px) rotateY(0) rotateX(0) translateY(0)';
      });
    });
  })();

  // ── Smooth scroll for anchor links ──
  document.querySelectorAll('a[href^="#"]').forEach(a=>{
    a.addEventListener('click',e=>{
      e.preventDefault();
      let t=document.querySelector(a.getAttribute('href'));
      if(t)t.scrollIntoView({behavior:'smooth'});
    });
  });
  </script>

  <!-- ═══ Conversion Tracking ═══ -->
  <script>
  (function(){
    var capi=window._capi||function(){};

    // ── 1. CTA clicks → Lead ──
    document.querySelectorAll('a[href*="t.me/vilonidxbot"]').forEach(function(a){
      a.addEventListener('click',function(){
        var plan=a.closest('.price-card');
        var tier=plan?plan.querySelector('h3').textContent.trim():'unknown';
        if(typeof fbq==='function')fbq('track','Lead',{content_name:'Telegram CTA',content_category:tier,currency:'IDR'});
        capi('Lead',{content_name:'Telegram CTA',content_category:tier});
      });
    });

    // ── 2. Pricing section → ViewContent ──
    var pricingTracked=false;
    var pricingSection=document.getElementById('pricing');
    if(pricingSection){
      var obs=new IntersectionObserver(function(entries){
        if(entries[0].isIntersecting && !pricingTracked){
          pricingTracked=true;
          if(typeof fbq==='function')fbq('track','ViewContent',{content_name:'Pricing Section',content_category:'IDX Trading',currency:'IDR'});
          capi('ViewContent',{content_name:'Pricing Section',content_category:'IDX Trading'});
          obs.disconnect();
        }
      },{threshold:0.3});
      obs.observe(pricingSection);
    }

    // ── 3. Upgrade CTA clicks → InitiateCheckout ──
    document.querySelectorAll('.price-btn').forEach(function(btn){
      btn.addEventListener('click',function(){
        var card=btn.closest('.price-card');
        var tier=card?card.querySelector('h3').textContent.trim():'unknown';
        var price=card?card.querySelector('.price').textContent.trim():'0';
        if(typeof fbq==='function')fbq('track','InitiateCheckout',{content_name:'Upgrade '+tier,value:parseInt(price.replace(/[^0-9]/g,''))||0,currency:'IDR'});
        capi('InitiateCheckout',{content_name:'Upgrade '+tier,value:price});
      });
    });
  })();
  </script>
</body>
</html>"""
