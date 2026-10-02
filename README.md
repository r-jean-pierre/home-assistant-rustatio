# Rustatio for Home Assistant

A lightweight Home Assistant custom integration for
[Rustatio](https://github.com/takitsu21/rustatio).

It exposes useful **global Rustatio statistics** in Home Assistant without
creating an entity for every torrent.

Maintainer: **r-jean-pierre**

## Purpose

Rustatio internally works with torrent "instances". This integration translates
that implementation vocabulary into terms that are clearer in Home Assistant:

- **Managed torrents**: torrents currently known and managed by Rustatio.
- **Running torrents**: managed torrents whose Rustatio state is `running`.
- **Torrent files in watch folder**: `.torrent` files currently detected by the
  Rustatio watch service.
- **Torrents with tracker errors**: managed torrents currently exposing a
  structured tracker error.

This distinction is intentional. For example, the watch folder can contain more
`.torrent` files than Rustatio has successfully loaded as managed torrents.

## Features

- Local polling only.
- UI configuration through Home Assistant.
- Optional Rustatio API token support.
- Reconfiguration and reauthentication flows.
- A single shared `DataUpdateCoordinator`.
- One refresh every 30 seconds.
- No per-torrent Home Assistant entities.
- No parsing of application logs.
- No external Python dependencies.
- English and French translations.
- Local Home Assistant branding.
- HACS-ready repository structure.

## Entities

The integration creates one Rustatio service device with ten aggregate entities.

| Entity | Meaning |
| --- | --- |
| Connected | Whether the latest Rustatio API refresh succeeded |
| Managed torrents | Number of torrents currently managed by Rustatio |
| Running torrents | Managed torrents currently in the `running` state |
| Torrents with tracker errors | Managed torrents currently reporting a tracker error |
| Torrent files in watch folder | Number of `.torrent` files detected by the watch service |
| Simulated upload rate | Sum of current Rustatio simulated upload rates |
| Simulated download rate | Sum of current Rustatio simulated download rates |
| Total torrent size | Sum of the sizes of all managed torrents |
| Simulated uploaded | Sum of Rustatio cumulative simulated uploaded counters |
| Simulated downloaded | Sum of Rustatio cumulative simulated downloaded counters |

### Managed torrents attributes

The **Managed torrents** sensor also exposes aggregate diagnostic context:

```yaml
torrent_states:
  running: 1
  stopped: 62

torrent_sources:
  watch_folder: 63
```

The exact state/source keys come from Rustatio.

### Torrent files in watch folder attributes

The **Torrent files in watch folder** sensor also exposes:

```yaml
loaded_torrent_files: 63
watch_enabled: true
watch_folder: /torrents
auto_start: false
```

`loaded_torrent_files` is deliberately an attribute instead of another sensor:
it is useful diagnostic context without adding another entity.

## Data sources

The integration intentionally uses only two structured Rustatio endpoints:

```text
GET /api/instances/summary
GET /api/watch/status
```

All Home Assistant entities share the same coordinator refresh.

No values are extracted from Rustatio logs.

## Units

Rustatio returns cumulative data sizes as bytes. The integration keeps bytes as
the native Home Assistant value so the source value remains exact.

Suggested display units are:

- **Total torrent size**: TB
- **Simulated uploaded**: GB
- **Simulated downloaded**: GB

Home Assistant performs the display conversion and users remain free to choose a
different compatible unit in the entity settings.

Rustatio defines its current transfer rates in **KB/s**, so the rate sensors use
Home Assistant's `kB/s` data-rate unit.

## Why "simulated"?

Rustatio's upload/download counters and rates describe the transfer statistics
it simulates/announces. They are not measurements of actual network traffic.

The entity names make that distinction explicit.

## Installation with HACS

This repository is structured as a HACS integration repository.

Until/if the repository is included in the default HACS catalog, add it as a
custom repository:

1. Open **HACS**.
2. Open the menu and choose **Custom repositories**.
3. Add:

   ```text
   https://github.com/r-jean-pierre/home-assistant-rustatio
   ```

4. Select the category **Integration**.
5. Find **Rustatio** in HACS and download it.
6. Restart Home Assistant.
7. Go to **Settings → Devices & services → Add integration → Rustatio**.

When using the Rustatio Home Assistant App, the integration is discovered
automatically through Home Assistant Supervisor. No server URL needs to be
entered manually.

For a standalone Rustatio server, add the integration manually and enter the
server URL. Leave the API token empty unless Rustatio is configured with
`AUTH_TOKEN`.

## Manual installation

Copy:

```text
custom_components/rustatio
```

to:

```text
/config/custom_components/rustatio
```

Restart Home Assistant and add **Rustatio** from **Settings → Devices & services**.

## Authentication

Rustatio supports an optional bearer token through its `AUTH_TOKEN` environment
variable.

If authentication is disabled in Rustatio, leave the token empty.

If authentication is enabled, enter the same token during the Home Assistant
integration setup. If Rustatio later rejects the stored token, Home Assistant
starts a reauthentication flow.

## Design choices

The integration deliberately does **not** create entities for individual
torrents. A Rustatio installation can manage many torrents, and creating several
Home Assistant entities per torrent would quickly pollute the entity registry.

It also intentionally excludes aggregate seeder/leecher statistics, seed-time
progress, ETA/stop-condition progress and log-derived information. The goal is a
small integration based on stable, structured global data.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the implementation details.

## Compatibility

- Home Assistant: **2026.9.0 or newer**
- Rustatio: designed against the current Rustatio structured API
- HACS: supported as an Integration repository

## Development validation

The repository includes automated tests and GitHub Actions for:

- integration behavior and config-flow tests against **Home Assistant 2026.9.4**;
- code coverage with a **90% minimum**;
- Home Assistant **Hassfest**;
- **HACS** repository validation;
- a scheduled forward-compatibility run against the latest available
  `pytest-homeassistant-custom-component` test harness.

The normal test job is pinned to
`pytest-homeassistant-custom-component==0.13.367`, which maps to Home Assistant
2026.9.4. This keeps pull-request CI reproducible.

The scheduled forward-compatibility job intentionally follows the latest test
harness. It is allowed to fail without blocking releases: its purpose is to
surface upcoming Home Assistant compatibility changes early.

Local test command:

```bash
python -m pip install -r requirements_test.txt
pytest --cov=custom_components.rustatio --cov-report=term-missing -vv
```

## Project relationship

This repository contains only the Home Assistant integration.

Rustatio itself is developed independently by
[takitsu21](https://github.com/takitsu21/rustatio).

The integration is maintained by **r-jean-pierre**.

## License

The Home Assistant integration is licensed under the MIT License.

The bundled Rustatio brand icon comes from the upstream Rustatio project and
retains its upstream MIT attribution. See [NOTICE.md](NOTICE.md).
