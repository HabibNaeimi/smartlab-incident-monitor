import pytest

from common.config.env import (
    get_required_str, get_optional_str, ConfigurationError,
    get_int, get_float, get_bool,
    get_secret, get_url,
)


REQUIRED_NAME = "TEST_REQUIRED_SETTING"
OPTIONAL_NAME = "TEST_OPTIONAL_SETTING"


def test_get_required_str_returns_stripped_value():
    source = {
        REQUIRED_NAME: "  required-value-for-test-only \t",
    }

    result = get_required_str(source, REQUIRED_NAME)

    assert result == "required-value-for-test-only"


@pytest.mark.parametrize(
    "source",
    [
        {},
        {REQUIRED_NAME: ""},
        {REQUIRED_NAME: " \t\n "},
    ],
    ids=["missing", "empty", "whitespace-only"],
)
def test_get_required_str_rejects_missing_or_blank_value(source):
    with pytest.raises(ConfigurationError) as exc_info:
        get_required_str(source, REQUIRED_NAME)

    message = str(exc_info.value)

    assert REQUIRED_NAME in message
    assert "str" in message.lower()
    assert "\t" not in message
    assert "\n" not in message


@pytest.mark.parametrize(
    ("source", "default", "expected"),
    [
        ({}, None, None),
        ({}, "default-for-test-only", "default-for-test-only"),
        (
            {OPTIONAL_NAME: ""},
            "default-for-test-only",
            "default-for-test-only",
        ),
        (
            {OPTIONAL_NAME: " \t\n "},
            "default-for-test-only",
            "default-for-test-only",
        ),
    ],
    ids=[
        "missing-with-none-default",
        "missing-with-string-default",
        "empty",
        "whitespace-only",
    ],
)
def test_get_optional_str_returns_default_for_missing_or_blank_value(
    source,
    default,
    expected,
):
    result = get_optional_str(source, OPTIONAL_NAME, default)

    assert result == expected


def test_get_optional_str_returns_stripped_value():
    source = {
        OPTIONAL_NAME: "  optional-value-for-test-only \t",
    }

    result = get_optional_str(
        source,
        OPTIONAL_NAME,
        default="unused-default-for-test-only",
    )

    assert result == "optional-value-for-test-only"


def test_string_readers_do_not_mutate_source():
    source = {
        REQUIRED_NAME: "  required-value-for-test-only  ",
        OPTIONAL_NAME: "  optional-value-for-test-only  ",
    }
    original_source = source.copy()

    get_required_str(source, REQUIRED_NAME)
    get_optional_str(source, OPTIONAL_NAME)

    assert source == original_source


INT_NAME = "TEST_INT_SETTING"
FLOAT_NAME = "TEST_FLOAT_SETTING"
BOOL_NAME = "TEST_BOOL_SETTING"


@pytest.mark.parametrize(
    ("reader", "name", "expected_type"),
    [
        (get_int, INT_NAME, "int"),
        (get_float, FLOAT_NAME, "float"),
        (get_bool, BOOL_NAME, "bool"),
    ],
    ids=["int", "float", "bool"],
)
@pytest.mark.parametrize(
    "raw_value",
    [None, "", " \t\n "],
    ids=["missing", "empty", "whitespace-only"],
)
def test_typed_reader_rejects_missing_or_blank_without_default(
    reader,
    name,
    expected_type,
    raw_value,
):
    source = {} if raw_value is None else {name: raw_value}

    with pytest.raises(ConfigurationError) as exc_info:
        reader(source, name)

    message = str(exc_info.value)

    assert name in message
    assert expected_type in message.lower()


@pytest.mark.parametrize(
    ("reader", "name", "default"),
    [
        (get_int, INT_NAME, 17),
        (get_float, FLOAT_NAME, 2.5),
        (get_bool, BOOL_NAME, False),
    ],
    ids=["int", "float", "bool"],
)
@pytest.mark.parametrize(
    "raw_value",
    [None, "", " \t\n "],
    ids=["missing", "empty", "whitespace-only"],
)
def test_typed_reader_returns_supplied_default_for_missing_or_blank(
    reader,
    name,
    default,
    raw_value,
):
    source = {} if raw_value is None else {name: raw_value}

    result = reader(source, name, default=default)

    assert result == default
    assert type(result) is type(default)


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("42", 42),
        ("  -7  ", -7),
        ("+15", 15),
    ],
)
def test_get_int_accepts_valid_values(raw_value, expected):
    result = get_int({INT_NAME: raw_value}, INT_NAME)

    assert result == expected
    assert type(result) is int


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("3.25", 3.25),
        ("  -2.5  ", -2.5),
        ("1e2", 100.0),
    ],
)
def test_get_float_accepts_valid_values(raw_value, expected):
    result = get_float({FLOAT_NAME: raw_value}, FLOAT_NAME)

    assert result == expected
    assert type(result) is float


@pytest.mark.parametrize(
    ("reader", "name", "raw_value", "minimum", "maximum", "expected"),
    [
        (get_int, INT_NAME, "10", 10, 20, 10),
        (get_int, INT_NAME, "20", 10, 20, 20),
        (get_float, FLOAT_NAME, "1.5", 1.5, 2.5, 1.5),
        (get_float, FLOAT_NAME, "2.5", 1.5, 2.5, 2.5),
    ],
    ids=[
        "int-minimum",
        "int-maximum",
        "float-minimum",
        "float-maximum",
    ],
)
def test_numeric_bounds_are_inclusive(
    reader,
    name,
    raw_value,
    minimum,
    maximum,
    expected,
):
    result = reader(
        {name: raw_value},
        name,
        minimum=minimum,
        maximum=maximum,
    )

    assert result == expected


@pytest.mark.parametrize(
    (
        "reader",
        "name",
        "rejected_value",
        "minimum",
        "maximum",
        "expected_type",
        "expected_bound",
    ),
    [
        (
            get_int,
            INT_NAME,
            "-999999",
            0,
            10,
            "int",
            "0",
        ),
        (
            get_int,
            INT_NAME,
            "999999",
            0,
            10,
            "int",
            "10",
        ),
        (
            get_float,
            FLOAT_NAME,
            "-999999.25",
            0.0,
            10.0,
            "float",
            "0.0",
        ),
        (
            get_float,
            FLOAT_NAME,
            "999999.25",
            0.0,
            10.0,
            "float",
            "10.0",
        ),
    ],
    ids=[
        "int-below-minimum",
        "int-above-maximum",
        "float-below-minimum",
        "float-above-maximum",
    ],
)
def test_numeric_reader_rejects_out_of_range_values(
    reader,
    name,
    rejected_value,
    minimum,
    maximum,
    expected_type,
    expected_bound,
):
    with pytest.raises(ConfigurationError) as exc_info:
        reader(
            {name: rejected_value},
            name,
            minimum=minimum,
            maximum=maximum,
        )

    message = str(exc_info.value)

    assert name in message
    assert expected_type in message.lower()
    assert expected_bound in message
    assert rejected_value not in message


@pytest.mark.parametrize(
    ("reader", "name", "rejected_value", "expected_type"),
    [
        (
            get_int,
            INT_NAME,
            "malformed-int-for-test-only",
            "int",
        ),
        (
            get_float,
            FLOAT_NAME,
            "malformed-float-for-test-only",
            "float",
        ),
    ],
    ids=["int", "float"],
)
def test_numeric_reader_rejects_malformed_values_without_leaking_them(
    reader,
    name,
    rejected_value,
    expected_type,
):
    with pytest.raises(ConfigurationError) as exc_info:
        reader({name: rejected_value}, name)

    error = exc_info.value
    message = str(error)

    assert name in message
    assert expected_type in message.lower()
    assert rejected_value not in message
    assert error.__suppress_context__ is True


@pytest.mark.parametrize(
    "rejected_value",
    ["nan", "inf", "-inf"],
)
def test_get_float_rejects_non_finite_values(rejected_value):
    with pytest.raises(ConfigurationError) as exc_info:
        get_float({FLOAT_NAME: rejected_value}, FLOAT_NAME)

    message = str(exc_info.value)

    assert FLOAT_NAME in message
    assert "float" in message.lower()


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("1", True),
        ("true", True),
        ("yes", True),
        ("on", True),
        ("0", False),
        ("false", False),
        ("no", False),
        ("off", False),
    ],
)
def test_get_bool_accepts_all_supported_tokens_case_insensitively(
    token,
    expected,
):
    variants = (
        token,
        token.upper(),
        f" \t{token.swapcase()}\n",
    )

    for variant in variants:
        result = get_bool({BOOL_NAME: variant}, BOOL_NAME)

        assert result is expected


@pytest.mark.parametrize(
    "rejected_value",
    [
        "2",
        "truthy",
        "enabled",
        "perhaps-for-test-only",
    ],
)
def test_get_bool_rejects_invalid_text_without_leaking_it(
    rejected_value,
):
    with pytest.raises(ConfigurationError) as exc_info:
        get_bool({BOOL_NAME: rejected_value}, BOOL_NAME)

    message = str(exc_info.value)

    assert BOOL_NAME in message
    assert "bool" in message.lower()
    assert rejected_value not in message


# URL TESTS
    
URL_NAME = "TEST_URL_SETTING"
SECRET_NAME = "TEST_SECRET_SETTING"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        (
            "http://service-catalog:8080",
            "http://service-catalog:8080",
        ),
        (
            "https://example.test",
            "https://example.test",
        ),
        (
            "  http://localhost:8080/api/v1  ",
            "http://localhost:8080/api/v1",
        ),
    ],
)
def test_get_url_accepts_valid_http_urls(raw_value, expected):
    result = get_url({URL_NAME: raw_value}, URL_NAME)

    assert result == expected


@pytest.mark.parametrize(
    "raw_value",
    [None, "", " \t\n "],
    ids=["missing", "empty", "whitespace-only"],
)
def test_get_url_rejects_missing_or_blank_values(raw_value):
    source = {} if raw_value is None else {URL_NAME: raw_value}

    with pytest.raises(ConfigurationError) as exc_info:
        get_url(source, URL_NAME)

    assert URL_NAME in str(exc_info.value)


@pytest.mark.parametrize(
    "rejected_url",
    [
        "catalog:8080",
        "ftp://catalog:8080",
        "http:///missing-host",
        "http://user:password@catalog:8080",
        "http://catalog:invalid",
        "http://catalog:65536",
        "http://catalog:8080/",
        "http://catalog:8080/path?limit=10",
        "http://catalog:8080/path#section",
        "http://bad host:8080",
    ],
    ids=[
        "missing-http-scheme",
        "unsupported-scheme",
        "missing-host",
        "embedded-credentials",
        "malformed-port",
        "out-of-range-port",
        "trailing-slash",
        "query-string",
        "fragment",
        "internal-whitespace",
    ],
)
def test_get_url_rejects_invalid_urls(rejected_url):
    with pytest.raises(ConfigurationError) as exc_info:
        get_url({URL_NAME: rejected_url}, URL_NAME)

    message = str(exc_info.value)

    assert URL_NAME in message
    assert rejected_url not in message


def test_get_url_does_not_leak_rejected_value():
    rejected_url = (
        "http://sensitive-host-for-test:"
        "invalid-port-for-test"
    )

    with pytest.raises(ConfigurationError) as exc_info:
        get_url({URL_NAME: rejected_url}, URL_NAME)

    error = exc_info.value
    message = str(error)

    assert URL_NAME in message
    assert rejected_url not in message
    assert "sensitive-host-for-test" not in message
    assert "invalid-port-for-test" not in message
    assert error.__suppress_context__ is True


@pytest.mark.parametrize(
    "raw_value",
    [None, "", " \t\n "],
    ids=["missing", "empty", "whitespace-only"],
)
def test_get_secret_returns_none_when_optional_and_absent(raw_value):
    source = {} if raw_value is None else {SECRET_NAME: raw_value}

    result = get_secret(source, SECRET_NAME)

    assert result is None


@pytest.mark.parametrize(
    "raw_value",
    [None, "", " \t\n "],
    ids=["missing", "empty", "whitespace-only"],
)
def test_get_secret_rejects_absent_required_secret(raw_value):
    source = {} if raw_value is None else {SECRET_NAME: raw_value}

    with pytest.raises(ConfigurationError) as exc_info:
        get_secret(source, SECRET_NAME, required=True)

    assert SECRET_NAME in str(exc_info.value)


@pytest.mark.parametrize(
    "secret_value",
    [
        "secret-for-test-only",
        "secret-with-symbols-for-test-only!@#$%",
        "secret with internal spaces for test only",
    ],
)
def test_get_secret_returns_valid_secret_unchanged(secret_value):
    result = get_secret(
        {SECRET_NAME: secret_value},
        SECRET_NAME,
    )

    assert result == secret_value


@pytest.mark.parametrize(
    "secret_value",
    [
        " secret-for-test-only",
        "secret-for-test-only ",
        "\tsecret-for-test-only",
        "secret-for-test-only\n",
    ],
    ids=[
        "leading-space",
        "trailing-space",
        "leading-tab",
        "trailing-newline",
    ],
)
@pytest.mark.parametrize(
    "required",
    [False, True],
    ids=["optional", "required"],
)
def test_get_secret_rejects_surrounding_whitespace(
    secret_value,
    required,
):
    with pytest.raises(ConfigurationError) as exc_info:
        get_secret(
            {SECRET_NAME: secret_value},
            SECRET_NAME,
            required=required,
        )

    assert SECRET_NAME in str(exc_info.value)


def test_get_secret_errors_do_not_expose_secret_value():
    rejected_secret = " sensitive-secret-for-test-only "

    with pytest.raises(ConfigurationError) as exc_info:
        get_secret(
            {SECRET_NAME: rejected_secret},
            SECRET_NAME,
        )

    message = str(exc_info.value)

    assert SECRET_NAME in message
    assert rejected_secret not in message
    assert rejected_secret.strip() not in message