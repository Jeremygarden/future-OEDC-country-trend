import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('countries API routes', () => {
  it('returns paginated countries with total count', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/countries?region=East%20Asia&sortBy=gdpPerCapita&limit=1'
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.total).toBe(2);
    expect(body.limit).toBe(1);
    expect(body.items).toHaveLength(1);
    expect(body.items[0].country).toBe('Japan');

    await app.close();
  });

  it('returns country summary metrics', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/countries/summary?region=North%20America'
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.totalCountries).toBe(2);
    expect(body.totalPopulation).toBeGreaterThan(0);
    expect(body.averageGdpPerCapita).toBeGreaterThan(0);

    await app.close();
  });

  it('returns 400 for invalid query parameters', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/countries?sortBy=unknown&limit=0'
    });

    expect(response.statusCode).toBe(400);
    expect(response.json().message).toContain('Invalid country query parameters');

    await app.close();
  });
});
