export interface CountryStat {
  country: string;
  region: string;
  population: number;
  gdpPerCapita: number;
  lifeExpectancy: number;
  internetUsers: number;
  co2PerCapita: number;
}

export type SortField =
  | 'population'
  | 'gdpPerCapita'
  | 'lifeExpectancy'
  | 'internetUsers'
  | 'co2PerCapita';

export interface DashboardState {
  search: string;
  region: string;
  sortBy: SortField;
}

export const DEFAULT_STATE: DashboardState = {
  search: '',
  region: 'all',
  sortBy: 'population'
};

const numericFields: SortField[] = ['population', 'gdpPerCapita', 'lifeExpectancy', 'internetUsers', 'co2PerCapita'];

export function isCountryStat(value: unknown): value is CountryStat {
  if (!value || typeof value !== 'object') return false;

  const candidate = value as Partial<CountryStat>;
  return (
    typeof candidate.country === 'string' &&
    candidate.country.trim().length > 0 &&
    typeof candidate.region === 'string' &&
    candidate.region.trim().length > 0 &&
    numericFields.every((field) => typeof candidate[field] === 'number' && Number.isFinite(candidate[field]))
  );
}

export function getCountries(dataset: unknown): CountryStat[] {
  if (!Array.isArray(dataset)) return [];
  if (dataset.every(isCountryStat)) return dataset as CountryStat[];
  return dataset.filter(isCountryStat);
}

export function average(items: CountryStat[], key: SortField): number {
  if (!items.length) return 0;
  return items.reduce((sum, item) => sum + item[key], 0) / items.length;
}

export function filterAndSortCountries(items: CountryStat[], state: DashboardState): CountryStat[] {
  const search = state.search.trim().toLowerCase();

  return [...items]
    .filter((item) => state.region === 'all' || item.region === state.region)
    .filter((item) => !search || item.country.toLowerCase().includes(search))
    .sort((a, b) => b[state.sortBy] - a[state.sortBy] || a.country.localeCompare(b.country));
}
