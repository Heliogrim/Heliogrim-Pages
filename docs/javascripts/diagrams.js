// Renders ```hg-diagram``` blocks with a self-hosted Mermaid. Loads it only on pages that have one.
(function () {
  var blocks = document.querySelectorAll("pre.hg-diagram");
  if (!blocks.length) return;
  var sources = [];
  blocks.forEach(function (pre) {
    var div = document.createElement("div");
    div.className = "hg-diagram-out";
    pre.replaceWith(div);
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
        primaryBorderColor: "#ff6a1a",
        lineColor: dark ? "#aaa397" : "#5f594f",
        edgeLabelBackground: dark ? "#12100e" : "#f4f1ea",
        clusterBkg: "transparent",
      },
    };
  }

  function draw() {
    mermaid.initialize(theme());
    sources.forEach(function (s, i) {
      mermaid.render("hgd" + Date.now() + i, s[1]).then(function (r) { s[0].innerHTML = r.svg; });
    });
  }

  var s = document.createElement("script");
  s.src = new URL("assets/js/mermaid.min.js", window.__md_scope || document.baseURI).href;
  s.onload = function () {
    draw();
    new MutationObserver(draw).observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
  };
  document.head.appendChild(s);
})();
