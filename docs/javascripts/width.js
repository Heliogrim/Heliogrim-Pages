// Block / fluid width switch in the header. The saved choice is applied before paint by overrides/main.html.
(function () {
  var root = document.documentElement, key = "hg-width";
  var btn = document.createElement("button");
  btn.className = "md-header__button md-icon hg-width";
  btn.type = "button";
  btn.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 11H15V8L19 12L15 16V13H9V16L5 12L9 8V11M2 5H4V19H2V5M20 5H22V19H20V5Z"/></svg>';
  function sync() {
    var fluid = root.getAttribute("data-hg-width") === "fluid";
    var label = fluid ? "Use block width" : "Use full browser width";
    btn.title = label; btn.setAttribute("aria-label", label); btn.setAttribute("aria-pressed", String(fluid));
  }
  btn.addEventListener("click", function () {
    var fluid = root.getAttribute("data-hg-width") !== "fluid";
    if (fluid) root.setAttribute("data-hg-width", "fluid"); else root.removeAttribute("data-hg-width");
    try { fluid ? localStorage.setItem(key, "fluid") : localStorage.removeItem(key); } catch (e) {}
    sync();
  });
  var anchor = document.querySelector(".md-header__option") || document.querySelector(".md-header__button[for=__search]");
  if (anchor) { anchor.parentNode.insertBefore(btn, anchor); sync(); }
})();
