const navLinks = Array.from(document.querySelectorAll(".section-nav a"));

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    navLinks.forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

const usecaseMainImage = document.querySelector("#usecase-main-image");
const usecaseKicker = document.querySelector("#usecase-kicker");
const usecaseTitle = document.querySelector("#usecase-title");
const usecaseCopy = document.querySelector("#usecase-copy");
const usecaseButtons = Array.from(document.querySelectorAll(".usecase-switch"));

usecaseButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (!usecaseMainImage || !usecaseKicker || !usecaseTitle || !usecaseCopy) return;
    const src = button.dataset.src;
    const alt = button.dataset.alt;
    const kicker = button.dataset.kicker;
    const title = button.dataset.title;
    const copy = button.dataset.copy;
    if (!src || !alt || !kicker || !title || !copy) return;

    usecaseMainImage.src = src;
    usecaseMainImage.alt = alt;
    usecaseKicker.textContent = kicker;
    usecaseTitle.textContent = title;
    usecaseCopy.textContent = copy;
    usecaseButtons.forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
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
