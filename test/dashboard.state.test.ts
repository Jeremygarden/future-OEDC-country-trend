import { describe, expect, it } from 'vitest';
import { DEFAULT_STATE, filterAndSortCountries, type CountryStat } from '../src/core/dashboard.js';

const data: CountryStat[] = [
  { country: 'Japan', region: 'East Asia', population: 124500000, gdpPerCapita: 33815, lifeExpectancy: 84.5, internetUsers: 94, co2PerCapita: 8.6 },
  { country: 'China', region: 'East Asia', population: 1412000000, gdpPerCapita: 12720, lifeExpectancy: 78.2, internetUsers: 76, co2PerCapita: 8.0 },
  { country: 'Canada', region: 'North America', population: 39290000, gdpPerCapita: 54966, lifeExpectancy: 82.6, internetUsers: 95, co2PerCapita: 14.2 }
];

describe('dashboard state transitions', () => {
  it('resets to default state values', () => {
    const changed = { search: 'ja', region: 'East Asia', sortBy: 'gdpPerCapita' as const };
    const reset = { ...DEFAULT_STATE };

    expect(changed).not.toEqual(reset);
    expect(reset).toEqual({ search: '', region: 'all', sortBy: 'population' });
  });

  it('trims and lowercases search text behavior', () => {
    const result = filterAndSortCountries(data, {
      ...DEFAULT_STATE,
      search: '  JAP  '
    });

    expect(result).toHaveLength(1);
    expect(result[0].country).toBe('Japan');
  });

  it('changes ordering when sortBy changes', () => {
    const byPopulation = filterAndSortCountries(data, {
      ...DEFAULT_STATE,
      sortBy: 'population'
    }).map((item) => item.country);

    const byGdp = filterAndSortCountries(data, {
      ...DEFAULT_STATE,
      sortBy: 'gdpPerCapita'
    }).map((item) => item.country);

    expect(byPopulation).toEqual(['China', 'Japan', 'Canada']);
    expect(byGdp).toEqual(['Canada', 'Japan', 'China']);
  });
});
