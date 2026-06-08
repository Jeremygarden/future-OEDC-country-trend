import { describe, expect, it } from 'vitest';
import { createApp } from '../src/app.js';

function isJsonContentType(value: string | undefined) {
  return (value ?? '').includes('application/json');
}

describe('API end-to-end smoke + schema validation', () => {
  it('boots Fastify and validates all core endpoint schemas', async () => {
    const app = createApp();

    const healthRes = await app.inject({ method: 'GET', url: '/api/v1/health' });
    expect(healthRes.statusCode).toBe(200);
    expect(isJsonContentType(healthRes.headers['content-type'] as string | undefined)).toBe(true);
    const health = healthRes.json();
    expect(health).toHaveProperty('status');

    const countriesRes = await app.inject({ method: 'GET', url: '/api/v1/countries?limit=2' });
    expect(countriesRes.statusCode).toBe(200);
    const countries = countriesRes.json();
    expect(typeof countries.total).toBe('number');
    expect(Array.isArray(countries.items)).toBe(true);

    const summaryRes = await app.inject({ method: 'GET', url: '/api/v1/countries/summary?region=East%20Asia' });
    expect(summaryRes.statusCode).toBe(200);
    const summary = summaryRes.json();
    expect(typeof summary.totalCountries).toBe('number');

    const timeseriesRes = await app.inject({ method: 'GET', url: '/api/v1/timeseries?country=US&indicator=GDP&fromYear=2020&toYear=2023' });
    expect(timeseriesRes.statusCode).toBe(200);
    const timeseries = timeseriesRes.json();
    expect(typeof timeseries.total).toBe('number');
    expect(Array.isArray(timeseries.items)).toBe(true);

    const indicatorsRes = await app.inject({ method: 'GET', url: '/api/v1/indicators?country=US' });
    expect(indicatorsRes.statusCode).toBe(200);
    const indicators = indicatorsRes.json();
    expect(Array.isArray(indicators.items)).toBe(true);

    const compareRes = await app.inject({ method: 'GET', url: '/api/v1/compare?indicator=GDP&countries=US,CN,JP' });
    expect(compareRes.statusCode).toBe(200);
    const compare = compareRes.json();
    expect(Array.isArray(compare.items)).toBe(true);

    const metricsRes = await app.inject({ method: 'GET', url: '/api/v1/metrics' });
    expect(metricsRes.statusCode).toBe(200);
    const metrics = metricsRes.json();
    expect(typeof metrics.requestsTotal).toBe('number');
    expect(typeof metrics.errorsTotal).toBe('number');

    const docsRes = await app.inject({ method: 'GET', url: '/api/v1/docs' });
    expect(docsRes.statusCode).toBe(200);
    const docs = docsRes.json();
    expect(Array.isArray(docs.endpoints)).toBe(true);

    const forecastRes = await app.inject({ method: 'GET', url: '/api/v1/forecast?country=US&indicator=GDP&horizon=2' });
    expect([404, 200]).toContain(forecastRes.statusCode);

    await app.close();
  });
});
