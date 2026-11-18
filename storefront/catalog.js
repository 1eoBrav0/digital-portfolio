"use strict";

const models = [
  { id: "linea-01", name: "Штрих 01", group: "shelf", type: "Полочная", finish: "Мел", power: "40 Вт", range: "65–20 000 Гц", size: "24 × 16 × 17 см", connection: "Клеммы", price: 16900, alt: "Светлая полочная колонка с перфорированной решёткой" },
  { id: "field-02", name: "Тембр 02", group: "shelf", type: "Полочная", finish: "Орех", power: "60 Вт", range: "52–22 000 Гц", size: "31 × 19 × 22 см", connection: "Клеммы", price: 24900, alt: "Колонка в отделке из ореха с двумя открытыми динамиками" },
  { id: "axis-03", name: "Ось 03", group: "floor", type: "Напольная", finish: "Графит", power: "120 Вт", range: "36–22 000 Гц", size: "97 × 20 × 28 см", connection: "Клеммы", price: 42900, alt: "Высокая графитовая колонка с тремя открытыми динамиками" },
  { id: "forma-04", name: "Контур 04", group: "floor", type: "Напольная", finish: "Ясень", power: "90 Вт", range: "42–21 000 Гц", size: "88 × 18 × 24 см", connection: "Клеммы", price: 37900, alt: "Напольная колонка из светлого ясеня с тканевой решёткой" },
  { id: "pulse-05", name: "Импульс 05", group: "compact", type: "Компактная", finish: "Гранат", power: "30 Вт", range: "70–19 000 Гц", size: "13 × 28 × 12 см", connection: "Bluetooth, AUX", price: 12900, alt: "Невысокая горизонтальная колонка с бордовой тканевой решёткой" }
];
const priceFormat = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });
const grid = document.getElementById("product-grid");
const dialog = document.getElementById("comparison");
const body = document.getElementById("comparison-body");
const count = document.getElementById("selection-count");
const selected = new Set();
let filter = "all";
let currentSlide = 1;

function productImage(model) {
  return "assets/" + model.id + ".jpg";
}

function selectionLabel(model) {
  return (selected.has(model.id) ? "Убрать из сравнения" : "Добавить к сравнению") + " — " + model.name;
}

function updatePick(button, model) {
  const chosen = selected.has(model.id);
  button.setAttribute("aria-pressed", String(chosen));
  button.setAttribute("aria-label", selectionLabel(model));
  button.title = selectionLabel(model);
  button.textContent = chosen ? "✓" : "+";
}

function renderCatalog() {
  const visible = filter === "all" ? models : models.filter(model => model.group === filter);
  grid.replaceChildren();
  for (const model of visible) {
    const card = document.createElement("article");
    card.className = "product";
    card.innerHTML = `<div class="product-photo"><img src="${productImage(model)}" width="768" height="512" alt="${model.alt}"><button type="button" class="pick" data-id="${model.id}"></button></div>
      <p class="card-type">${model.type} акустика</p>
      <div class="card-line"><h3>${model.name}</h3><span class="price">${priceFormat.format(model.price)}</span></div>
      <p class="card-spec">${model.finish} · ${model.power}</p>`;
    updatePick(card.querySelector(".pick"), model);
    grid.append(card);
  }
  document.getElementById("result-count").textContent = "Показано моделей: " + visible.length;
}

const metrics = [
  ["Тип", model => model.type],
  ["Мощность", model => model.power],
  ["Частоты", model => model.range],
  ["В × Ш × Г", model => model.size],
  ["Подключение", model => model.connection],
  ["Отделка", model => model.finish],
  ["Цена за штуку", model => priceFormat.format(model.price)]
];

function renderComparison() {
  const items = [...selected].map(id => models.find(model => model.id === id));
  if (!items.length) {
    body.innerHTML = '<p class="dialog-message">Выберите две или несколько колонок кнопкой «+» на карточке каждой модели.</p>';
    return;
  }
  const heading = items.map(model => `<th scope="col"><img src="${productImage(model)}" alt="">${model.name}
    <button type="button" class="remove" data-id="${model.id}" aria-label="Убрать из сравнения — ${model.name}">Убрать</button></th>`).join("");
  const rows = metrics.map(([label, value]) =>
    `<tr><th scope="row">${label}</th>${items.map(model => "<td>" + value(model) + "</td>").join("")}</tr>`
  ).join("");
  body.innerHTML = (items.length === 1 ? '<p class="dialog-message">Добавьте ещё одну модель, чтобы сопоставить характеристики.</p>' : "") +
    `<div class="table-scroll" tabindex="0" role="region" aria-label="Таблица сравнения"><table aria-label="Характеристики выбранных моделей">
    <thead><tr><th scope="col">Модель</th>${heading}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

function toggleSelection(id) {
  const model = models.find(item => item.id === id);
  if (!model) return;
  if (selected.has(id)) selected.delete(id);
  else selected.add(id);
  count.textContent = String(selected.size);
  const button = grid.querySelector('[data-id="' + id + '"]');
  if (button) updatePick(button, model);
  document.getElementById("selection-announcement").textContent = model.name +
    (selected.has(id) ? " добавлена в сравнение." : " убрана из сравнения.") + " Выбрано моделей: " + selected.size;
}

function nextSlide(step) {
  currentSlide = (currentSlide + step + models.length) % models.length;
  const model = models[currentSlide];
  const image = document.getElementById("feature-image");
  image.src = productImage(model);
  image.alt = model.alt;
  document.getElementById("feature-title").textContent = model.name;
  document.getElementById("feature-finish").textContent = model.finish;
  document.getElementById("slide-index").textContent = String(currentSlide + 1).padStart(2,"0") + " / 05";
  document.getElementById("slide-announcement").textContent = model.name + ", " + model.finish + ". Модель " + (currentSlide + 1) + " из " + models.length;
}

document.querySelector(".filterbar").addEventListener("click", event => {
  const choice = event.target.closest("button[data-filter]");
  if (!choice) return;
  filter = choice.dataset.filter;
  for (const button of choice.parentElement.querySelectorAll("button")) {
    button.setAttribute("aria-pressed", String(button === choice));
  }
  renderCatalog();
});
grid.addEventListener("click", event => {
  const button = event.target.closest(".pick");
  if (button) toggleSelection(button.dataset.id);
});
body.addEventListener("click", event => {
  const button = event.target.closest(".remove");
  if (!button) return;
  toggleSelection(button.dataset.id);
  renderComparison();
  (body.querySelector(".remove") || document.getElementById("back-to-catalog")).focus();
});
document.getElementById("prev-slide").addEventListener("click", () => nextSlide(-1));
document.getElementById("next-slide").addEventListener("click", () => nextSlide(1));
document.getElementById("open-compare").addEventListener("click", () => {
  renderComparison();
  dialog.showModal();
  document.getElementById("close-dialog").focus();
});
document.getElementById("close-dialog").addEventListener("click", () => dialog.close());
document.getElementById("back-to-catalog").addEventListener("click", () => {
  dialog.close();
  document.querySelector(".filterbar button[aria-pressed='true']").focus();
  document.getElementById("catalog").scrollIntoView();
});
dialog.addEventListener("click", event => {
  if (event.target !== dialog) return;
  const rect = dialog.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
});
renderCatalog();
