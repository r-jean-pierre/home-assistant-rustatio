# Contributing

Contributions are welcome when they keep the integration focused and small.

## Development principles

- Prefer structured Rustatio API data over log parsing.
- Prefer aggregate Home Assistant entities over per-torrent entities.
- Avoid adding external runtime Python dependencies unless there is a clear
  benefit.
- Keep one shared coordinator refresh for all entities.
- Preserve clear user-facing torrent terminology even when Rustatio internally
  uses the word `instance`.
- Add or update tests when behavior changes.

## Test environment

The reproducible test environment is defined in:

```text
requirements_test.txt
```

The pinned `pytest-homeassistant-custom-component` release corresponds to the
minimum supported Home Assistant 2026.9 series used by this repository.

Install the test dependencies:

```bash
python -m pip install -r requirements_test.txt
```

Run the complete suite:

```bash
pytest -vv
```

Run with coverage:

```bash
pytest   --cov=custom_components.rustatio   --cov-report=term-missing   --cov-fail-under=90   -vv
```

## What the tests cover

The suite verifies:

- the Rustatio HTTP response envelope and endpoint data shapes;
- bearer-token handling;
- connection, HTTP and authentication failures;
- initial config flow;
- config-flow recovery after errors;
- duplicate-server detection;
- reconfiguration;
- reauthentication;
- aggregate sensor values and attributes;
- Home Assistant unit conversion;
- entity availability when Rustatio goes offline;
- recovery when Rustatio comes back;
- clean config-entry unloading.

Tests should exercise Home Assistant through config entries and entity states
where practical. Small isolated HTTP-client behaviors may be tested directly.

## Continuous integration

GitHub Actions run on pushes and pull requests:

- pytest against Home Assistant 2026.9.4;
- at least 90% integration-code coverage;
- Hassfest;
- HACS validation.

A weekly scheduled job also runs the same tests against the newest available
`pytest-homeassistant-custom-component` package. That package tracks current
Home Assistant releases, including betas.

The scheduled future-compatibility job is intentionally non-blocking. A failure
is an early warning that an upcoming Home Assistant release may require a code
change; it does not make a stable release fail retroactively.

## Versioning

The integration uses Semantic Versioning.

The version is stored in:

```text
custom_components/rustatio/manifest.json
```

A GitHub release should use a matching tag such as:

```text
v1.0.0
```
