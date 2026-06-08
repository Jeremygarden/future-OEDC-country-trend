import type { FastifyPluginAsync } from 'fastify';

const docsRoute: FastifyPluginAsync = async (app) => {
  app.get('/docs', async () => {
    return {
      name: 'future-OEDC-country-trend backend',
      version: '0.1.0',
      endpoints: [
        {
          method: 'GET',
          path: '/api/v1/health',
          description: 'Service health check'
        },
        {
          method: 'GET',
          path: '/api/v1/countries',
          description: 'List countries with optional filtering/sorting/pagination',
          query: {
            search: 'string',
            region: 'string',
            sortBy: 'population|gdpPerCapita|lifeExpectancy|internetUsers|co2PerCapita',
            limit: 'number>0',
            offset: 'number>=0'
          }
        },
        {
          method: 'GET',
          path: '/api/v1/countries/summary',
          description: 'Aggregate summary values for selected countries',
          query: {
            search: 'string',
            region: 'string',
            sortBy: 'population|gdpPerCapita|lifeExpectancy|internetUsers|co2PerCapita'
          }
        },
        {
          method: 'GET',
          path: '/api/v1/metrics',
          description: 'In-process request/uptime counters'
        },
        {
          method: 'GET',
          path: '/api/v1/docs',
          description: 'Lightweight API documentation payload'
        }
      ]
    };
  });
};

export default docsRoute;
