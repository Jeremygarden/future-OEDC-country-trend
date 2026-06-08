import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('error handler and validation', () => {
  it('returns structured 400 for invalid countries query', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/countries?limit=0'
    });

    expect(response.statusCode).toBe(400);

    const body = response.json();
    expect(body).toMatchObject({
      error: {
        code: 'REQUEST_ERROR',
        statusCode: 400
      }
    });
    expect(body.error.message).toContain('Invalid country query parameters');

    await app.close();
  });

  it('returns structured 404 for missing route', async () => {
    const app = createApp();

    const response = await app.inject({
      method: 'GET',
      url: '/api/v1/does-not-exist'
    });

    expect(response.statusCode).toBe(404);

    const body = response.json();
    expect(body).toMatchObject({
      error: {
        code: 'ROUTE_NOT_FOUND',
        statusCode: 404
      }
    });
    expect(body.error.message).toContain('Route GET:/api/v1/does-not-exist not found');

    await app.close();
  });
});
