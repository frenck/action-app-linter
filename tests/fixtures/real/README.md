# Real apps

Configuration files of real apps, copied as they are, so a change to the
linter shows what it does to apps people actually ship. Only the files the
linter reads are here: `config`, `build` and `translations`.

The official and Community Apps must stay free of errors; see
`tests/test_real_apps.py`. To refresh one, copy its files again from a newer
commit, update the table, and review the snapshot diff.

| Fixture                  | Source                                                                                                         | Commit     | License    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------- | ---------- | ---------- |
| `official-*`             | [home-assistant/addons](https://github.com/home-assistant/addons)                                              | `d812da54` | Apache-2.0 |
| `community-example`      | [hassio-addons/app-example](https://github.com/hassio-addons/app-example) (`example/`)                         | `1cbc95b8` | MIT        |
| `community-vscode`       | [hassio-addons/app-vscode](https://github.com/hassio-addons/app-vscode) (`vscode/`)                            | `1f03c02c` | MIT        |
| `community-node-red`     | [hassio-addons/app-node-red](https://github.com/hassio-addons/app-node-red) (`node-red/`)                      | `1e66ffcb` | MIT        |
| `frigate`                | [blakeblackshear/frigate-hass-addons](https://github.com/blakeblackshear/frigate-hass-addons) (`frigate/`)     | `c8f95c1d` | MIT        |
| `zigbee2mqtt`            | [zigbee2mqtt/hassio-zigbee2mqtt](https://github.com/zigbee2mqtt/hassio-zigbee2mqtt) (`zigbee2mqtt/`)           | `f8264199` | Apache-2.0 |
| `zigbee2mqtt-proxy`      | [zigbee2mqtt/hassio-zigbee2mqtt](https://github.com/zigbee2mqtt/hassio-zigbee2mqtt) (`zigbee2mqtt-proxy/`)     | `f8264199` | Apache-2.0 |
