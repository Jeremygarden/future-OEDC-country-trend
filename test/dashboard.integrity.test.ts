import { describe, expect, it } from 'vitest';
import { DEFAULT_STATE, filterAndSortCountries, getCountries, type CountryStat } from '../src/core/dashboard.js';

describe('dashboard data integrity behavior', () => {
  it('returns only valid records from array input and [] for non-arrays', () => {
    const sample = [
      { country: 'A', region: 'R', population: 1, gdpPerCapita: 2, lifeExpectancy: 3, internetUsers: 4, co2PerCapita: 5 },
      { country: 'Bad', region: 'R', population: Number.NaN, gdpPerCapita: 2, lifeExpectancy: 3, internetUsers: 4, co2PerCapita: 5 }
    ];

    expect(getCountries(sample)).toEqual([
      { country: 'A', region: 'R', population: 1, gdpPerCapita: 2, lifeExpectancy: 3, internetUsers: 4, co2PerCapita: 5 }
    ]);
    expect(getCountries('bad-input')).toEqual([]);
  });

  it('does not mutate the original input order while sorting filtered results', () => {
    const input: CountryStat[] = [
      { country: 'Brazil', region: 'Latin America', population: 200, gdpPerCapita: 10, lifeExpectancy: 70, internetUsers: 80, co2PerCapita: 2 },
      { country: 'Argentina', region: 'Latin America', population: 100, gdpPerCapita: 40, lifeExpectancy: 75, internetUsers: 82, co2PerCapita: 2 }
    ];

    const originalOrder = input.map((item) => item.country);
    const result = filterAndSortCountries(input, {
      ...DEFAULT_STATE,
      sortBy: 'gdpPerCapita'
    });

    expect(result.map((item) => item.country)).toEqual(['Argentina', 'Brazil']);
    expect(input.map((item) => item.country)).toEqual(originalOrder);
  });
});
