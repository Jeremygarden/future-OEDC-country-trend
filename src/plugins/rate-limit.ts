import fp from 'fastify-plugin';
import rateLimit from '@fastify/rate-limit';
import type { FastifyPluginAsync } from 'fastify';

const rateLimitPluginRaw: FastifyPluginAsync = async (app) => {
  await app.register(rateLimit, {
    max: 120,
    timeWindow: '1 minute',
    keyGenerator: (request) => request.ip,
    errorResponseBuilder: (_request, context) => ({
      statusCode: 429,
      error: 'Too Many Requests',
      message: `Rate limit exceeded, retry in ${context.after}`
    })
  });
};

export const rateLimitPlugin = fp(rateLimitPluginRaw, {
  name: 'rate-limit-plugin'
});
