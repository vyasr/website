(() => {
  const header = document.querySelector(".site-header");
  const navToggle = document.querySelector(".nav-toggle");

  if (navToggle && header) {
    navToggle.addEventListener("click", () => {
      const isOpen = header.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  }

  document.querySelectorAll(".submenu-toggle").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      const item = button.closest(".nav-item");
      if (!item) {
        return;
      }
      const isOpen = item.classList.toggle("submenu-open");
      button.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  });
})();
