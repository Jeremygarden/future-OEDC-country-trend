-- SQL Views for country stats dashboard
-- Created by iteration 5

-- v_latest_stats: Most recent value per country per indicator
DROP VIEW IF EXISTS v_latest_stats;
CREATE VIEW v_latest_stats AS
SELECT
    c.iso3,
    c.name AS country_name,
    i.code AS indicator_code,
    i.name AS indicator_name,
    i.unit,
    i.category,
    dp.year,
    dp.value,
    ds.name AS source_name
FROM data_points dp
JOIN countries c ON c.id = dp.country_id
JOIN indicators i ON i.id = dp.indicator_id
LEFT JOIN data_sources ds ON ds.id = dp.source_id
WHERE dp.year = (
    SELECT MAX(dp2.year)
    FROM data_points dp2
    WHERE dp2.country_id = dp.country_id
      AND dp2.indicator_id = dp.indicator_id
);

-- v_gdp_trend: GDP values 2015-2024 per country
DROP VIEW IF EXISTS v_gdp_trend;
CREATE VIEW v_gdp_trend AS
SELECT
    c.iso3,
    c.name AS country_name,
    dp.year,
    dp.value AS gdp_usd,
    ROUND(dp.value / 1e12, 2) AS gdp_trillion_usd
FROM data_points dp
JOIN countries c ON c.id = dp.country_id
JOIN indicators i ON i.id = dp.indicator_id
WHERE i.code = 'NY.GDP.MKTP.CD'
  AND dp.year BETWEEN 2015 AND 2024
ORDER BY dp.year, c.iso3;

-- v_country_comparison: Latest values for all indicators across 5 countries
DROP VIEW IF EXISTS v_country_comparison;
CREATE VIEW v_country_comparison AS
SELECT
    c.iso3,
    c.name AS country_name,
    c.region,
    MAX(CASE WHEN i.code = 'NY.GDP.MKTP.CD' THEN dp.value END) AS gdp_usd,
    MAX(CASE WHEN i.code = 'NY.GDP.PCAP.CD' THEN dp.value END) AS gdp_per_capita_usd,
    MAX(CASE WHEN i.code = 'NY.GDP.MKTP.KD.ZG' THEN dp.value END) AS gdp_growth_pct,
    MAX(CASE WHEN i.code = 'SP.POP.TOTL' THEN dp.value END) AS population,
    MAX(CASE WHEN i.code = 'FP.CPI.TOTL.ZG' THEN dp.value END) AS inflation_pct,
    MAX(CASE WHEN i.code = 'SL.UEM.TOTL.ZS' OR i.code = 'LRHUTTTT' THEN dp.value END) AS unemployment_pct,
    MAX(CASE WHEN i.code = 'NE.TRD.GNFS.ZS' THEN dp.value END) AS trade_pct_gdp,
    MAX(CASE WHEN i.code = 'GC.DOD.TOTL.GD.ZS' OR i.code = 'GGXWDG_NGDP' THEN dp.value END) AS govt_debt_pct_gdp,
    MAX(dp.year) AS data_year
FROM data_points dp
JOIN countries c ON c.id = dp.country_id
JOIN indicators i ON i.id = dp.indicator_id
WHERE dp.year = (
    SELECT MAX(dp2.year) FROM data_points dp2 
    WHERE dp2.country_id = dp.country_id AND dp2.indicator_id = dp.indicator_id
)
GROUP BY c.iso3, c.name, c.region
ORDER BY gdp_usd DESC;
