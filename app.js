const state = {
  search: "",
  region: "all",
  sortBy: "population"
};

const formatters = {
  population: new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }),
  currency: new Intl.NumberFormat("en", { style: "currency", currency: "USD", maximumFractionDigits: 0 }),
  number: new Intl.NumberFormat("en", { maximumFractionDigits: 1 })
};

const els = {
  search: document.querySelector("#search"),
  region: document.querySelector("#regionFilter"),
  sortBy: document.querySelector("#sortBy"),
  summary: document.querySelector("#summary"),
  chart: document.querySelector("#chart"),
  rows: document.querySelector("#countryRows"),
  resultCount: document.querySelector("#resultCount"),
  reset: document.querySelector("#reset")
};

function getCountries() {
  return Array.isArray(window.COUNTRY_STATS) ? window.COUNTRY_STATS : [];
}

function populateRegions() {
  const regions = [...new Set(getCountries().map((item) => item.region))].sort();
  for (const region of regions) {
    const option = document.createElement("option");
    option.value = region;
    option.textContent = region;
    els.region.append(option);
  }
}

function filteredCountries() {
  const search = state.search.trim().toLowerCase();
  return getCountries()
    .filter((item) => state.region === "all" || item.region === state.region)
    .filter((item) => !search || item.country.toLowerCase().includes(search))
    .sort((a, b) => b[state.sortBy] - a[state.sortBy] || a.country.localeCompare(b.country));
}

function average(items, key) {
  if (!items.length) return 0;
  return items.reduce((sum, item) => sum + item[key], 0) / items.length;
}

function clearElement(element) {
  element.replaceChildren();
}

function renderSummary(items) {
  const population = items.reduce((sum, item) => sum + item.population, 0);
  const stats = [
    [formatters.population.format(population), "Total population"],
    [formatters.currency.format(average(items, "gdpPerCapita")), "Average GDP per capita"],
    [`${formatters.number.format(average(items, "lifeExpectancy"))} yrs`, "Average life expectancy"],
    [`${formatters.number.format(average(items, "internetUsers"))}%`, "Average internet access"]
  ];

  clearElement(els.summary);
  for (const [value, label] of stats) {
    const article = document.createElement("article");
    article.className = "stat";

    const strong = document.createElement("strong");
    strong.textContent = value;

    const span = document.createElement("span");
    span.textContent = label;

    article.append(strong, span);
    els.summary.append(article);
  }
}

function renderChart(items) {
  const topItems = items.slice(0, 8);
  const max = Math.max(...topItems.map((item) => item.gdpPerCapita), 1);

  clearElement(els.chart);

  if (!topItems.length) {
    const empty = document.createElement("p");
    empty.textContent = "No countries match the current filters.";
    els.chart.append(empty);
    return;
  }

  for (const item of topItems) {
    const width = Math.max(4, (item.gdpPerCapita / max) * 100);

    const row = document.createElement("div");
    row.className = "bar-row";

    const label = document.createElement("span");
    label.className = "bar-label";
    label.title = item.country;
    label.textContent = item.country;

    const track = document.createElement("span");
    track.className = "bar-track";

    const fill = document.createElement("span");
    fill.className = "bar-fill";
    fill.style.width = `${width}%`;
    track.append(fill);

    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = formatters.currency.format(item.gdpPerCapita);

    row.append(label, track, value);
    els.chart.append(row);
  }
}

function renderRows(items) {
  clearElement(els.rows);

  for (const item of items) {
    const row = document.createElement("tr");
    const cells = [
      ["th", item.country, ""],
      ["td", item.region, ""],
      ["td", formatters.population.format(item.population), "numeric"],
      ["td", formatters.currency.format(item.gdpPerCapita), "numeric"],
      ["td", formatters.number.format(item.lifeExpectancy), "numeric"],
      ["td", `${formatters.number.format(item.internetUsers)}%`, "numeric"],
      ["td", formatters.number.format(item.co2PerCapita), "numeric"]
    ];

    for (const [tag, text, className] of cells) {
      const cell = document.createElement(tag);
      if (tag === "th") cell.scope = "row";
      if (className) cell.className = className;
      cell.textContent = text;
      row.append(cell);
    }

    els.rows.append(row);
  }
}

function render() {
  const items = filteredCountries();
  els.resultCount.textContent = `${items.length} countries`;
  renderSummary(items);
  renderChart(items);
  renderRows(items);
}

els.search.addEventListener("input", (event) => {
  state.search = event.target.value;
  render();
});

els.region.addEventListener("change", (event) => {
  state.region = event.target.value;
  render();
});

els.sortBy.addEventListener("change", (event) => {
  state.sortBy = event.target.value;
  render();
});

els.reset.addEventListener("click", () => {
  state.search = "";
  state.region = "all";
  state.sortBy = "population";
  els.search.value = "";
  els.region.value = "all";
  els.sortBy.value = "population";
  render();
});

populateRegions();
render();

if (typeof module !== "undefined") {
  module.exports = { average };
}
