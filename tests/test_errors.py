from etl.errors import EtlError, etl_error_payload


def test_etl_error_payload_shape():
    payload = etl_error_payload(
        "UPSTREAM_TIMEOUT",
        "World Bank request timed out",
        status_code=504,
        details={"source": "worldbank"},
    )

    assert payload == {
        "error": {
            "code": "UPSTREAM_TIMEOUT",
            "message": "World Bank request timed out",
            "status_code": 504,
            "details": {"source": "worldbank"},
        }
    }


def test_etl_error_str_and_payload_without_details():
    error = EtlError("BAD_RECORD", "Malformed ETL record", 400)

    assert str(error) == "Malformed ETL record"
    assert error.to_payload() == {
        "error": {
            "code": "BAD_RECORD",
            "message": "Malformed ETL record",
            "status_code": 400,
        }
    }
