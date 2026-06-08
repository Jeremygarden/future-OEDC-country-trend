"""Tests for data transformation and derived metrics."""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl.transform import (
    normalize_value, compute_yoy_change, compute_cagr,
    compute_country_rank, flag_outliers
)


def test_normalize_gdp():
    """Test GDP normalization to trillions."""
    # GDP values in USD
    result = normalize_value(27360000000000.0, "NY.GDP.MKTP.CD")
    assert result == pytest.approx(27.36, rel=0.01)
    
    # Small values shouldn't be divided
    result = normalize_value(100.0, "NY.GDP.MKTP.CD")
    assert result == 100.0


def test_normalize_percentage():
    """Test percentage values are rounded correctly."""
    result = normalize_value(3.14159, "SL.UEM.TOTL.ZS")
    assert result == 3.14
    
    result = normalize_value(2.7, "FP.CPI.TOTL.ZG")
    assert result == 2.7


def test_normalize_population():
    """Test population normalization to billions."""
    result = normalize_value(334914895.0, "SP.POP.TOTL")
    assert result == pytest.approx(0.3349, rel=0.01)


def test_normalize_none():
    """Test that None values pass through."""
    result = normalize_value(None, "NY.GDP.MKTP.CD")
    assert result is None


def test_compute_yoy_change():
    """Test year-over-year change computation."""
    values = [
        {"year": 2020, "value": 100.0},
        {"year": 2021, "value": 110.0},
        {"year": 2022, "value": 105.0},
        {"year": 2023, "value": 115.5},
    ]
    
    result = compute_yoy_change(values)
    
    assert result[0]["yoy_change"] is None  # First year has no previous
    assert result[1]["yoy_change"] == pytest.approx(10.0, rel=0.01)  # 10% growth
    assert result[2]["yoy_change"] == pytest.approx(-4.545, rel=0.01)  # ~-4.5% decline
    assert result[3]["yoy_change"] == pytest.approx(10.0, rel=0.01)  # (115.5-105)/105*100 = 10.0


def test_compute_yoy_change_empty():
    """Test YoY with empty input."""
    assert compute_yoy_change([]) == []


def test_compute_cagr():
    """Test 5-year CAGR computation."""
    values = [
        {"year": 2015, "value": 100.0},
        {"year": 2016, "value": 105.0},
        {"year": 2017, "value": 110.0},
        {"year": 2018, "value": 115.0},
        {"year": 2019, "value": 120.0},
        {"year": 2020, "value": 125.0},  # 5 years later
    ]
    
    result = compute_cagr(values, n_years=5)
    # CAGR = (125/100)^(1/5) - 1 ≈ 4.56%
    assert result == pytest.approx(4.56, abs=0.1)


def test_compute_cagr_insufficient_data():
    """Test CAGR with insufficient data."""
    values = [{"year": 2023, "value": 100.0}]
    assert compute_cagr(values) is None
    assert compute_cagr([]) is None


def test_compute_country_rank_descending():
    """Test country ranking (higher = rank 1 for GDP)."""
    values = {"USA": 27.0, "CHN": 17.0, "JPN": 4.2, "AUS": 1.7, "CAN": 2.1}
    ranks = compute_country_rank(values, ascending=False)
    
    assert ranks["USA"] == 1
    assert ranks["CHN"] == 2
    assert ranks["JPN"] == 3
    assert ranks["CAN"] == 4
    assert ranks["AUS"] == 5


def test_compute_country_rank_ascending():
    """Test country ranking (lower = rank 1 for unemployment)."""
    values = {"USA": 3.5, "CHN": 5.2, "JPN": 2.8, "AUS": 4.1, "CAN": 5.7}
    ranks = compute_country_rank(values, ascending=True)
    
    assert ranks["JPN"] == 1   # Lowest unemployment
    assert ranks["USA"] == 2
    assert ranks["AUS"] == 3
    assert ranks["CHN"] == 4
    assert ranks["CAN"] == 5   # Highest unemployment


def test_flag_outliers():
    """Test outlier detection with clearly separated values."""
    # Use values where the outlier is clearly beyond 3 std
    # Mean of normals ≈ 10.0, std ≈ 0.5, outlier 1000 is way beyond 3 std
    values = [10.0, 11.0, 9.5, 10.5, 10.2, 1000.0, 10.1]  # 1000.0 is outlier
    flags = flag_outliers(values, threshold_std=3.0)
    
    assert flags[5] == True   # 1000.0 is clear outlier
    normal_flags = [f for i, f in enumerate(flags) if i != 5]
    assert all(f == False for f in normal_flags)


def test_flag_outliers_small_dataset():
    """Test outlier detection with insufficient data."""
    values = [1.0, 2.0]
    flags = flag_outliers(values)
    assert all(f == False for f in flags)
