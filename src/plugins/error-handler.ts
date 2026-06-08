import fp from 'fastify-plugin';
import type { FastifyPluginAsync } from 'fastify';
import { buildApiErrorPayload } from '../core/api-error.js';

const errorHandlerPluginRaw: FastifyPluginAsync = async (app) => {
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
