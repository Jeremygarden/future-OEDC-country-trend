import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

describe('metrics route', () => {
  it('returns observability counters and uptime', async () => {
    const app = createApp();

    await app.inject({ method: 'GET', url: '/api/v1/health' });
    await app.inject({ method: 'GET', url: '/api/v1/countries?limit=1' });

    const response = await app.inject({ method: 'GET', url: '/api/v1/metrics' });
    expect(response.statusCode).toBe(200);

    const body = response.json();
    expect(body.requestsTotal).toBeGreaterThanOrEqual(2);
    expect(body.errorsTotal).toBeGreaterThanOrEqual(0);
    expect(body.uptimeSeconds).toBeGreaterThanOrEqual(0);

    await app.close();
  });
});
