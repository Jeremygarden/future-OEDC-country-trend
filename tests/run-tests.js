const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const requiredFiles = ["index.html", "styles.css", "app.js", "data/countries.js"];
for (const file of requiredFiles) {
  const fullPath = path.join(root, file);
  if (!fs.existsSync(fullPath)) throw new Error(`Missing ${file}`);
  if (!fs.readFileSync(fullPath, "utf8").trim()) throw new Error(`${file} is empty`);
}

const sandbox = { window: {} };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(root, "data/countries.js"), "utf8"), sandbox);
const data = sandbox.window.COUNTRY_STATS;
if (!Array.isArray(data) || data.length < 10) throw new Error("Expected at least 10 country records");

const names = new Set();
for (const item of data) {
  for (const key of ["country", "region", "population", "gdpPerCapita", "lifeExpectancy", "internetUsers", "co2PerCapita"]) {
    if (!(key in item)) throw new Error(`Missing ${key} on ${JSON.stringify(item)}`);
  }
  if (names.has(item.country)) throw new Error(`Duplicate country ${item.country}`);
  names.add(item.country);
  if (item.population <= 0 || item.gdpPerCapita <= 0 || item.lifeExpectancy <= 0) {
    throw new Error(`Invalid positive metric for ${item.country}`);
  }
}

const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
for (const selector of ["search", "regionFilter", "sortBy", "summary", "chart", "countryRows"]) {
  if (!html.includes(`id="${selector}"`)) throw new Error(`Missing #${selector}`);
}

console.log("All dashboard checks passed.");
