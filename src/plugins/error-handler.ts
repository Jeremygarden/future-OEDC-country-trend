import fp from 'fastify-plugin';
import type { FastifyPluginAsync } from 'fastify';
import { buildApiErrorPayload } from '../core/api-error.js';

const errorHandlerPluginRaw: FastifyPluginAsync = async (app) => {

  app.setNotFoundHandler((request, reply) => {
    const message = `Route ${request.method}:${request.url} not found`;
    request.log.info('route not found');
    reply.status(404).send(buildApiErrorPayload(404, 'ROUTE_NOT_FOUND', message));
  });

  app.setErrorHandler((error, request, reply) => {
    const statusCode = (error as { statusCode?: number }).statusCode ?? 500;
    const namedError = error instanceof Error ? error : new Error('Unknown error');
    const code = (error as { code?: string }).code ?? (statusCode >= 500 ? 'INTERNAL_ERROR' : 'REQUEST_ERROR');
    const details = (error as { details?: unknown }).details;

    request.log.error({ err: error, statusCode, code }, 'request failed');

    reply.status(statusCode).send(
      buildApiErrorPayload(
        statusCode,
        code,
        statusCode >= 500 ? 'Unexpected server error' : namedError.message,
        statusCode >= 500 ? undefined : details
      )
    );
  });
};

export const errorHandlerPlugin = fp(errorHandlerPluginRaw, {
  name: 'error-handler-plugin'
});
