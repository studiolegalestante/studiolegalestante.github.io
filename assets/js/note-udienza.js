/* Note di udienza cifrate - Studio Legale Stante.
   Il testo è cifrato nel browser (AES-GCM) con una chiave ricavata dal codice (PBKDF2);
   al server arrivano solo l'impronta del codice e il testo cifrato. */
(function () {
  'use strict';
  var API = 'https://note-udienza.avv-vincenzostante.workers.dev/n/';
  var ALFABETO = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'; // senza 0, O, 1, I, L
  var SALE = 'studiolegalestante-note-udienza-v1';
  var ITER = 300000;
  var enc = new TextEncoder(), dec = new TextDecoder();
  var $ = function (id) { return document.getElementById(id); };
  var stato = { codice: null, token: null, chiavi: null };

  function b64(buf) { var s = ''; new Uint8Array(buf).forEach(function (b) { s += String.fromCharCode(b); }); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
  function deb64(s) { s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '='; var r = atob(s), u = new Uint8Array(r.length); for (var i = 0; i < r.length; i++) u[i] = r.charCodeAt(i); return u; }
  function hex(buf) { return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ('0' + b.toString(16)).slice(-2); }).join(''); }
  function normalizza(c) { return String(c || '').toUpperCase().replace(/[^0-9A-Z]/g, ''); }
  function valido(c) { return c.length === 8 && [].every.call(c, function (ch) { return ALFABETO.indexOf(ch) >= 0; }); }
  function mostra(c) { return c.slice(0, 4) + '-' + c.slice(4); }
  function nuovoCodice() {
    var out = '', r = new Uint8Array(16);
    while (out.length < 8) { crypto.getRandomValues(r); for (var i = 0; i < r.length && out.length < 8; i++) if (r[i] < 248) out += ALFABETO[r[i] % 31]; }
    return out;
  }
  function nuovoToken() { var r = new Uint8Array(16); crypto.getRandomValues(r); return b64(r); }

  function deriva(codice) {
    return crypto.subtle.importKey('raw', enc.encode(codice), 'PBKDF2', false, ['deriveBits']).then(function (k) {
      return crypto.subtle.deriveBits({ name: 'PBKDF2', salt: enc.encode(SALE), iterations: ITER, hash: 'SHA-256' }, k, 512);
    }).then(function (bits) {
      var b = new Uint8Array(bits);
      return crypto.subtle.importKey('raw', b.slice(0, 32), 'AES-GCM', false, ['encrypt', 'decrypt']).then(function (key) {
        return { key: key, id: hex(b.slice(32)) };
      });
    });
  }
  function cifra(key, obj) {
    var iv = crypto.getRandomValues(new Uint8Array(12));
    return crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, enc.encode(JSON.stringify(obj))).then(function (ct) { return { ct: b64(ct), iv: b64(iv) }; });
  }
  function decifra(key, d) {
    return crypto.subtle.decrypt({ name: 'AES-GCM', iv: deb64(d.iv) }, key, deb64(d.ct)).then(function (p) { return JSON.parse(dec.decode(p)); });
  }
  function sha(s) { return crypto.subtle.digest('SHA-256', enc.encode(s)).then(hex); }
  function chiama(metodo, id, corpo, token) {
    var h = { 'Content-Type': 'application/json' }; if (token) h['X-Modifica'] = token;
    return fetch(API + id, { method: metodo, headers: h, body: corpo ? JSON.stringify(corpo) : undefined }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { j._status = r.status; return j; });
    });
  }
  function dataOra(ms) { return new Date(ms).toLocaleString('it-IT', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }); }

  /* --- archivio locale delle proprie note (solo su questo dispositivo) --- */
  function mie() { try { return JSON.parse(localStorage.getItem('note-udienza') || '[]'); } catch (e) { return []; } }
  function salvaMie(l) { try { localStorage.setItem('note-udienza', JSON.stringify(l)); } catch (e) {} }
  function ricorda(codice, token, scade, titolo) {
    var l = mie().filter(function (n) { return n.c !== codice && n.s > Date.now(); });
    l.unshift({ c: codice, t: token, s: scade, n: titolo }); salvaMie(l.slice(0, 20)); elencoMie();
  }
  function dimentica(codice) { salvaMie(mie().filter(function (n) { return n.c !== codice; })); elencoMie(); }
  function linkPrivato(c, t) { return location.origin + location.pathname + '#m=' + c + '.' + t; }
  function elencoMie() {
    var l = mie().filter(function (n) { return n.s > Date.now(); }), ul = $('nu-mie-lista');
    $('nu-mie').hidden = !l.length; ul.textContent = '';
    l.forEach(function (n) {
      var li = document.createElement('li'), a = document.createElement('a');
      a.href = linkPrivato(n.c, n.t); a.textContent = mostra(n.c) + (n.n ? ' – ' + n.n : '');
      a.addEventListener('click', function (e) { e.preventDefault(); apriModifica(n.c, n.t); });
      li.appendChild(a); li.appendChild(document.createTextNode(' (scade il ' + dataOra(n.s) + ')')); ul.appendChild(li);
    });
  }

  /* --- schede --- */
  function scheda(nome) {
    var leggi = nome === 'leggi';
    $('tab-leggi').setAttribute('aria-selected', leggi); $('tab-scrivi').setAttribute('aria-selected', !leggi);
    $('pan-leggi').hidden = !leggi; $('pan-scrivi').hidden = leggi;
  }
  $('tab-leggi').addEventListener('click', function () { scheda('leggi'); });
  $('tab-scrivi').addEventListener('click', function () { scheda('scrivi'); });

  /* --- lettura --- */
  var letto = [];
  function apri() {
    var codici = $('nu-codici').value.split(/[,;\s]+/).map(normalizza).filter(Boolean);
    var st = $('nu-stato-leggi'); $('nu-risultato').hidden = true;
    if (!codici.length) { st.textContent = 'Inserite il codice della nota.'; return; }
    var errati = codici.filter(function (c) { return !valido(c); });
    if (errati.length) { st.textContent = 'Codice non valido: ' + errati.join(', ') + '. I codici hanno otto caratteri.'; return; }
    st.textContent = 'Apertura in corso…';
    Promise.all(codici.map(function (c) {
      return deriva(c).then(function (k) {
        return chiama('GET', k.id).then(function (r) {
          if (r._status !== 200) return { c: c, err: r.errore || 'nota non disponibile' };
          return decifra(k.key, r).then(function (n) { n.c = c; n.agg = r.agg; return n; }, function () { return { c: c, err: 'impossibile decifrare la nota' }; });
        });
      });
    })).then(function (ris) {
      letto = ris.filter(function (n) { return !n.err; });
      var box = $('nu-testi'); box.textContent = '';
      ris.forEach(function (n) {
        var art = document.createElement('article'); art.className = 'nu-nota';
        var h = document.createElement('h3');
        if (n.err) { h.textContent = mostra(n.c) + ': ' + n.err; art.appendChild(h); box.appendChild(art); return; }
        h.textContent = intestazione(n); art.appendChild(h);
        var meta = document.createElement('p'); meta.className = 'nu-aiuto'; meta.textContent = 'Codice ' + mostra(n.c) + ' · ultima modifica ' + dataOra(n.agg); art.appendChild(meta);
        var pre = document.createElement('div'); pre.className = 'nu-testo'; pre.textContent = n.testo; art.appendChild(pre);
        box.appendChild(art);
      });
      st.textContent = letto.length ? '' : 'Nessuna nota trovata: controllate il codice. Le note si cancellano alla scadenza.';
      $('nu-risultato').hidden = false; $('nu-copia').hidden = !letto.length;
    }).catch(function () { st.textContent = 'Servizio momentaneamente non raggiungibile. Riprovate tra poco.'; });
  }
  function intestazione(n) {
    var t = 'Note di udienza' + (n.difensore ? ' dell\'' + n.difensore.replace(/^\s*(avv\.?|avvocato)\s*/i, 'Avv. ') : '');
    if (n.parte) t += ', ' + n.parte; if (n.rg) t += ' – ' + n.rg; return t;
  }
  $('nu-apri').addEventListener('click', apri);
  $('nu-codici').addEventListener('keydown', function (e) { if (e.key === 'Enter') apri(); });
  $('nu-copia').addEventListener('click', function () {
    var testo = letto.map(function (n) { return intestazione(n) + ':\n' + n.testo; }).join('\n\n');
    var fatto = function () { $('nu-stato-leggi').textContent = 'Testo copiato: incollatelo nel verbale.'; };
    if (navigator.clipboard) navigator.clipboard.writeText(testo).then(fatto, function () { selezionaTesto(); });
    else selezionaTesto();
  });
  function selezionaTesto() { var r = document.createRange(); r.selectNodeContents($('nu-testi')); var s = getSelection(); s.removeAllRanges(); s.addRange(r); $('nu-stato-leggi').textContent = 'Testo selezionato: copiatelo con Ctrl+C.'; }
  $('nu-stampa').addEventListener('click', function () { window.print(); });

  /* --- scrittura --- */
  function dati() { return { v: 1, difensore: $('nu-difensore').value.trim(), parte: $('nu-parte').value.trim(), rg: $('nu-rg').value.trim(), testo: $('nu-testo').value }; }
  function ttl() { return parseInt(document.querySelector('input[name="nu-ttl"]:checked').value, 10); }
  function modalita(modifica) {
    $('nu-salva').textContent = modifica ? 'Salva le modifiche' : 'Crea la nota';
    $('nu-elimina').hidden = !modifica; $('nu-nuova').hidden = !modifica; $('nu-codice-box').hidden = !modifica;
    if (modifica) $('nu-codice').textContent = mostra(stato.codice);
  }
  function salva() {
    var d = dati(), st = $('nu-stato-scrivi'), btn = $('nu-salva');
    if (!d.testo.trim()) { st.textContent = 'Scrivete il testo delle note.'; return; }
    btn.disabled = true; st.textContent = stato.codice ? 'Salvataggio…' : 'Creazione e cifratura…';
    var p;
    if (stato.codice) {
      p = cifra(stato.chiavi.key, d).then(function (c) { c.ttl = ttl(); return chiama('PUT', stato.chiavi.id, c, stato.token); });
    } else {
      var tentativo = function (n) {
        var codice = nuovoCodice(), token = nuovoToken();
        return deriva(codice).then(function (k) {
          return Promise.all([cifra(k.key, d), sha(token)]).then(function (x) {
            var c = x[0]; c.h = x[1]; c.ttl = ttl();
            return chiama('POST', k.id, c).then(function (r) {
              if (r._status === 409 && n < 3) return tentativo(n + 1);
              if (r._status === 201) { stato.codice = codice; stato.token = token; stato.chiavi = k; }
              return r;
            });
          });
        });
      };
      p = tentativo(0);
    }
    p.then(function (r) {
      btn.disabled = false;
      if (r._status !== 200 && r._status !== 201) { st.textContent = 'Errore: ' + (r.errore || 'riprovate') + '.'; return; }
      ricorda(stato.codice, stato.token, r.scade, [d.difensore, d.rg].filter(Boolean).join(' – '));
      history.replaceState(null, '', location.pathname + '#m=' + stato.codice + '.' + stato.token);
      modalita(true); st.textContent = (r._status === 201 ? 'Nota creata. ' : 'Modifiche salvate. ') + 'Si cancellerà il ' + dataOra(r.scade) + ' se non la modificate.';
    }).catch(function () { btn.disabled = false; st.textContent = 'Servizio momentaneamente non raggiungibile. Riprovate tra poco.'; });
  }
  function apriModifica(codice, token) {
    scheda('scrivi'); var st = $('nu-stato-scrivi'); st.textContent = 'Apertura della nota…';
    deriva(codice).then(function (k) {
      return chiama('GET', k.id).then(function (r) {
        if (r._status !== 200) { st.textContent = 'La nota non esiste più: è scaduta o è stata eliminata.'; dimentica(codice); return; }
        return decifra(k.key, r).then(function (n) {
          stato.codice = codice; stato.token = token; stato.chiavi = k;
          $('nu-difensore').value = n.difensore || ''; $('nu-parte').value = n.parte || ''; $('nu-rg').value = n.rg || ''; $('nu-testo').value = n.testo || '';
          history.replaceState(null, '', location.pathname + '#m=' + codice + '.' + token);
          modalita(true); st.textContent = 'Nota aperta in modifica. Scade il ' + dataOra(r.scade) + '.';
        });
      });
    }).catch(function () { st.textContent = 'Impossibile aprire la nota.'; });
  }
  function nuova() {
    stato = { codice: null, token: null, chiavi: null };
    ['nu-difensore', 'nu-parte', 'nu-rg', 'nu-testo'].forEach(function (id) { $(id).value = ''; });
    history.replaceState(null, '', location.pathname); modalita(false); $('nu-stato-scrivi').textContent = '';
  }
  $('nu-salva').addEventListener('click', salva);
  $('nu-nuova').addEventListener('click', nuova);
  $('nu-elimina').addEventListener('click', function () {
    if (!stato.codice) return;
    chiama('DELETE', stato.chiavi.id, null, stato.token).then(function (r) {
      if (r._status === 200 || r._status === 404) { dimentica(stato.codice); nuova(); $('nu-stato-scrivi').textContent = 'Nota eliminata.'; }
      else $('nu-stato-scrivi').textContent = 'Errore: ' + (r.errore || 'riprovate') + '.';
    });
  });
  $('nu-copia-link').addEventListener('click', function () {
    var l = linkPrivato(stato.codice, stato.token);
    if (navigator.clipboard) navigator.clipboard.writeText(l).then(function () { $('nu-stato-scrivi').textContent = 'Link privato copiato. Non condividetelo: permette di modificare la nota.'; });
  });

  /* --- avvio --- */
  elencoMie();
  var m = location.hash.match(/^#m=([0-9A-Z]{8})\.([A-Za-z0-9_-]{22})$/);
  var c = location.hash.match(/^#c=([0-9A-Za-z,-]+)$/);
  if (m) apriModifica(m[1], m[2]);
  else if (c) { $('nu-codici').value = c[1]; apri(); }
})();
