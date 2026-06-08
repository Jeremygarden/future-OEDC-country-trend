import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('createApp bootstrap', () => {
  it('enables CORS preflight on health route', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'OPTIONS',
      url: '/api/v1/health',
      headers: {
        origin: 'https://example.com',
        'access-control-request-method': 'GET'
      }
    });

    expect(response.statusCode).toBe(204);
    expect(response.headers['access-control-allow-origin']).toBe('https://example.com');

    await app.close();
  });

  it('returns 404 for unknown api route', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/missing'
    });

    expect(response.statusCode).toBe(404);

    await app.close();
  });
});
