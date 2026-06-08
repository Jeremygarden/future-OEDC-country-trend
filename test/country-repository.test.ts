import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { CountryRepository } from '../src/services/country-repository.js';

describe('CountryRepository', () => {
  it('loads fallback in-memory stats when COUNTRY_STATS_PATH is not set', async () => {
    const previous = process.env.COUNTRY_STATS_PATH;
    delete process.env.COUNTRY_STATS_PATH;

    const repository = new CountryRepository();
    const data = await repository.list();

    expect(data.length).toBeGreaterThan(1);

    if (previous) process.env.COUNTRY_STATS_PATH = previous;
  });

  it('loads and validates JSON file when COUNTRY_STATS_PATH is set', async () => {
    const previous = process.env.COUNTRY_STATS_PATH;
    process.env.COUNTRY_STATS_PATH = path.resolve('fixtures/countries.sample.json');

    const repository = new CountryRepository();
    const data = await repository.list();

    expect(data).toHaveLength(2);
    expect(data[0].country).toBe('Testland');

    if (previous) process.env.COUNTRY_STATS_PATH = previous;
    else delete process.env.COUNTRY_STATS_PATH;
  });
});
