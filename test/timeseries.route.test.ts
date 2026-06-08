import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('timeseries API route (scaffold)', () => {
  it('returns 404 until /api/v1/timeseries is implemented, otherwise validates response shape', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/timeseries?indicator=GDP&country=US&fromYear=2020&toYear=2023'
    });

    expect([404, 200]).toContain(response.statusCode);

    if (response.statusCode === 404) {
      expect(response.json().message).toContain('not found');
    } else {
      const body = response.json();
      expect(body.total).toBeTypeOf('number');
      expect(body.query).toBeTypeOf('object');
      expect(Array.isArray(body.items)).toBe(true);

      if (body.items.length > 0) {
        expect(body.items[0]).toHaveProperty('countryCode');
        expect(body.items[0]).toHaveProperty('indicator');
        expect(body.items[0]).toHaveProperty('year');
        expect(body.items[0]).toHaveProperty('value');
      }
    }

    await app.close();
  });

  it.todo('returns per-country time series with year/value/yoy fields');
  it.todo('validates required query parameters and date ranges for /timeseries');
});
