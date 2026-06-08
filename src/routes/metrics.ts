import type { FastifyPluginAsync } from 'fastify';

const metricsRoute: FastifyPluginAsync = async (app) => {
  app.get('/metrics', async () => {
    return {
      requestsTotal: app.metrics.requestsTotal,
      errorsTotal: app.metrics.errorsTotal,
      uptimeSeconds: app.metrics.uptimeSeconds()
    };
  });
};

export default metricsRoute;
