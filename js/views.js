(function () {
  var layer = document.getElementById("views-layer");
  var body = document.getElementById("views-body");
  var title = document.getElementById("views-title");
  var kicker = document.getElementById("views-kicker");
  if (!layer || !body) return;

  document.documentElement.classList.add("has-views-js");

  function articleRoot(el) {
    return el.closest("article") || el.parentElement;
  }

  function headline(article) {
    var h = article.querySelector(".lead-hed, .story-hed, h1, h2");
    return h ? h.textContent.trim() : "Two views";
  }

  function kickerText(article) {
    var k = article.querySelector(".kicker");
    return k ? k.textContent.trim() : "";
  }

  function openFrom(btn) {
    var article = articleRoot(btn);
    var frames = article.querySelector(".frames");
    if (!frames) return;
    kicker.textContent = kickerText(article);
    title.textContent = headline(article);
    body.innerHTML = "";
    body.appendChild(frames.cloneNode(true)).removeAttribute("hidden");
    var clone = body.querySelector(".frames");
    if (clone) clone.hidden = false;
    layer.hidden = false;
    document.body.classList.add("views-open");
    var closeBtn = layer.querySelector(".views-close");
    if (closeBtn) closeBtn.focus();
  }

  function close() {
    layer.hidden = true;
    body.innerHTML = "";
    document.body.classList.remove("views-open");
  }

  document.addEventListener("click", function (e) {
    var open = e.target.closest("[data-open-views]");
    if (open) {
      e.preventDefault();
      openFrom(open);
      return;
    }
    if (e.target.closest("[data-views-close]")) {
      close();
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !layer.hidden) close();
  });
})();
