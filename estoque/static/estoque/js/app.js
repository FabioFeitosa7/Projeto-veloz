document.querySelectorAll("[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    const message = form.dataset.confirm;
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });
});

const menuButton = document.querySelector(".menu-button");
const mainMenu = document.querySelector("#menu-principal");

if (menuButton && mainMenu) {
  menuButton.addEventListener("click", () => {
    const expanded = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!expanded));
    mainMenu.classList.toggle("menu-open", !expanded);
  });
}
