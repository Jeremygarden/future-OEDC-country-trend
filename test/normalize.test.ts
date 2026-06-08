import { describe, expect, it } from 'vitest';
import { normalizeRows } from '../src/core/normalize.js';

describe('normalizeRows', () => {
  it('groups rows by country and metric and sorts years', () => {
    const records = normalizeRows([
      { country_code: 'US', country_name: 'United States', metric: 'gdp', year: 2021, value: 23 },
      { country_code: 'US', country_name: 'United States', metric: 'gdp', year: 2020, value: 21 },
      { country_code: 'JP', country_name: 'Japan', metric: 'gdp', year: 2021, value: 5 }
    ]);

    expect(records).toHaveLength(2);

    const us = records.find((r) => r.countryCode === 'US');
    expect(us?.points.map((p) => p.year)).toEqual([2020, 2021]);
  });

  it('skips malformed rows', () => {
    const records = normalizeRows([
      { country_code: '', country_name: 'X', metric: 'gdp', year: 2021, value: 1 },
      { country_code: 'US', country_name: 'United States', metric: 'gdp', year: 'n/a', value: 1 },
      { country_code: 'US', country_name: 'United States', metric: 'gdp', year: 2021, value: 1 }
    ]);

    expect(records).toHaveLength(1);
    expect(records[0].points).toEqual([{ year: 2021, value: 1 }]);
  });
});
