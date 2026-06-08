import type { CountryStat } from './dashboard.js';
export type { CountryStat } from './dashboard.js';

export type SummaryItem = [value: string, label: string];

export interface RenderFormatters {
  population: (n: number) => string;
  currency: (n: number) => string;
  number: (n: number) => string;
}

export function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    };
    return entities[character];
  });
}

export function renderSummary(stats: SummaryItem[]): string {
  return stats
    .map(([value, label]) => `<article class="stat"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></article>`)
    .join('');
}

export function renderChart(items: CountryStat[], formatCurrency: (n: number) => string): string {
  const topItems = items.slice(0, 8);
  if (!topItems.length) {
    return '<p>No countries match the current filters.</p>';
  }

  const max = Math.max(...topItems.map((item) => item.gdpPerCapita), 1);

  return topItems
    .map((item) => {
      const width = Math.max(4, (item.gdpPerCapita / max) * 100);
      const safeWidth = Number.isFinite(width) ? Math.min(100, Math.max(0, width)) : 4;
      const country = escapeHtml(item.country);
      return `<div class="bar-row">\n      <span class="bar-label" title="${country}">${country}</span>\n      <span class="bar-track"><span class="bar-fill" style="width:${safeWidth}%"></span></span>\n      <span class="bar-value">${escapeHtml(formatCurrency(item.gdpPerCapita))}</span>\n    </div>`;
    })
    .join('');
}

export function renderRows(items: CountryStat[], formatters: RenderFormatters): string {
  return items
    .map(
      (item) => `<tr>\n    <th scope="row">${escapeHtml(item.country)}</th>\n    <td>${escapeHtml(item.region)}</td>\n    <td class="numeric">${escapeHtml(formatters.population(item.population))}</td>\n    <td class="numeric">${escapeHtml(formatters.currency(item.gdpPerCapita))}</td>\n    <td class="numeric">${escapeHtml(formatters.number(item.lifeExpectancy))}</td>\n    <td class="numeric">${escapeHtml(formatters.number(item.internetUsers))}%</td>\n    <td class="numeric">${escapeHtml(formatters.number(item.co2PerCapita))}</td>\n  </tr>`
    )
    .join('');
}
