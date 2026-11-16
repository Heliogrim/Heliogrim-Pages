// Renders ```hg-diagram``` blocks with a self-hosted Mermaid (loaded only on pages that have one)
// and gives every diagram and content image an inspect viewer: fit to window, drag to pan, wheel to zoom.
(function () {
  var ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5,5H10V7H7V10H5V5M14,5H19V10H17V7H14V5M17,14H19V19H14V17H17V14M10,17V19H5V14H7V17H10Z"/></svg>';

  // ---- Inspect viewer: one <dialog> per page, created on first use.
  var dlg, stage, layer, s = 1, x = 0, y = 0, w = 0, h = 0;
  function apply() { layer.style.transform = "translate(" + x + "px," + y + "px) scale(" + s + ")"; }
  function fit() {
    var r = stage.getBoundingClientRect();
    s = Math.min(r.width / w, r.height / h) * 0.95;
    x = (r.width - w * s) / 2; y = (r.height - h * s) / 2; apply();
  }
  function zoom(f, cx, cy) {
    var n = Math.min(Math.max(s * f, 0.05), 40); f = n / s; s = n;
    x = cx - (cx - x) * f; y = cy - (cy - y) * f; apply();
  }
  function viewer() {
    if (dlg) return;
    dlg = document.createElement("dialog");
    dlg.className = "hg-inspect";
    dlg.setAttribute("aria-label", "Inspect figure");
    function btn(a, label, d) {
      return '<button type="button" data-a="' + a + '" title="' + label + '" aria-label="' + label + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + d + '"/></svg></button>';
    }
    dlg.innerHTML = '<div class="hg-inspect__bar"><span>Drag to pan · scroll to zoom · double-click to fit · Esc to close</span>' +
      btn("out", "Zoom out", "M19,13H5V11H19V13Z") +
      btn("in", "Zoom in", "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z") +
      btn("fit", "Fit to window", ICON.match(/d="([^"]+)"/)[1]) +
      '<i></i>' + btn("close", "Close", "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z") +
      '</div><div class="hg-inspect__stage"><div></div></div>';
    stage = dlg.querySelector(".hg-inspect__stage"); layer = stage.firstChild;
    // Backdrop click closes: only when both press and release land outside the panel (not the end of a drag).
    var outside = false;
    dlg.addEventListener("pointerdown", function (e) { outside = e.target === dlg; });
    dlg.addEventListener("click", function (e) { if (outside && e.target === dlg) dlg.close(); });
    dlg.querySelector(".hg-inspect__bar").addEventListener("click", function (e) {
      var b = e.target.closest("button"), a = b && b.getAttribute("data-a"), r = stage.getBoundingClientRect();
      if (a === "close") dlg.close(); else if (a === "fit") fit();
      else if (a) zoom(a === "in" ? 1.25 : 0.8, r.width / 2, r.height / 2);
    });
    stage.addEventListener("wheel", function (e) {
      e.preventDefault();
      var r = stage.getBoundingClientRect();
      zoom(Math.exp(-e.deltaY * (e.deltaMode ? 0.05 : 0.0015)), e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });
    var drag = null;
    stage.addEventListener("pointerdown", function (e) { drag = [e.clientX - x, e.clientY - y]; stage.setPointerCapture(e.pointerId); });
    stage.addEventListener("pointermove", function (e) { if (drag) { x = e.clientX - drag[0]; y = e.clientY - drag[1]; apply(); } });
    stage.addEventListener("pointerup", function () { drag = null; });
    stage.addEventListener("dblclick", fit);
    dlg.addEventListener("close", function () { layer.innerHTML = ""; });
    document.body.appendChild(dlg);
  }
  function inspect(node) {
    if (!node) return;
    viewer();
    var c = node.cloneNode(true);
    if (c.tagName.toLowerCase() === "svg") {
      var vb = node.viewBox.baseVal, b = node.getBoundingClientRect();
      w = vb && vb.width ? vb.width : b.width; h = vb && vb.height ? vb.height : b.height;
      c.removeAttribute("style"); c.setAttribute("width", w); c.setAttribute("height", h);
    } else {
      w = node.naturalWidth || node.width; h = node.naturalHeight || node.height;
      c.removeAttribute("style"); c.width = w; c.height = h;
    }
    layer.innerHTML = ""; layer.appendChild(c);
    dlg.showModal(); fit();
  }
  function button(fig, target) {
    var b = document.createElement("button");
    b.type = "button"; b.className = "hg-inspect-btn"; b.title = "Inspect"; b.setAttribute("aria-label", "Inspect figure");
    b.innerHTML = ICON;
    b.addEventListener("click", function () { inspect(target()); });
    fig.appendChild(b);
  }

  // ---- Content images (not the landing hero).
  document.querySelectorAll(".md-content article img").forEach(function (img) {
    if (img.closest(".hg-hero")) return;
    var fig = document.createElement("span");
    fig.className = "hg-figure hg-figure--img";
    img.replaceWith(fig); fig.appendChild(img);
    button(fig, function () { return img; });
  });

  // ---- Diagrams.
  var blocks = document.querySelectorAll("pre.hg-diagram");
  if (!blocks.length) return;
  var sources = [];
  blocks.forEach(function (pre) {
    var fig = document.createElement("div"), div = document.createElement("div");
    fig.className = "hg-figure";
    div.className = "hg-diagram-out";
    fig.appendChild(div);
    pre.replaceWith(fig);
    button(fig, function () { return div.querySelector("svg"); });
    sources.push([div, pre.textContent]);
  });

  function theme() {
    var dark = document.body.getAttribute("data-md-color-scheme") === "slate";
    return {
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      themeVariables: {
        fontFamily: '"IBM Plex Sans", sans-serif',
        background: "transparent",
        primaryColor: dark ? "#1b1815" : "#ebe6db",
        primaryTextColor: dark ? "#ece6da" : "#1b1917",
        primaryBorderColor: dark ? "#756f65" : "#8a8378",
        lineColor: dark ? "#aaa397" : "#5f594f",
        edgeLabelBackground: dark ? "#12100e" : "#f4f1ea",
        clusterBkg: "transparent",
      },
    };
  }

  function draw() {
    mermaid.initialize(theme());
    sources.forEach(function (src, i) {
      mermaid.render("hgd" + Date.now() + i, src[1]).then(function (r) { src[0].innerHTML = r.svg; });
    });
  }

  var sc = document.createElement("script");
  sc.src = new URL("assets/js/mermaid.min.js", window.__md_scope || document.baseURI).href;
  sc.onload = function () {
    draw();
    new MutationObserver(draw).observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
  };
  document.head.appendChild(sc);
})();
