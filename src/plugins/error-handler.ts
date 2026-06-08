import fp from 'fastify-plugin';
import type { FastifyPluginAsync } from 'fastify';

const errorHandlerPluginRaw: FastifyPluginAsync = async (app) => {
  app.setErrorHandler((error, request, reply) => {
    const statusCode = (error as { statusCode?: number }).statusCode ?? 500;
    const namedError = error instanceof Error ? error : new Error('Unknown error');

    request.log.error({ err: error, statusCode }, 'request failed');

    reply.status(statusCode).send({
      error: statusCode >= 500 ? 'Internal Server Error' : namedError.name,
      message: statusCode >= 500 ? 'Unexpected server error' : namedError.message,
      statusCode
    });
  });
};

export const errorHandlerPlugin = fp(errorHandlerPluginRaw, {
  name: 'error-handler-plugin'
});
