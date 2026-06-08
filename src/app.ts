import Fastify from 'fastify';
import cors from '@fastify/cors';
import sensible from '@fastify/sensible';
import healthRoute from './routes/health.js';
import countriesRoute from './routes/countries.js';
import metricsRoute from './routes/metrics.js';
import { observabilityPlugin } from './plugins/observability.js';
import { rateLimitPlugin } from './plugins/rate-limit.js';
import { errorHandlerPlugin } from './plugins/error-handler.js';

export function createApp() {
  const app = Fastify({
    logger: true
  });

  app.register(cors, {
    origin: true
  });

  app.register(sensible);
  app.register(errorHandlerPlugin);
  app.register(rateLimitPlugin);
  app.register(observabilityPlugin);
  app.register(healthRoute, { prefix: '/api/v1' });
  app.register(countriesRoute, { prefix: '/api/v1' });
  app.register(metricsRoute, { prefix: '/api/v1' });

  return app;
}
