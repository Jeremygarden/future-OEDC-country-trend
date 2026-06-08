export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    statusCode: number;
    details?: unknown;
  };
}

export interface PythonApiErrorPayload {
  error: {
    code: string;
    message: string;
    status_code: number;
    details?: unknown;
  };
}

export function buildApiErrorPayload(
  statusCode: number,
  code: string,
  message: string,
  details?: unknown
): ApiErrorPayload {
  return {
    error: {
      code,
      message,
      statusCode,
      ...(details === undefined ? {} : { details })
    }
  };
}
