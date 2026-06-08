import { describe, expect, it } from 'vitest';
import { average, DEFAULT_STATE, filterAndSortCountries, getCountries, isCountryStat, type CountryStat } from '../src/core/dashboard.js';

const data: CountryStat[] = [
  { country: 'Japan', region: 'East Asia', population: 124500000, gdpPerCapita: 33815, lifeExpectancy: 84.5, internetUsers: 94, co2PerCapita: 8.6 },
  { country: 'China', region: 'East Asia', population: 1412000000, gdpPerCapita: 12720, lifeExpectancy: 78.2, internetUsers: 76, co2PerCapita: 8.0 },
  { country: 'Canada', region: 'North America', population: 39290000, gdpPerCapita: 54966, lifeExpectancy: 82.6, internetUsers: 95, co2PerCapita: 14.2 }
];

describe('dashboard core filtering and sorting', () => {
  it('returns only valid countries from unknown datasets', () => {
    expect(getCountries(null)).toEqual([]);
    expect(getCountries({})).toEqual([]);
    expect(getCountries([data[0], null, { country: '', region: 'Nowhere', population: Number.NaN }])).toEqual([data[0]]);
    expect(isCountryStat(data[0])).toBe(true);
    expect(isCountryStat({ ...data[0], gdpPerCapita: '33815' })).toBe(false);
  });

  it('filters by region and search term, then sorts by selected metric descending', () => {
    const state = { ...DEFAULT_STATE, region: 'East Asia', search: 'a', sortBy: 'gdpPerCapita' as const };
    const result = filterAndSortCountries(data, state);

    expect(result.map((item) => item.country)).toEqual(['Japan', 'China']);
  });

  it('uses country name alphabetical order to break metric ties', () => {
    const tied: CountryStat[] = [
      { country: 'Brazil', region: 'Latin America', population: 200, gdpPerCapita: 10, lifeExpectancy: 70, internetUsers: 80, co2PerCapita: 2 },
      { country: 'Argentina', region: 'Latin America', population: 100, gdpPerCapita: 10, lifeExpectancy: 75, internetUsers: 82, co2PerCapita: 2 }
    ];

    const result = filterAndSortCountries(tied, { ...DEFAULT_STATE, sortBy: 'gdpPerCapita' });
    expect(result.map((item) => item.country)).toEqual(['Argentina', 'Brazil']);
  });

  it('calculates average and returns 0 for empty arrays', () => {
    expect(average(data, 'internetUsers')).toBeCloseTo((94 + 76 + 95) / 3);
    expect(average([], 'population')).toBe(0);
  });
});
