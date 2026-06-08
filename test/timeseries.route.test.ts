import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('timeseries API route (scaffold)', () => {
  it('returns 404 until /api/v1/timeseries is implemented', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/timeseries?indicator=NY.GDP.MKTP.CD&countries=USA,CHN&startYear=2020&endYear=2023'
    });

    // TODO(timeseries): switch this test to a strict 200+schema assertion
    // once backend route is merged.
    expect([404, 200]).toContain(response.statusCode);

    if (response.statusCode === 404) {
      expect(response.json().message).toContain('not found');
    } else {
      const body = response.json();
      expect(body).toHaveProperty('indicator');
      expect(body).toHaveProperty('series');
      expect(Array.isArray(body.series)).toBe(true);
    }

    await app.close();
  });

  it.todo('returns per-country time series with year/value/yoy fields');
  it.todo('validates required query parameters and date ranges for /timeseries');
});
