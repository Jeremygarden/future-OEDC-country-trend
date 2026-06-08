export type AppHttpErrorShape = Error & {
  statusCode: number;
  code: string;
  details?: unknown;
};

export function appHttpError(
  statusCode: number,
  code: string,
  message: string,
  details?: unknown
): AppHttpErrorShape {
  const error = new Error(message) as AppHttpErrorShape;
  error.statusCode = statusCode;
  error.code = code;
  error.details = details;
  return error;
}
