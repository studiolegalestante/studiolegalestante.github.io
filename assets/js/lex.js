/* Lex, assistente virtuale dello Studio Stante: pulsante fluttuante con chat.
   Accompagna il visitatore verso la richiesta di consulenza online. */
(function () {
  var SERVIZIO = 'https://lex.avv-vincenzostante.workers.dev';
  var IT = (document.documentElement.lang || 'it').slice(0, 2) === 'it';
  var T = IT ? {
    consulenza: '/consulenza-online.html#richiesta',
    aria: 'Apri la chat con Lex, assistente virtuale',
    invito: '<b>Serve aiuto?</b>Sono Lex: scrivetemi, vi indico da dove partire.',
    ruolo: 'assistente virtuale dello Studio Stante', chiudi: 'Chiudi la chat',
    avviso: 'Assistente automatico basato su intelligenza artificiale: non è l\'avvocato e non dà pareri. La conversazione non viene conservata.',
    azione: 'Continua con la consulenza online →', campo: 'Scrivete qui…', invia: 'Invia',
    saluto: 'Buongiorno, sono Lex, l\'assistente virtuale dello Studio Stante. Raccontatemi pure in breve che cosa vi è successo: vi aiuto a capire come lo studio può seguirvi.',
    errore: 'In questo momento non riesco a rispondere. Potete chiamare lo studio al 340 1834145 o richiedere direttamente la consulenza online.'
  } : {
    consulenza: '/en/online-consultation.html',
    aria: 'Open the chat with Lex, virtual assistant',
    invito: '<b>Need help?</b>I\'m Lex: write to me and I\'ll show you where to start.',
    ruolo: 'virtual assistant of the Stante law office', chiudi: 'Close the chat',
    avviso: 'Automated assistant based on artificial intelligence: it is not the lawyer and gives no legal advice. The conversation is not stored.',
    azione: 'Continue with the online consultation →', campo: 'Write here…', invia: 'Send',
    saluto: 'Hello, I\'m Lex, the virtual assistant of the Stante law office. Please tell me briefly what happened: I\'ll help you understand how the office can assist you. You can write in any language.',
    errore: 'I cannot reply right now. You can call the office on +39 340 1834145 or request the online consultation directly.'
  };
  var CONSULENZA = T.consulenza;
  var storia = [], scheda = null;

  var css = '' +
    '.lex-bolla{position:fixed;right:max(24px,7vw);bottom:max(24px,10vh);z-index:50;width:128px;height:128px;border-radius:50%;border:4px solid #fff;cursor:pointer;' +
    'background:var(--inchiostro,#1D2B45);color:#fff;box-shadow:0 10px 30px rgba(29,43,69,.45),0 0 0 3px var(--ceralacca,#8E2B22);display:flex;align-items:center;justify-content:center;' +
    'animation:lex-inchino 7s ease-in-out 2s infinite;transform-origin:50% 100%}' +
    '.lex-bolla:hover{animation:none;transform:scale(1.05)}.lex-bolla svg{width:88px;height:88px;overflow:visible}' +
    '.lex-giogo{transform-origin:32px 12px;animation:lex-bilancia 7s ease-in-out 2s infinite}' +
    '@keyframes lex-inchino{0%,14%,100%{transform:none}4%{transform:translateY(6px) rotate(-8deg) scale(.97)}9%{transform:translateY(0) rotate(3deg)}}' +
    '@keyframes lex-bilancia{0%,22%,100%{transform:none}5%{transform:rotate(-14deg)}11%{transform:rotate(9deg)}16%{transform:rotate(-4deg)}}' +
    '@media (prefers-reduced-motion:reduce){.lex-bolla,.lex-giogo{animation:none}}' +
    '.lex-bolla:focus-visible{outline:3px solid var(--ceralacca,#8E2B22);outline-offset:3px}' +
    '.lex-invito{position:fixed;right:calc(max(24px,7vw) + 144px);bottom:calc(max(24px,10vh) + 28px);z-index:50;background:#fff;color:var(--inchiostro,#1D2B45);border:2px solid var(--inchiostro,#1D2B45);' +
    'padding:.7rem 1.1rem;font:1.05rem/1.35 var(--serif,Georgia,serif);box-shadow:0 6px 18px rgba(0,0,0,.15);max-width:250px;cursor:pointer;text-align:left}' +
    '.lex-invito b{display:block;font-family:var(--display,Georgia,serif);font-weight:400;font-size:1.35rem;color:var(--ceralacca,#8E2B22)}' +
    '.lex-invito::after{content:"";position:absolute;right:-10px;top:50%;margin-top:-8px;border:8px solid transparent;border-left:10px solid var(--inchiostro,#1D2B45);border-right:0}' +
    '.lex-pannello{position:fixed;right:max(20px,7vw);bottom:calc(max(24px,10vh) + 144px);z-index:51;width:min(380px,calc(100vw - 32px));height:min(560px,calc(100vh - max(24px,10vh) - 180px));' +
    'background:var(--carta,#FCFCFA);border:1px solid var(--inchiostro,#1D2B45);box-shadow:0 12px 40px rgba(29,43,69,.3);display:flex;flex-direction:column;font-family:var(--serif,Georgia,serif)}' +
    '.lex-testata{display:flex;align-items:center;gap:.7rem;padding:.8rem 1rem;background:var(--inchiostro,#1D2B45);color:#fff}' +
    '.lex-testata svg{width:30px;height:30px;flex:none}.lex-testata b{font-family:var(--display,Georgia,serif);font-weight:400;font-size:1.3rem;display:block;line-height:1.1}' +
    '.lex-testata small{font-style:italic;opacity:.85;font-size:.8rem}.lex-chiudi{margin-left:auto;background:none;border:0;color:#fff;font-size:1.6rem;cursor:pointer;line-height:1}' +
    '.lex-avviso{font-size:.75rem;color:var(--grigio,#5B6270);padding:.5rem 1rem;border-bottom:1px solid var(--filetto,#C9CDD4);margin:0}' +
    '.lex-avviso a{color:inherit}' +
    '.lex-messaggi{flex:1;overflow-y:auto;padding:1rem;display:flex;flex-direction:column;gap:.6rem}' +
    '.lex-messaggi p{margin:0;padding:.6rem .8rem;font-size:.95rem;line-height:1.5;white-space:pre-wrap;max-width:88%}' +
    '.lex-messaggi .lex-u{align-self:flex-end;background:var(--inchiostro,#1D2B45);color:#fff}' +
    '.lex-messaggi .lex-a{align-self:flex-start;background:var(--carta-2,#F2F3F5);border:1px solid var(--filetto,#C9CDD4)}' +
    '.lex-azione{margin:.2rem 1rem .6rem;padding:.7rem 1rem;background:var(--ceralacca,#8E2B22);color:#fff;border:0;font:inherit;font-size:.95rem;cursor:pointer}' +
    '.lex-scrivi{display:flex;gap:.5rem;padding:.7rem;border-top:1px solid var(--filetto,#C9CDD4)}' +
    '.lex-scrivi textarea{flex:1;resize:none;font:inherit;font-size:.95rem;padding:.5rem .6rem;border:1px solid #9AA1AD;min-height:44px;max-height:120px}' +
    '.lex-scrivi button{background:var(--inchiostro,#1D2B45);color:#fff;border:0;padding:0 1rem;font:inherit;cursor:pointer}' +
    '.lex-scrivi button:disabled{opacity:.5}' +
    '[hidden]{display:none!important}' +
    '@media (max-width:600px){.lex-bolla{width:96px;height:96px;right:16px;bottom:20px}.lex-bolla svg{width:64px;height:64px}' +
    '.lex-invito{right:122px;bottom:34px;max-width:190px;font-size:.95rem;padding:.55rem .8rem}.lex-invito b{font-size:1.15rem}' +
    '.lex-pannello{right:16px;bottom:126px;height:calc(100vh - 150px)}}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  // Bilancia della giustizia
  var BILANCIA = '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M32 12v40M20 52h24"/>' +
    '<g class="lex-giogo"><path d="M14 18h36"/><path d="M14 18 6 36h16zM50 18l-8 18h16z"/><path d="M6 36a8 5 0 0 0 16 0M42 36a8 5 0 0 0 16 0"/></g>' +
    '<circle cx="32" cy="12" r="3.5" fill="currentColor"/></svg>';

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html) e.innerHTML = html; return e; }

  var bolla = el('button', 'lex-bolla', BILANCIA);
  bolla.type = 'button';
  bolla.setAttribute('aria-label', T.aria);
  var invito = el('div', 'lex-invito');
  invito.innerHTML = T.invito;
  invito.setAttribute('role', 'button');

  var pannello = el('section', 'lex-pannello');
  pannello.hidden = true;
  pannello.setAttribute('aria-label', 'Chat con Lex');
  pannello.innerHTML =
    '<div class="lex-testata">' + BILANCIA + '<div><b>Lex</b><small>' + T.ruolo + '</small></div>' +
    '<button type="button" class="lex-chiudi" aria-label="' + T.chiudi + '">×</button></div>' +
    '<p class="lex-avviso">' + T.avviso + ' <a href="/privacy.html">Privacy</a></p>' +
    '<div class="lex-messaggi" aria-live="polite"></div>' +
    '<button type="button" class="lex-azione" hidden>' + T.azione + '</button>' +
    '<form class="lex-scrivi"><label hidden for="lex-campo">Il vostro messaggio</label>' +
    '<textarea id="lex-campo" rows="1" maxlength="2000" placeholder="' + T.campo + '"></textarea>' +
    '<button type="submit">' + T.invia + '</button></form>';

  document.body.appendChild(invito);
  document.body.appendChild(pannello);
  document.body.appendChild(bolla);

  var elenco = pannello.querySelector('.lex-messaggi');
  var modulo = pannello.querySelector('.lex-scrivi');
  var campo = pannello.querySelector('textarea');
  var azione = pannello.querySelector('.lex-azione');

  function aggiungi(chi, testo) {
    var p = el('p', chi === 'user' ? 'lex-u' : 'lex-a');
    p.textContent = testo; elenco.appendChild(p); elenco.scrollTop = elenco.scrollHeight; return p;
  }
  function apri() {
    pannello.hidden = false; invito.hidden = true;
    if (!elenco.children.length) aggiungi('assistant', T.saluto);
    campo.focus();
  }
  function chiudi() { pannello.hidden = true; bolla.focus(); }

  bolla.addEventListener('click', function () { pannello.hidden ? apri() : chiudi(); });
  invito.addEventListener('click', apri);
  pannello.querySelector('.lex-chiudi').addEventListener('click', chiudi);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !pannello.hidden) chiudi(); });
  campo.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); modulo.requestSubmit(); } });

  modulo.addEventListener('submit', function (e) {
    e.preventDefault();
    var testo = campo.value.trim(); if (!testo) return;
    campo.value = ''; aggiungi('user', testo); storia.push({ role: 'user', content: testo });
    var attesa = aggiungi('assistant', '…'); modulo.querySelector('button').disabled = true;
    fetch(SERVIZIO, { method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ messaggi: storia.slice(-24), pagina: 'home' }) })
      .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.errore || r.status); return j; }); })
      .then(function (j) {
        var t = String(j.testo || ''), m = t.match(/<scheda>([\s\S]*?)<\/scheda>/);
        storia.push({ role: 'assistant', content: t });
        attesa.textContent = t.replace(/<scheda>[\s\S]*?<\/scheda>/, '').replace(/\*\*|__|^#+\s*/gm, '').trim();
        if (m) { try { scheda = JSON.parse(m[1]); } catch (er) { scheda = null; } }
        if (scheda || storia.length >= 4) azione.hidden = false;
      })
      .catch(function () { attesa.textContent = T.errore; azione.hidden = false; })
      .then(function () { modulo.querySelector('button').disabled = false; campo.focus(); });
  });

  azione.addEventListener('click', function () {
    try { if (scheda && IT) sessionStorage.setItem('lex-scheda', JSON.stringify(scheda)); } catch (e) {}
    window.location.href = CONSULENZA;
  });

  // Sul telefono il fumetto copre i contenuti: si nasconde dopo qualche secondo o al primo scorrimento
  if (window.matchMedia && window.matchMedia('(max-width:600px)').matches) {
    var via = function () { if (pannello.hidden) invito.hidden = true; window.removeEventListener('scroll', via); };
    setTimeout(via, 8000); window.addEventListener('scroll', via, { passive: true });
  }
})();
