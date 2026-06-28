const navLinks = Array.from(document.querySelectorAll(".section-nav a"));

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    navLinks.forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

const ganttMainImage = document.querySelector("#gantt-main-image");
const ganttMainCaption = document.querySelector("#gantt-main-caption");
const ganttButtons = Array.from(document.querySelectorAll(".gantt-thumb"));

ganttButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (!ganttMainImage || !ganttMainCaption) return;
    const src = button.dataset.src;
    const alt = button.dataset.alt;
    const caption = button.dataset.caption;
    if (!src || !alt || !caption) return;

    ganttMainImage.src = src;
    ganttMainImage.alt = alt;
    ganttMainCaption.innerHTML = caption;
    ganttButtons.forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
  });
});
