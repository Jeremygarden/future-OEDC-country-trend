import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('indicators + compare API routes', () => {
  it('handles /api/v1/indicators readiness', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/indicators?search=gdp'
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.totalCountries).toBeGreaterThan(0);
    expect(Array.isArray(body.items)).toBe(true);
    expect(body.items[0]).toHaveProperty('countryCode');
    expect(body.items[0]).toHaveProperty('indicators');

    await app.close();
  });

  it('handles /api/v1/compare readiness', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/compare?indicator=NY.GDP.MKTP.CD&countries=USA,CHN,JPN'
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body).toBeTypeOf('object');
    expect(body.countries).toEqual(['USA', 'CHN', 'JPN']);
    expect(body.items.map((item: { countryCode: string }) => item.countryCode)).toEqual(['USA', 'CHN', 'JPN']);

    await app.close();
  });

  it('validates malformed indicator/country query combinations', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/compare?countries=US'
    });

    expect(response.statusCode).toBe(400);
    expect(response.json()).toMatchObject({
      code: 'INVALID_COMPARE_QUERY',
      message: 'Invalid compare query parameters'
    });

    await app.close();
  });
});
