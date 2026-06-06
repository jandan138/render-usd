/* ============================================================================
   Render-USD Learning Guide — book.js (classic script, no build)
   Depends on window.BOOK (content.js). Works under file:// and http server.
   ============================================================================ */
(function () {
  "use strict";

  var BOOK = window.BOOK || { parts: [], flat: [] };
  var body = document.body;
  var ROOT = body.getAttribute("data-root") || ""; // "" on index, "../../" on section pages
  var CURRENT = body.getAttribute("data-section-id") || null;

  function el(tag, cls, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /* ---- Theme ------------------------------------------------------------ */
  function initTheme() {
    var saved = null;
    try { saved = localStorage.getItem("ru-theme"); } catch (e) {}
    if (saved) document.documentElement.setAttribute("data-theme", saved);
    var btn = document.querySelector(".theme-toggle");
    var SUN = '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.5M12 19v2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M2.5 12H5M19 12h2.5M4.6 19.4l1.8-1.8M17.6 6.4l1.8-1.8"/></svg>';
    var MOON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.6 6.6 0 0 0 9.8 9.8z"/></svg>';
    function sync() {
      var dark = document.documentElement.getAttribute("data-theme") === "dark";
      if (btn) btn.innerHTML = dark ? SUN : MOON;
    }
    sync();
    if (btn) btn.addEventListener("click", function () {
      var dark = document.documentElement.getAttribute("data-theme") === "dark";
      var next = dark ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("ru-theme", next); } catch (e) {}
      sync();
    });
  }

  /* ---- Sidebar TOC tree ------------------------------------------------- */
  function buildSidebar() {
    var sb = document.querySelector(".sidebar .toc");
    if (!sb) return;
    BOOK.parts.forEach(function (part) {
      var pWrap = el("div", "toc-part");
      pWrap.appendChild(el("div", "toc-part-label",
        '<span class="pn">' + esc(part.n) + "</span><span>" + esc(part.title) + "</span>"));
      part.chapters.forEach(function (ch) {
        var cWrap = el("div", "toc-chapter");
        cWrap.appendChild(el("div", "toc-chapter-title",
          '<span class="cn">' + esc(ch.num) + "</span><span>" + esc(ch.title) + "</span>"));
        var ul = el("ul", "toc-sections");
        ch.sections.forEach(function (sec) {
          var li = el("li");
          var a = el("a", null,
            '<span class="sid">' + esc(sec.id) + "</span>" + esc(sec.t));
          a.href = ROOT + sec.href;
          if (sec.id === CURRENT) {
            a.className = "current";
            a.setAttribute("aria-current", "page");
          }
          li.appendChild(a);
          ul.appendChild(li);
        });
        cWrap.appendChild(ul);
        pWrap.appendChild(cWrap);
      });
      sb.appendChild(pWrap);
    });
    // scroll current into view
    var cur = sb.querySelector("a.current");
    if (cur) setTimeout(function () { cur.scrollIntoView({ block: "center" }); }, 0);
  }

  /* ---- Prev / Next ------------------------------------------------------ */
  function buildPrevNext() {
    var host = document.querySelector(".prevnext");
    if (!host || !CURRENT) return;
    var idx = -1;
    for (var i = 0; i < BOOK.flat.length; i++) if (BOOK.flat[i].id === CURRENT) { idx = i; break; }
    if (idx < 0) return;
    var prev = idx > 0 ? BOOK.flat[idx - 1] : null;
    var next = idx < BOOK.flat.length - 1 ? BOOK.flat[idx + 1] : null;
    host.innerHTML = "";
    if (prev) {
      var a1 = el("a", "prev",
        '<span class="pn-dir">\u2190 ' + esc(prev.id) + '</span><span class="pn-title">' + esc(prev.t) + "</span>");
      a1.href = ROOT + prev.href;
      host.appendChild(a1);
    }
    if (next) {
      var a2 = el("a", "next",
        '<span class="pn-dir">' + esc(next.id) + " \u2192</span><span class=\"pn-title\">" + esc(next.t) + "</span>");
      a2.href = ROOT + next.href;
      host.appendChild(a2);
    }
  }

  /* ---- On this page (right rail) + scroll-spy --------------------------- */
  function buildRail() {
    var rail = document.querySelector(".rail ul");
    var article = document.querySelector(".reading");
    if (!rail || !article) return;
    var heads = article.querySelectorAll("h2[id]");
    if (!heads.length) { var railBox = document.querySelector(".rail"); if (railBox) railBox.style.visibility = "hidden"; return; }
    var links = [];
    heads.forEach(function (h) {
      var li = el("li");
      var a = el("a", null, esc(h.textContent));
      a.href = "#" + h.id;
      li.appendChild(a); rail.appendChild(li);
      links.push({ a: a, h: h });
    });
    function spy() {
      var y = window.scrollY + 100;
      var active = links[0];
      links.forEach(function (l) { if (l.h.offsetTop <= y) active = l; });
      links.forEach(function (l) { l.a.classList.toggle("active", l === active); });
    }
    window.addEventListener("scroll", spy, { passive: true });
    spy();
  }

  /* ---- Reading progress bar -------------------------------------------- */
  function initProgress() {
    var bar = document.querySelector(".progress-bar");
    if (!bar) return;
    function upd() {
      var h = document.documentElement;
      var max = h.scrollHeight - h.clientHeight;
      var p = max > 0 ? (h.scrollTop || window.scrollY) / max : 0;
      bar.style.width = (p * 100).toFixed(1) + "%";
    }
    window.addEventListener("scroll", upd, { passive: true });
    window.addEventListener("resize", upd);
    upd();
  }

  /* ---- Mobile menu ------------------------------------------------------ */
  function initMenu() {
    var btn = document.querySelector(".menu-btn");
    var sb = document.querySelector(".sidebar");
    if (!btn || !sb) return;
    var scrim;
    function close() { sb.classList.remove("open"); if (scrim) { scrim.remove(); scrim = null; } }
    btn.addEventListener("click", function () {
      var open = sb.classList.toggle("open");
      if (open) { scrim = el("div", "scrim"); scrim.addEventListener("click", close); document.body.appendChild(scrim); }
      else close();
    });
  }

  /* ---- Minimal code highlighting + copy --------------------------------- */
  var PY_KW = /\b(def|class|return|import|from|as|if|elif|else|for|while|in|not|and|or|is|None|True|False|with|try|except|finally|raise|lambda|yield|pass|break|continue|global|nonlocal|assert|del)\b/g;
  function highlight(text, lang) {
    var out = esc(text);
    if (lang === "json") {
      out = out.replace(/&quot;([^&]*?)&quot;(\s*:)/g, '<span class="tok-fn">&quot;$1&quot;</span>$2')
               .replace(/:\s*&quot;([^&]*?)&quot;/g, ': <span class="tok-str">&quot;$1&quot;</span>')
               .replace(/\b(-?\d+\.?\d*)\b/g, '<span class="tok-num">$1</span>')
               .replace(/\b(true|false|null)\b/g, '<span class="tok-kw">$1</span>');
      return out;
    }
    // default: python / pseudo
    out = out.replace(/(#[^\n]*)/g, '<span class="tok-com">$1</span>');
    out = out.replace(/(&quot;[^&]*?&quot;|&#39;[^&]*?&#39;|"[^"\n]*"|'[^'\n]*')/g, '<span class="tok-str">$1</span>');
    out = out.replace(PY_KW, '<span class="tok-kw">$1</span>');
    out = out.replace(/\b(\d+\.?\d*)\b/g, '<span class="tok-num">$1</span>');
    return out;
  }
  function initCode() {
    document.querySelectorAll(".code").forEach(function (block) {
      var codeEl = block.querySelector("code");
      if (codeEl && !codeEl.dataset.hl) {
        var lang = codeEl.getAttribute("data-lang") || "python";
        var raw = codeEl.textContent;
        codeEl.dataset.raw = raw;
        codeEl.innerHTML = highlight(raw, lang);
        codeEl.dataset.hl = "1";
      }
      var copy = block.querySelector(".copy");
      if (copy && codeEl) copy.addEventListener("click", function () {
        var txt = codeEl.dataset.raw || codeEl.textContent;
        navigator.clipboard && navigator.clipboard.writeText(txt);
        var old = copy.textContent; copy.textContent = "copied"; setTimeout(function () { copy.textContent = old; }, 1200);
      });
    });
  }

  /* ---- KaTeX bootstrap (if loaded) -------------------------------------- */
  function initMath() {
    if (typeof window.renderMathInElement === "function") {
      window.renderMathInElement(document.body, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\(", right: "\\)", display: false },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    }
  }

  /* ---- Landing TOC (index only) ----------------------------------------- */
  function buildLandingTOC() {
    var host = document.querySelector(".toc-grid");
    if (!host) return;
    BOOK.parts.forEach(function (part) {
      var row = el("div", "part-row");
      row.appendChild(el("div", "rn", esc(part.n)));
      var right = el("div");
      right.appendChild(el("div", "ptitle", esc(part.title)));
      var chs = el("div", "chapters");
      part.chapters.forEach(function (ch) {
        var first = ch.sections[0];
        var crow = el("div", "crow",
          '<span class="cn">' + esc(ch.num) + "</span>");
        var a = el("a", null, esc(ch.title));
        a.href = ROOT + (first ? first.href : "#");
        crow.appendChild(a);
        chs.appendChild(crow);
      });
      right.appendChild(chs);
      row.appendChild(right);
      host.appendChild(row);
    });
  }

  /* ---- init ------------------------------------------------------------- */
  function init() {
    initTheme();
    buildSidebar();
    buildPrevNext();
    buildRail();
    initProgress();
    initMenu();
    initCode();
    buildLandingTOC();
    initMath();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
