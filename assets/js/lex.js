/* Lex, assistente virtuale dello Studio Stante: pulsante fluttuante con chat.
   Accompagna il visitatore verso la richiesta di consulenza online. */
(function () {
  var SERVIZIO = 'https://lex.avv-vincenzostante.workers.dev';
  var CONSULENZA = '/consulenza-online.html#richiesta';
  var storia = [], scheda = null;

  var css = '' +
    '.lex-bolla{position:fixed;right:20px;bottom:20px;z-index:50;width:64px;height:64px;border-radius:50%;border:0;cursor:pointer;' +
    'background:var(--inchiostro,#1D2B45);color:#fff;box-shadow:0 6px 20px rgba(29,43,69,.35);display:flex;align-items:center;justify-content:center;transition:transform .2s}' +
    '.lex-bolla:hover{transform:scale(1.06)}.lex-bolla svg{width:34px;height:34px}' +
    '.lex-bolla:focus-visible{outline:3px solid var(--ceralacca,#8E2B22);outline-offset:3px}' +
    '.lex-invito{position:fixed;right:96px;bottom:32px;z-index:50;background:#fff;color:var(--testo,#2A2D33);border:1px solid var(--filetto,#C9CDD4);' +
    'padding:.6rem .9rem;font:1rem/1.4 var(--serif,Georgia,serif);box-shadow:0 4px 14px rgba(0,0,0,.12);max-width:230px;cursor:pointer}' +
    '.lex-pannello{position:fixed;right:20px;bottom:96px;z-index:51;width:min(380px,calc(100vw - 32px));height:min(560px,calc(100vh - 130px));' +
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
    '@media (max-width:480px){.lex-invito{display:none}.lex-pannello{right:16px;bottom:92px}}';
  var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  // Bilancia della giustizia
  var BILANCIA = '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M32 8v44M20 52h24M14 18h36"/><circle cx="32" cy="12" r="3" fill="currentColor"/>' +
    '<path d="M14 18 6 36h16zM50 18l-8 18h16z"/><path d="M6 36a8 5 0 0 0 16 0M42 36a8 5 0 0 0 16 0"/></svg>';

  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html) e.innerHTML = html; return e; }

  var bolla = el('button', 'lex-bolla', BILANCIA);
  bolla.type = 'button';
  bolla.setAttribute('aria-label', 'Apri la chat con Lex, assistente virtuale');
  var invito = el('div', 'lex-invito');
  invito.textContent = 'Buongiorno, sono Lex. Posso aiutarvi a capire da dove partire?';
  invito.hidden = true;

  var pannello = el('section', 'lex-pannello');
  pannello.hidden = true;
  pannello.setAttribute('aria-label', 'Chat con Lex');
  pannello.innerHTML =
    '<div class="lex-testata">' + BILANCIA + '<div><b>Lex</b><small>assistente virtuale dello Studio Stante</small></div>' +
    '<button type="button" class="lex-chiudi" aria-label="Chiudi la chat">×</button></div>' +
    '<p class="lex-avviso">Assistente automatico basato su intelligenza artificiale: non è l\'avvocato e non dà pareri. ' +
    'La conversazione non viene conservata. <a href="/privacy.html">Privacy</a></p>' +
    '<div class="lex-messaggi" aria-live="polite"></div>' +
    '<button type="button" class="lex-azione" hidden>Continua con la consulenza online →</button>' +
    '<form class="lex-scrivi"><label hidden for="lex-campo">Il vostro messaggio</label>' +
    '<textarea id="lex-campo" rows="1" maxlength="2000" placeholder="Scrivete qui…"></textarea>' +
    '<button type="submit">Invia</button></form>';

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
    if (!elenco.children.length) aggiungi('assistant', 'Buongiorno, sono Lex, l\'assistente virtuale dello Studio Stante. Raccontatemi pure in breve che cosa vi è successo: vi aiuto a capire come lo studio può seguirvi.');
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
      .catch(function () { attesa.textContent = 'In questo momento non riesco a rispondere. Potete chiamare lo studio al 340 1834145 o richiedere direttamente la consulenza online.'; azione.hidden = false; })
      .then(function () { modulo.querySelector('button').disabled = false; campo.focus(); });
  });

  azione.addEventListener('click', function () {
    try { if (scheda) sessionStorage.setItem('lex-scheda', JSON.stringify(scheda)); } catch (e) {}
    window.location.href = CONSULENZA;
  });

  // Invito discreto dopo qualche secondo, una sola volta per sessione
  var giaVisto = false;
  try { giaVisto = sessionStorage.getItem('lex-invito') === '1'; } catch (e) {}
  if (!giaVisto) setTimeout(function () {
    if (pannello.hidden) invito.hidden = false;
    try { sessionStorage.setItem('lex-invito', '1'); } catch (e) {}
  }, 6000);
})();
