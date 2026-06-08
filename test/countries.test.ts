import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('countries routes', () => {
  it('returns countries sorted by requested metric with pagination', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/countries?sortBy=gdpPerCapita&limit=2&offset=0'
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();

    expect(body.total).toBeGreaterThan(2);
    expect(body.items).toHaveLength(2);
    expect(body.items[0].country).toBe('United States');

    await app.close();
  });

  it('filters by region and returns summary data', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/countries/summary?region=East%20Asia'
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();

    expect(body.totalCountries).toBe(2);
    expect(body.averageInternetUsers).toBeGreaterThan(80);

    await app.close();
  });
});
