import type { FastifyPluginAsync } from 'fastify';

const openapi = {
  openapi: '3.0.3',
  info: {
    title: 'future-OEDC-country-trend backend API',
    version: '0.1.0'
  },
  servers: [{ url: '/' }],
  paths: {
    '/api/v1/health': {
      get: { summary: 'Health check', responses: { '200': { description: 'ok' } } }
    },
    '/api/v1/countries': {
      get: {
        summary: 'List countries',
        parameters: [
          { in: 'query', name: 'search', schema: { type: 'string' } },
          { in: 'query', name: 'region', schema: { type: 'string' } },
          {
            in: 'query',
            name: 'sortBy',
            schema: {
              type: 'string',
              enum: ['population', 'gdpPerCapita', 'lifeExpectancy', 'internetUsers', 'co2PerCapita']
            }
          },
          { in: 'query', name: 'limit', schema: { type: 'integer', minimum: 1 } },
          { in: 'query', name: 'offset', schema: { type: 'integer', minimum: 0 } }
        ],
        responses: { '200': { description: 'Country list' } }
      }
    },
    '/api/v1/countries/summary': {
      get: { summary: 'Countries summary', responses: { '200': { description: 'Summary payload' } } }
    },
    '/api/v1/timeseries': {
      get: {
        summary: 'Timeseries endpoint',
        parameters: [
          { in: 'query', name: 'country', schema: { type: 'string' } },
          { in: 'query', name: 'indicator', schema: { type: 'string' } },
          { in: 'query', name: 'fromYear', schema: { type: 'integer' } },
          { in: 'query', name: 'toYear', schema: { type: 'integer' } }
        ],
        responses: { '200': { description: 'Timeseries payload' }, '400': { description: 'Invalid query' } }
      }
    },
    '/api/v1/indicators': {
      get: {
        summary: 'Indicators by country',
        parameters: [{ in: 'query', name: 'country', schema: { type: 'string' } }],
        responses: { '200': { description: 'Indicators payload' } }
      }
    },
    '/api/v1/compare': {
      get: {
        summary: 'Compare indicator across countries',
        parameters: [
          { in: 'query', name: 'countries', required: true, schema: { type: 'string' } },
          { in: 'query', name: 'indicator', required: true, schema: { type: 'string' } }
        ],
        responses: { '200': { description: 'Compare payload' }, '400': { description: 'Invalid query' } }
      }
    },
    '/api/v1/forecast': {
      get: {
        summary: 'Forecast using linear or CAGR',
        parameters: [
          { in: 'query', name: 'country', required: true, schema: { type: 'string' } },
          { in: 'query', name: 'indicator', required: true, schema: { type: 'string' } },
          { in: 'query', name: 'yearsAhead', schema: { type: 'integer', minimum: 1, maximum: 20 } },
          { in: 'query', name: 'method', schema: { type: 'string', enum: ['linear', 'cagr'] } }
        ],
        responses: {
          '200': { description: 'Forecast payload' },
          '400': { description: 'Invalid query' },
          '404': { description: 'Not found' }
        }
      }
    },
    '/api/v1/metrics': {
      get: { summary: 'Service metrics', responses: { '200': { description: 'Metrics payload' } } }
    },
    '/api/v1/docs': {
      get: { summary: 'Human docs', responses: { '200': { description: 'Docs payload' } } }
    },
    '/api/v1/openapi.json': {
      get: { summary: 'OpenAPI spec', responses: { '200': { description: 'OpenAPI JSON' } } }
    }
  }
} as const;

const openapiRoute: FastifyPluginAsync = async (app) => {
  app.get('/openapi.json', async () => openapi);
};

export default openapiRoute;
