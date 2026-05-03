(function () {
  function autoResizeTextarea(textarea) {
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 320) + "px";
  }

  function setupTextarea() {
    var ta = document.getElementById("ingredients");
    if (!ta) return;
    ta.addEventListener("input", function () {
      autoResizeTextarea(ta);
      updateChipPreview(ta.value);
    });
    autoResizeTextarea(ta);
    updateChipPreview(ta.value);
  }

  function updateChipPreview(text) {
    var el = document.getElementById("chip-preview");
    if (!el) return;
    var parts = text
      .split(/[,，\n]/)
      .map(function (s) {
        return s.trim();
      })
      .filter(Boolean)
      .slice(0, 8);
    if (!parts.length) {
      el.textContent = "";
      return;
    }
    el.textContent = "Орцууд: " + parts.join(" · ");
  }

  function setupGenerateForm() {
    var form = document.getElementById("generate-form");
    var btn = document.getElementById("generate-btn");
    if (!form || !btn) return;

    form.addEventListener("submit", function (e) {
      var ing = document.getElementById("ingredients");
      var servings = document.getElementById("servings");
      if (ing && !ing.value.trim()) {
        e.preventDefault();
        alert("Гэрт байгаа орцоо бичнэ үү.");
        ing.focus();
        return;
      }
      if (servings && (parseInt(servings.value, 10) || 0) < 1) {
        e.preventDefault();
        alert("Хэдэн хүн идэх вэ? — 1-ээс их тоо оруулна уу.");
        servings.focus();
        return;
      }
      btn.classList.add("loading");
      btn.textContent = "Жор бэлдэж байна…";
    });
  }

  function setupNavToggle() {
    var toggle = document.querySelector(".nav-toggle");
    var nav = document.querySelector(".main-nav");
    if (!toggle || !nav) return;
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupTextarea();
    setupGenerateForm();
    setupNavToggle();
  });
})();
