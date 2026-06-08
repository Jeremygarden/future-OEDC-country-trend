import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('forecast API route (scaffold)', () => {
  it('returns 404 until /api/v1/forecast is implemented, otherwise validates numerical payload', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/forecast?indicator=GDP&country=US&startYear=2020&endYear=2022&horizon=2'
    });

    expect([404, 200]).toContain(response.statusCode);

    if (response.statusCode === 404) {
      expect(response.json().message).toContain('not found');
    } else {
      const body = response.json();
      expect(body).toHaveProperty('indicator');
      expect(body).toHaveProperty('country');
      expect(Array.isArray(body.history)).toBe(true);
      expect(Array.isArray(body.forecast)).toBe(true);

      for (const row of body.forecast) {
        expect(typeof row.year).toBe('number');
        expect(typeof row.value).toBe('number');
      }
    }

    await app.close();
  });

  it.todo('computes numerically correct linear forecast from a known history');
  it.todo('handles edge cases: missing history points, negative horizon, and invalid years');
});
