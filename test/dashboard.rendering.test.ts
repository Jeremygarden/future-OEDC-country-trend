import { describe, expect, it } from 'vitest';
import { type CountryStat } from '../src/core/dashboard.js';
import { renderChart, renderRows, renderSummary, type SummaryItem } from '../src/core/rendering.js';

const items: CountryStat[] = [
  { country: 'Canada', region: 'North America', population: 39290000, gdpPerCapita: 54966, lifeExpectancy: 82.6, internetUsers: 95, co2PerCapita: 14.2 },
  { country: 'Japan', region: 'East Asia', population: 124500000, gdpPerCapita: 33815, lifeExpectancy: 84.5, internetUsers: 94, co2PerCapita: 8.6 }
];

describe('dashboard rendering helpers', () => {
  it('renders summary cards html', () => {
    const summary: SummaryItem[] = [
      ['100M', 'Total population'],
      ['$10,000', 'Average GDP per capita']
    ];

    const html = renderSummary(summary);
    expect(html).toContain('<article class="stat">');
    expect(html).toContain('Total population');
  });

  it('renders chart rows with min width and empty state', () => {
    const html = renderChart(items, (n) => `$${n.toFixed(0)}`);
    expect(html).toContain('bar-row');
    expect(html).toContain('style="width:100%"');

    const empty = renderChart([], (n) => `${n}`);
    expect(empty).toContain('No countries match the current filters.');
  });

  it('renders table rows with formatted numeric values', () => {
    const html = renderRows(
      items,
      {
        population: (n) => `${n}`,
        currency: (n) => `$${n}`,
        number: (n) => `${n}`
      }
    );

    expect(html).toContain('<th scope="row">Canada</th>');
    expect(html).toContain('<td>North America</td>');
    expect(html).toContain('95%');
  });
});
