export interface CountryMetricPoint {
  year: number;
  value: number;
}

export interface CountryMetricRecord {
  countryCode: string;
  countryName: string;
  metric: string;
  points: CountryMetricPoint[];
}
