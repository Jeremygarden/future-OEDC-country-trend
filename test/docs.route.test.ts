import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('docs route', () => {
  it('returns API endpoint catalog', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/docs'
    });

    expect(response.statusCode).toBe(200);

    const body = response.json();
    expect(body.name).toContain('future-OEDC-country-trend');
    expect(Array.isArray(body.endpoints)).toBe(true);
    expect(body.endpoints.some((endpoint: { path: string }) => endpoint.path === '/api/v1/countries')).toBe(true);

    await app.close();
  });
});
