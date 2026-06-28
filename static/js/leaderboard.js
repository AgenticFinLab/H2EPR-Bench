const leaderboardTable = document.querySelector("#leaderboard-table");
const leaderboardBody = leaderboardTable?.querySelector("tbody");

const columns = [
  { key: "system", label: "System", type: "text" },
  { key: "schema_valid_rate_pct", label: "Valid outputs (%)", type: "number", decimals: 1 },
  { key: "QualityScore", label: "QualityScore", type: "number", decimals: 2 },
  { key: "S_structure", label: "Structure", type: "number", decimals: 2 },
  { key: "S_temporal", label: "Temporal", type: "number", decimals: 2 },
  { key: "S_mechanistic", label: "Mechanistic", type: "number", decimals: 2 },
  { key: "S_evidence", label: "Evidence", type: "number", decimals: 2 },
];

let leaderboardRows = [];
let sortState = { key: "QualityScore", direction: "desc" };

function formatValue(column, value) {
  if (column.type === "number") {
    return Number(value).toFixed(column.decimals);
  }
  return value;
}

function compareRows(left, right, column) {
  const leftValue = left[column.key];
  const rightValue = right[column.key];
  if (column.type === "number") {
    return Number(leftValue) - Number(rightValue);
  }
  return String(leftValue).localeCompare(String(rightValue));
}

function sortedRows() {
  const column = columns.find((item) => item.key === sortState.key);
  const direction = sortState.direction === "asc" ? 1 : -1;
  return [...leaderboardRows].sort((left, right) => compareRows(left, right, column) * direction);
}

function renderHeader() {
  const headerRow = leaderboardTable.querySelector("thead tr");
  headerRow.innerHTML = "";

  columns.forEach((column) => {
    const cell = document.createElement("th");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "sort-button";
    button.textContent = column.label;
    button.dataset.key = column.key;
    button.setAttribute("aria-label", `Sort by ${column.label}`);

    if (sortState.key === column.key) {
      button.classList.add("active");
      button.dataset.direction = sortState.direction;
      button.textContent = `${column.label} ${sortState.direction === "asc" ? "↑" : "↓"}`;
    }

    button.addEventListener("click", () => {
      if (sortState.key === column.key) {
        sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
      } else {
        sortState = { key: column.key, direction: column.type === "number" ? "desc" : "asc" };
      }
      renderLeaderboard();
    });

    cell.appendChild(button);
    headerRow.appendChild(cell);
  });
}

function renderBody() {
  leaderboardBody.innerHTML = "";
  sortedRows().forEach((row, index) => {
    const tableRow = document.createElement("tr");
    tableRow.dataset.rank = String(index + 1);
    columns.forEach((column) => {
      const cell = document.createElement("td");
      cell.textContent = formatValue(column, row[column.key]);
      if (column.type === "number") {
        cell.classList.add("numeric");
      }
      tableRow.appendChild(cell);
    });
    leaderboardBody.appendChild(tableRow);
  });
}

function renderLeaderboard() {
  renderHeader();
  renderBody();
}

async function loadLeaderboard() {
  if (!leaderboardTable || !leaderboardBody) {
    return;
  }

  try {
    const response = await fetch("data/direct_llm_16model_main_results.json");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    leaderboardRows = await response.json();
    renderLeaderboard();
  } catch (error) {
    leaderboardBody.innerHTML = `<tr><td colspan="${columns.length}">Unable to load leaderboard data.</td></tr>`;
    console.error("Leaderboard load failed:", error);
  }
}

loadLeaderboard();
