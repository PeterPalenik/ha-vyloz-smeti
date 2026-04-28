# Vyloz Smeti FCC SK

Home Assistant calendar integration for the Slovak **FCC Vyloz Smeti** waste
collection service ([vylozsmeti.kabernet.sk](https://vylozsmeti.kabernet.sk)).

After install, pick your municipality from a dropdown and a `calendar` entity
will list every upcoming pickup for every waste type (mixed, plastic, paper,
bio, glass, …) for the current and following year.

- 100 % async, no YAML, native config + options flow
- English and Slovak translations
- Polling interval is configurable (1-24 h, default 6)
- No login required — uses the same public endpoints as the official mobile app

See the [README](https://github.com/PeterPalenik/ha-vyloz-smeti) for setup,
example automations and the API reference.
