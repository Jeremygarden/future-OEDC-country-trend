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

function renderSummary(items) {
  const population = items.reduce((sum, item) => sum + item.population, 0);
  const stats = [
    [formatters.population.format(population), "Total population"],
    [formatters.currency.format(average(items, "gdpPerCapita")), "Average GDP per capita"],
    [`${formatters.number.format(average(items, "lifeExpectancy"))} yrs`, "Average life expectancy"],
    [`${formatters.number.format(average(items, "internetUsers"))}%`, "Average internet access"]
  ];
  els.summary.innerHTML = stats.map(([value, label]) => `<article class="stat"><strong>${value}</strong><span>${label}</span></article>`).join("");
}

function renderChart(items) {
  const topItems = items.slice(0, 8);
  const max = Math.max(...topItems.map((item) => item.gdpPerCapita), 1);
  els.chart.innerHTML = topItems.map((item) => {
    const width = Math.max(4, (item.gdpPerCapita / max) * 100);
    return `<div class="bar-row">
      <span class="bar-label" title="${item.country}">${item.country}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${width}%"></span></span>
      <span class="bar-value">${formatters.currency.format(item.gdpPerCapita)}</span>
    </div>`;
  }).join("") || "<p>No countries match the current filters.</p>";
}

function renderRows(items) {
  els.rows.innerHTML = items.map((item) => `<tr>
    <th scope="row">${item.country}</th>
    <td>${item.region}</td>
    <td class="numeric">${formatters.population.format(item.population)}</td>
    <td class="numeric">${formatters.currency.format(item.gdpPerCapita)}</td>
    <td class="numeric">${formatters.number.format(item.lifeExpectancy)}</td>
    <td class="numeric">${formatters.number.format(item.internetUsers)}%</td>
    <td class="numeric">${formatters.number.format(item.co2PerCapita)}</td>
  </tr>`).join("");
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
