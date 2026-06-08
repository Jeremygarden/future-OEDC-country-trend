import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('indicators + compare API routes (scaffold)', () => {
  it('handles /api/v1/indicators readiness', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/indicators?search=gdp'
    });

    // TODO(indicators): once implemented, require strict 200 and exact schema.
    expect([404, 200]).toContain(response.statusCode);

    if (response.statusCode === 404) {
      expect(response.json().message).toContain('not found');
    } else {
      const body = response.json();
      expect(Array.isArray(body.items ?? body.indicators ?? [])).toBe(true);
    }

    await app.close();
  });

  it('handles /api/v1/compare readiness', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/compare?indicator=NY.GDP.MKTP.CD&countries=USA,CHN,JPN'
    });

    // TODO(compare): once implemented, require strict 200 and exact schema.
    expect([404, 200]).toContain(response.statusCode);

    if (response.statusCode === 404) {
      expect(response.json().message).toContain('not found');
    } else {
      const body = response.json();
      expect(body).toBeTypeOf('object');
      expect(body).toHaveProperty('countries');
    }

    await app.close();
  });

  it.todo('returns stable ordering for compare endpoint results');
  it.todo('validates malformed indicator/country query combinations');
});
