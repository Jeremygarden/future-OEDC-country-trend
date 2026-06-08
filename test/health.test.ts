import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('GET /api/v1/health', () => {
  it('returns healthy status payload', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/health'
    });

    expect(response.statusCode).toBe(200);

    const body = response.json();
    expect(body.status).toBe('ok');
    expect(body.service).toBe('future-oedc-country-trend-backend');
    expect(Number.isNaN(Date.parse(body.timestamp))).toBe(false);

    await app.close();
  });

  it('keeps route under /api/v1 prefix', async () => {
    const app = createApp();

    const noPrefix = await app.inject({
      method: 'GET',
      url: '/health'
    });

    expect(noPrefix.statusCode).toBe(404);

    await app.close();
  });
});
