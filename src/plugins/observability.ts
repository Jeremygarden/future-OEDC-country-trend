import type { FastifyPluginAsync } from 'fastify';
import fp from 'fastify-plugin';

declare module 'fastify' {
  interface FastifyInstance {
    metrics: {
      requestsTotal: number;
      errorsTotal: number;
      uptimeSeconds: () => number;
    };
  }
}

const observabilityPluginRaw: FastifyPluginAsync = async (app) => {
  const startedAt = Date.now();

  app.decorate('metrics', {
    requestsTotal: 0,
    errorsTotal: 0,
    uptimeSeconds: () => Math.floor((Date.now() - startedAt) / 1000)
  });

  app.addHook('onResponse', async (_request, reply) => {
    app.metrics.requestsTotal += 1;

    if (reply.statusCode >= 500) {
      app.metrics.errorsTotal += 1;
    }
  });
};

export const observabilityPlugin = fp(observabilityPluginRaw, {
  name: 'observability-plugin'
});
