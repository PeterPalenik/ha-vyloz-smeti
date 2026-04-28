# Vyloz Smeti FCC SK — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://hacs.xyz)
[![Validate](https://github.com/PeterPalenik/ha-vyloz-smeti/actions/workflows/validate.yml/badge.svg)](https://github.com/PeterPalenik/ha-vyloz-smeti/actions/workflows/validate.yml)
[![Tests](https://github.com/PeterPalenik/ha-vyloz-smeti/actions/workflows/tests.yml/badge.svg)](https://github.com/PeterPalenik/ha-vyloz-smeti/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A [Home Assistant](https://www.home-assistant.io/) custom integration that exposes the
Slovak **FCC Vyloz Smeti** (`vylozsmeti.kabernet.sk`) waste-collection schedule as a
native HA `calendar` entity. Pick your municipality during setup and the
upcoming pickups for every waste type (mixed, plastic, paper, bio, glass, …) appear
on your dashboard, in automations and in voice assistants.

> The integration talks to the same public API as the
> [official FCC mobile app](https://play.google.com/store/apps/details?id=sk.fccgroup.vylozsmeti).
> No login required.

---

## Features

- One **calendar entity per municipality** with all upcoming collection events
- Locations, waste types and 2 years of schedule fetched in parallel
- Native config flow (UI install — no YAML)
- Options flow lets you tune the polling interval (1-24 h, default 6 h)
- Translations: English, Slovak
- Brand assets bundled locally — icon shows up immediately after install
- 100 % async, type-hinted, with `pytest` test suite

---

## Installation

### Via HACS (recommended)

1. Open HACS → **Integrations** → menu (top-right) → **Custom repositories**
2. Add `https://github.com/PeterPalenik/ha-vyloz-smeti` as **Integration**
3. Search for **Vyloz Smeti FCC SK** and install
4. Restart Home Assistant
5. **Settings → Devices & Services → Add Integration → Vyloz Smeti FCC SK**

### Manual

1. Download the latest release ZIP from the
   [releases page](https://github.com/PeterPalenik/ha-vyloz-smeti/releases)
2. Extract it to `<config>/custom_components/vyloz_smeti/`
3. Restart Home Assistant
4. Add the integration via **Settings → Devices & Services**

---

## Configuration

The config flow fetches the list of municipalities from the FCC API and presents
a single dropdown. Pick the city/town you live in. Done.

If two municipalities share the same name, the FCC location code is shown in
parentheses to disambiguate.

### Options

After install, click **Configure** on the integration card to change the
polling interval (1-24 hours, default 6).

---

## Entities

| Entity                                | Description                                |
| ------------------------------------- | ------------------------------------------ |
| `calendar.<municipality>_schedule`    | Upcoming waste collection events           |

Each calendar event's `summary` is the human-readable waste type name (in Slovak,
as returned by the FCC API).

### Example automation

```yaml
automation:
  - alias: "Notify me the evening before garbage pickup"
    triggers:
      - trigger: calendar
        entity_id: calendar.bratislava_schedule
        event: start
        offset: "-12:00:00"
    actions:
      - action: notify.notify
        data:
          title: "Tomorrow's pickup"
          message: "{{ trigger.calendar_event.summary }}"
```

---

## Development

```bash
git clone https://github.com/PeterPalenik/ha-vyloz-smeti.git
cd ha-vyloz-smeti
python -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pytest -v --cov=custom_components.vyloz_smeti tests/
ruff check .
ruff format --check .
```

To run the integration in a dev HA instance, symlink:

```bash
ln -s "$PWD/custom_components/vyloz_smeti" "$HA_CONFIG/custom_components/vyloz_smeti"
```

---

## How it works

```
       ┌───────────────────────┐
       │ vylozsmeti.kabernet.sk│
       │  /api/public/...      │
       └──────────┬────────────┘
                  │ aiohttp + 10 s timeout
                  ▼
       ┌───────────────────────┐
       │ VylozSmetiClient      │   api.py
       └──────────┬────────────┘
                  │ Location / WasteEvent / waste_types
                  ▼
       ┌───────────────────────┐
       │ VylozSmetiCoordinator │   coordinator.py
       │ DataUpdateCoordinator │   merges current + next year
       └──────────┬────────────┘
                  │ VylozSmetiData
                  ▼
       ┌───────────────────────┐
       │ VylozSmetiCalendar    │   calendar.py
       │ CalendarEntity        │
       └───────────────────────┘
```

Three endpoints are consumed:

| Method | URL                                                   | Purpose                                |
| ------ | ----------------------------------------------------- | -------------------------------------- |
| GET    | `/location?includeLocations=True`                     | List of all municipalities (for setup) |
| GET    | `/schedule/options?locationId=<id>`                   | Mapping of `wasteId` → human title     |
| GET    | `/schedule?locationId=<id>&year=<yyyy>`               | All collection events for a year       |

---

## Disclaimer

This is an **unofficial** integration. It is not affiliated with FCC Slovensko
or its parent companies. The integration uses the same public, unauthenticated
endpoints as the official mobile app.

The "Vyloz Smeti" name and app icon are the trademark of FCC Group; they are
re-used here only to make the integration immediately recognizable to Slovak
HA users.

## License

[MIT](LICENSE) — © 2026 Peter Palenik
