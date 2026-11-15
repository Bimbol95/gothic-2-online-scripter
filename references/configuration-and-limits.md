# Configuration and limits

Use this reference when reading or editing `config.xml`, deciding script/module/resource order, tuning streamer/synchronization settings, or validating values. Known differences between the analyzed implementation and published manual are recorded below.

## Configuration model

The server loads the file passed through `--config`, otherwise `config.xml`. The root must be `<server>`.

Core elements include:

- `<config public="..." host_name="..." max_slots="..." port="..." />`: required identity/listing/network values. Port is clamped to 1024..65535; slots to 1..512; host name is at most 32 characters.
- `<master url="..." />`: required by this parser, even when `public="false"`; public controls master registration.
- `<world name="..." />`: starting world, at most 32 characters; the parser normalizes it to uppercase.
- `<version build="..." />`: minimum accepted client build, stored as an 8-bit value; multiple entries can only raise the configured minimum.
- `<description>...</description>`: optional, at most 400 characters.
- `<debug ...>true|false</debug>`: optional console/debugger configuration. `chcp` accepts 1250..1258; debug log level accepts `trace|debug|info|warn|error|critical|off`.
- `<log_level>...</log_level>`: server logger level with the same names.
- `<tickrate-limit>...</tickrate-limit>`: server loop limit, accepted range 10..32767; absent/invalid becomes 60.
- `<data src="..." />`, `<mds src="..." />`, `<faceani src="..." />`, and `<wayfile src="..." />`: data/instance and lookup inputs needed by the selected project. Do not generate `data.xml` or `mds.xml`; this skill treats them as user-supplied.
- `<downloader>`, `<resource>`, `<streamer>`, and `<synchronization>`: content delivery and network behavior.

Paths for `<script>`, `<module>`, `<resource>`, and `<import>` are resolved relative to the XML file containing the element, except loaders whose own formats define another base. Imports must themselves have a `<server>` root.

Official overview: <https://docs.gothic-online.com/0.3.9/server-manual/configuration/>. Actual target parser behavior remains authoritative.

## Scripts, imports, modules, and resources

`<script src="..." type="client|server|shared" reload="true|false" />` determines both execution side and order.

- `server`: executed only in the server VM.
- `client`: compiled/packed by the server and executed only in each client VM.
- `shared`: loaded by both VMs; this shares definitions, not live variables.
- `reload="true"`: watched for hot reload; see `runtime-lifecycle.md`.

Elements and imports are traversed in document order. Wildcard script paths are accepted but filesystem enumeration order should not be used for dependencies. Prefer explicit ordered entries for schemas, custom NPC actions, inheritance, and entry points.

`<module>` loads a native `.dll`/`.so` on its declared side. Modules can be required/optional and may use checksums. Treat a module as native code with process-level lifetime, not as a Squirrel import.

`<resource>` publishes/downloads a VDF or ZIP. ZIP may be password-protected; this parser rejects `$` in the password. Resources change the client's available Gothic files and are loaded before gameplay.

## Streamer configuration

The current source defaults are:

| Setting | Default | Accepted source range | Meaning |
|---|---:|---:|---|
| `radius` | 3500 | 0..15000 | horizontal X/Z stream radius, Gothic world units |
| `height` | 2000 | 0..15000 | maximum vertical separation |
| `intervals/refresh` | 500 ms | 0..10000 | grid visibility refresh |
| `intervals/info` | 0 (disabled) | 500..60000 when present | non-streamed info broadcast |
| NPC state interval | 250 ms | 0..10000 | server action/state batch cadence |

Important: `radius` and `height` are required when a `<streamer>` element is present. Omitting `<streamer>` uses defaults.

### Source/manual discrepancies

- The official manual says streamer info defaults to 500 ms. This source sets `info_ms = 0`, explicitly disabled, and only runs it when nonzero.
- The manual presents NPC state under `<intervals><npc><state>...</state></npc></intervals>`. The current parser detects `<npc>` but then mistakenly searches `state` directly under `<intervals>`, not under the detected `<npc>`. Until the target build is verified/fixed, do not promise that the documented nested value takes effect.

These are runtime facts, not recommendations to exploit a parser bug. Preserve an existing working configuration and report the mismatch when a requested change depends on it.

## Synchronization configuration

The source defaults are:

| Setting | Default | Accepted range | Consumer |
|---|---:|---:|---|
| `broadcast-zone-distance` | 1250 | 500..15000 | server distance-based player update zones |
| `intervals/player` | 100 ms | 30..1000 | local-player movement production/interpolation base |
| `intervals/npc` | 400 ms | 30..1000 | hosted remote-NPC movement production/interpolation |
| `intervals/camera` | 500 ms | 30..1000 | camera/streamer-position updates |
| `intervals/wear` | 300 ms | 100..1500 | equipment polling/sync |

These values are sent to the client in initial state. They change traffic and perceived interpolation, not the server script `onTick` rate.

The published manual omits the implementation's `intervals/npc` and mentions a face-animation interval not present in the analyzed synchronization settings. For that implementation, use the table above; check the target parser when changing these fields.

Tuning consequences:

- smaller intervals increase responsiveness and bandwidth/CPU cost;
- larger movement intervals increase interpolation windows and visible delay;
- a smaller broadcast-zone distance makes update frequency degrade sooner with distance;
- streamer refresh controls spawn/unspawn latency, while synchronization intervals control already-streamed state.

## Limits

Validate at boundaries and avoid allocating protocol IDs as if they were unbounded.

| Value | Limit in the analyzed implementation |
|---|---:|
| connected player slots | 512 |
| player/host name | 32 characters |
| server description | 400 characters |
| ground item IDs | 65535 in source (`2^16 - 1`) |
| Daedalus instance IDs | 16777215 (`2^24 - 1`) |
| virtual-world value space | 16-bit; maximum 65535 |
| custom script NPC action types | 16384 |
| registered MDS entries in shared manager | 256 |
| registered face-animation entries | 256 |
| health/mana/strength/dexterity transport | signed 32-bit practical maximum 2147483647 |
| skill values | 8-bit practical maximum 255 |
| server world name | 32 characters |

The official limits page additionally records engine/gameplay constraints such as roughly `-640000..640000` map coordinates, scale `0..63`, fatness `-20..20`, and 4094 animation identifiers. Verify the exact setter's clamping and target-version API before generating boundary-sensitive code.

The official page lists 65565 ground items; the source encoding is 16 bits and defines `(1 << 16) - 1`, which is 65535. Treat 65565 as a documentation typo for this revision.

Official background: <https://docs.gothic-online.com/0.3.9/multiplayer/limits/>.

## Configuration review checklist

- Confirm the target G2O build before changing defaults.
- Preserve XML order for script dependencies and custom NPC action registration.
- Resolve imported paths relative to the importing file.
- Separate server tickrate, streamer refresh, and synchronization intervals; they control different loops.
- Check both documented syntax and the target parser for settings affected by known discrepancies.
- Never infer a Windows code page from `debug chcp`; confirm the project's required source-file encoding separately.
- Do not create or edit user-owned `data.xml`, `mds.xml`, or VDF files.
