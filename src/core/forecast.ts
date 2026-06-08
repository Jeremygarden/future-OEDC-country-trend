import { appHttpError } from './http-error.js';
import type { TimeSeriesPoint } from './timeseries.js';

export type ForecastMethod = 'linear' | 'cagr';

export type ForecastPoint = {
  year: number;
  value: number;
  method: ForecastMethod;
};

export function computeLinearForecast(points: TimeSeriesPoint[], yearsAhead: number): ForecastPoint[] {
  const sorted = [...points].sort((a, b) => a.year - b.year);

  if (sorted.length < 2) {
    throw appHttpError(400, 'INSUFFICIENT_DATA', 'At least 2 data points are required for linear forecast');
  }

  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const years = last.year - first.year;

  if (years <= 0) {
    throw appHttpError(400, 'INVALID_YEAR_SERIES', 'Time series years must span at least 1 year');
  }

  const slope = (last.value - first.value) / years;

  return Array.from({ length: yearsAhead }, (_, index) => {
    const futureYear = last.year + index + 1;
    return {
      year: futureYear,
      value: Number((last.value + slope * (index + 1)).toFixed(4)),
      method: 'linear' as const
    };
  });
}

export function computeCagrForecast(points: TimeSeriesPoint[], yearsAhead: number): ForecastPoint[] {
  const sorted = [...points].sort((a, b) => a.year - b.year);

  if (sorted.length < 2) {
    throw appHttpError(400, 'INSUFFICIENT_DATA', 'At least 2 data points are required for CAGR forecast');
  }

  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const years = last.year - first.year;

  if (years <= 0 || first.value <= 0 || last.value <= 0) {
    throw appHttpError(400, 'INVALID_CAGR_INPUT', 'CAGR requires positive values and multi-year history');
  }

  const growthRate = (last.value / first.value) ** (1 / years) - 1;

  return Array.from({ length: yearsAhead }, (_, index) => {
    const step = index + 1;
    const futureYear = last.year + step;
    return {
      year: futureYear,
      value: Number((last.value * (1 + growthRate) ** step).toFixed(4)),
      method: 'cagr' as const
    };
  });
}
