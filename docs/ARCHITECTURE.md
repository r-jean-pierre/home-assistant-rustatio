# Architecture

## Scope

This integration exposes a deliberately small set of aggregate Rustatio
statistics to Home Assistant.

It is not intended to reproduce the Rustatio UI or create one Home Assistant
entity per torrent.

## Runtime layout

```text
Home Assistant Core
        |
        | HTTP every 30 s
        v
Rustatio server
        |
        +-- GET /api/instances/summary
        |
        +-- GET /api/watch/status
```

All entities consume the same `RustatioCoordinator` data snapshot.

## Source files

```text
custom_components/rustatio/
├── __init__.py          Config entry setup/unload
├── api.py               Minimal asynchronous Rustatio HTTP client
├── binary_sensor.py     Connectivity diagnostic
├── config_flow.py       Setup, reconfigure and reauthentication
├── const.py             Domain and defaults
├── coordinator.py       Polling and aggregation
├── entity.py            Shared device metadata
├── sensor.py            Aggregate sensors
├── icons.json           Home Assistant entity icons
├── manifest.json        Integration metadata
├── brand/
│   └── icon.png
└── translations/
    ├── en.json
    └── fr.json
```

## Rustatio terminology

Rustatio calls a managed torrent an `instance`.

The low-level API client keeps the upstream endpoint naming
(`/api/instances/summary`) because it mirrors Rustatio.

The coordinator translates the concept into Home Assistant-facing terminology:

```text
Rustatio instance        -> managed torrent
running instance         -> running torrent
watch file               -> torrent file in watch folder
tracker error instance   -> torrent with tracker error
```

This translation is kept at the coordinator/entity layer so the API code stays
easy to compare with the upstream API.

## Polling

`DataUpdateCoordinator` performs one coordinated refresh every 30 seconds.

Each refresh makes two requests concurrently:

```text
GET /api/instances/summary
GET /api/watch/status
```

Adding Home Assistant entities does not add additional HTTP requests.

## Aggregation

`/api/instances/summary` provides one compact record per managed Rustatio
torrent. The integration computes only straightforward global aggregations:

- number of records;
- number whose state is `running`;
- state/source counters;
- sum of torrent sizes;
- sum of cumulative uploaded/downloaded counters;
- sum of current upload/download rates;
- number currently reporting a tracker error.

No ratio averages or other synthetic metrics are created.

`/api/watch/status` directly supplies:

- watch service enabled state;
- watch directory;
- auto-start state;
- file count;
- loaded file count.

## Availability

Normal sensors inherit coordinator availability: if the API refresh fails,
Home Assistant marks them unavailable.

The `Connected` diagnostic binary sensor deliberately remains available so it
can represent the coordinator's last-update status as connected/disconnected.

## Authentication

The API client sends:

```text
Authorization: Bearer <token>
```

only when a token is configured.

HTTP 401 and 403 responses are treated as authentication failures and trigger
Home Assistant's config-entry reauthentication mechanism.

## Units

Cumulative sizes are retained in bytes as native Home Assistant values.

Home Assistant receives only display suggestions (TB/GB) and is responsible for
the conversion.

Rustatio rates are expressed in KB/s by the upstream API/configuration model and
are represented as Home Assistant `kB/s` data-rate sensors.

## Entity model

The integration creates a single `DeviceEntryType.SERVICE` device because
Rustatio is a software service rather than physical hardware.

All entities use:

- stable config-entry-based unique IDs;
- translated entity names;
- entity icons from `icons.json`;
- one common service device.

## Deliberate exclusions

The component does not expose:

- individual torrent entities;
- individual tracker names/errors as entities;
- seeder/leecher totals;
- ETA;
- stop-condition progress;
- seed-time progress;
- parsed log information;
- control buttons/services.

These exclusions keep the code small and avoid making Home Assistant depend on
less stable or highly granular Rustatio behavior.


## Automated test strategy

The repository keeps runtime code independent from the test framework. Test-only
dependencies live in `requirements_test.txt`.

The test suite has three levels:

1. **HTTP client tests** validate Rustatio response envelopes, data shapes,
   bearer authentication and error mapping.
2. **Config-flow tests** validate setup, duplicate protection, recovery,
   reconfiguration and reauthentication.
3. **Home Assistant integration tests** set up a real config entry with mocked
   Rustatio responses and assert the public entity states exposed by Home
   Assistant.

Normal CI is pinned to the Home Assistant 2026.9.4-compatible test harness for
reproducibility.

A separate scheduled, non-blocking CI job installs the newest
`pytest-homeassistant-custom-component` package. Since that package tracks new
Home Assistant releases and betas, it acts as an early compatibility probe
without changing the supported-version promise of the integration.
