import Fastify from 'fastify';
import cors from '@fastify/cors';
import sensible from '@fastify/sensible';
import healthRoute from './routes/health.js';

export function createApp() {
  const app = Fastify({
    logger: true
  });

  app.register(cors, {
    origin: true
  });

  app.register(sensible);
  app.register(healthRoute, { prefix: '/api/v1' });

  return app;
}
