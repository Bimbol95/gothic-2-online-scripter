# Coding standards

Apply these standards to all new and modified project code. Do not rewrite unrelated existing files only to normalize their style.

## File encoding

Text files consumed directly by Gothic or the G2O runtime must use the exact regional `Windows-12xx` code page selected for the target server. This includes Squirrel scripts, XML manifests, and other runtime text files.

- Never save these files as UTF-8, UTF-8 with BOM, or another Unicode encoding.
- Determine the exact Windows code page from the user's requirement or explicit project evidence before writing files. Do not guess a code page from the language name alone.
- When editing an existing file, read and write it with its established regional code page. Do not let an editor or formatter silently convert it to UTF-8.
- Encode strictly. If a character cannot be represented, report it instead of replacing it with `?` or another fallback.
- An ASCII-only file must still be written through the selected Windows encoding workflow so later non-ASCII edits do not silently change the convention.
- Do not infer the encoding of a separate CEF web build from this rule. Follow that web project's explicit encoding/toolchain configuration; ask when it is not established.

This requirement applies to generated G2O project files, not to this Markdown skill package.

## Project settings

Store project configuration in `settings.nut` and expose one shared root table named `settings`:

```js
settings <- {
    debug = false,
    lobby = {
        minimum_players = 2,
        round_time_seconds = 300,
    },
}
```

Use `snake_case` for every settings key, including nested keys.

Good:

```js
round_time_seconds = 300
minimum_players = 2
spawn_position = Vec3(100.0, 200.0, 300.0)
```

Bad:

```js
roundTimeSeconds = 300
MinimumPlayers = 2
spawnPosition = {x = 100.0, y = 200.0, z = 300.0}
```

## Built-in shared value types

Use G2O's shared value classes instead of ad-hoc tables when they represent the value directly:

- `Color` for RGBA colors;
- `Vec3` for three-dimensional floating-point positions or vectors;
- `Vec2` for two-dimensional floating-point values;
- `Vec2i` for two-dimensional integer values such as pixel sizes.

```js
settings <- {
    team_color = Color(62, 139, 255),
    spawn_position = Vec3(100.0, 200.0, 300.0),
    map_scale = Vec2(1.0, 1.0),
    window_size = Vec2i(1280, 720),
}
```

Verify each class against the exact target-version API snapshot before use. These four classes are documented as shared in the included G2O 0.3.9 snapshot.

## Naming

- Classes: `PascalCase`; preserve an intentional acronym, for example `TDMService`.
- Class methods: `lowerCamelCase`, for example `findTeam`.
- Preserve established acronyms in uppercase inside class and method names: `TDMService`, `NPCManager`, `findNPC`, and `getUID`, not `TdmService`, `NpcManager`, `findNpc`, or `getUid`.
- Settings keys: `snake_case`.
- Class attributes and instance fields: `snake_case`, for example `stats_by_uid`.
- Local variables: `snake_case`, for example `team_config`.
- Function and method parameters: `snake_case`, for example `team_id`.
- Global variables: `snake_case`, for example `tdm_service`.
- Local and global standalone functions: `snake_case`.
- Event handler functions: event name without the `on` prefix, converted to `snake_case`, followed by `_handler`.
- Constants: `UPPER_SNAKE_CASE` when a real constant is needed outside the `settings` table.
- Internal instance fields may use a leading underscore when they are private implementation state.

Do not shorten ordinary words into clipped identifiers. Write `manager`, `service`, `message`, `request`, and `response`, not `mgr`, `svc`, `msg`, `req`, or `res`. Established domain acronyms such as `TDM`, `NPC`, and `UID` are allowed and follow the acronym rule above. In `snake_case` identifiers, keep them lowercase: `tdm_service`, `npc_manager`, and `player_uid`.

These naming rules apply to project-defined identifiers. Preserve the exact documented spelling of G2O and library APIs even when an external symbol follows a different convention.

Examples:

```text
onPlayerJoin       -> player_join_handler
onPlayerDisconnect -> player_disconnect_handler
onPlayerDamage     -> player_damage_handler
```

Good local names, parameters, and attributes:

```js
local team_id = 1
local team_config = settings.teams[team_id]

class PlayerSession {
    player_id = null
    stats_by_uid = null

    constructor(player_id) {
        this.player_id = player_id
        this.stats_by_uid = {}
    }
}
```

Bad:

```js
local teamId = 1
local teamConfig = settings.teams[teamId]

class PlayerSession {
    playerId = null
    statsByUid = null
}
```

## Concise contextual names

Prefer the shortest name that remains clear in its owning context. The receiver already supplies domain information, so do not repeat it in every method name.

Good:

```js
local function player_respawn_handler(player_id) {
    tdm_service.respawn(player_id)
}

addEventHandler("onPlayerRespawn", player_respawn_handler)
```

Bad:

```js
local function player_respawn_handler(player_id) {
    tdm_service.playerRespawn(player_id)
}
```

Other examples:

```text
player_manager.get(player_id)       not player_manager.getPlayer(player_id)
lobby_service.join(player)          not lobby_service.joinPlayer(player)
match_service.start(lobby)          not match_service.startMatch(lobby)
player_state.reset()                not player_state.resetPlayerState()
```

Keep the subject when the receiver does not provide it or manages several subject types. For example, a world service that manages both players and NPCs may need distinct `spawnPlayer` and `spawnNPC` methods.

Concise does not mean vague. Avoid names such as `do`, `run`, `process`, or `handle` when a precise action verb is available. Event handler functions are intentionally more explicit because their name documents the external event they receive.

## Method declaration syntax

Declare methods with Squirrel's method syntax inside classes and tables.

Good:

```js
function findTeam(team_id) {
    foreach (team_config in settings.teams) {
        if (team_config.id == team_id) {
            return team_config
        }
    }

    return null
}
```

For a table method:

```js
local team_lookup = {
    function findTeam(team_id) {
        foreach (team_config in settings.teams) {
            if (team_config.id == team_id) {
                return team_config
            }
        }

        return null
    },
}
```

Do not assign an anonymous function to a method slot:

```js
// Bad
findTeam = function(team_id) {
    return null
}
```

Anonymous functions remain appropriate as short callbacks passed directly to APIs such as `BPacketMessage.bind`.

## Prefer classes over service tables

Use a class when an object owns state or behavior. For a singleton, define a local class and assign one instance to a global `snake_case` variable.

Good:

```js
local class TDMService {
    sessions = null
    stats_by_uid = null

    constructor() {
        this.sessions = {}
        this.stats_by_uid = {}
    }

    function findClass(class_id) {
        foreach (class_config in settings.classes) {
            if (class_config.id == class_id) {
                return class_config
            }
        }

        return null
    }
}

tdm_service <- TDMService()
```

Bad:

```js
TDMService <- {
    sessions = {},
    statsByUid = {},

    findClass = function(classId) {
        return null
    },
}
```

Initialize mutable instance state such as arrays and tables in the constructor rather than sharing a mutable class-level default.

## Handler placement and sections

Keep event and packet handlers in `handlers.nut` inside the smallest feature directory they belong to:

```text
server/states/lobby/handlers.nut
client/states/lobby/handlers.nut
server/player/handlers.nut
```

Use section separators to keep entry points scannable:

```js
////////////////////////////////////////////
/// Events
////////////////////////////////////////////

local function player_disconnect_handler(player_id, reason) {
    local player = server.players.get(player_id)
    if (player && player.inState(PlayerState.LOBBY)) {
        server.lobby.service.leave(player)
    }
}

addEventHandler("onPlayerDisconnect", player_disconnect_handler)

////////////////////////////////////////////
/// Packets
////////////////////////////////////////////

LobbyLeaveMessage.bind(function (player_id, message) {
    local player = server.players.get(player_id)
    if (player) {
        server.flow.lobbyLeave(player)
    }
})
```

Place every `addEventHandler` immediately below the local function it registers. Do not collect registrations at the end of the file.

Handlers should be thin entry points: resolve the relevant player or object, reject invalid context, and delegate domain work to a service or state object.

## Networking rule

Never instantiate or use G2O's raw `Packet` class in project code.

- Use BPackets messages for simple client/server communication.
- Use BPackets requests for correlated request/response operations.
- As the project grows, use BNetReplicate for persistent synchronized state and keep BPackets for actions and requests that are not state replication.
- Validate every client-originated message, request, or replicated change on the server.

Bad:

```js
local packet = Packet()
// Manual header and field serialization.
```

Good:

```js
class LobbyLeaveMessage extends BPacketMessage {
}

LobbyLeaveMessage().serialize().send(RELIABLE)
```

Verify the target-version transport API and constants before sending.

## String interpolation

Use the modified Squirrel fork's backtick interpolation when inserting values into a string.

Good:

```js
local message = `Player ${player_name} joined team ${team_name}.`
```

Avoid unnecessary concatenation for the same case:

```js
// Bad
local message = "Player " + player_name + " joined team " + team_name + "."
```

Use ordinary quoted strings when no value is interpolated. See `references/squirrel-fork.md` for the documented syntax boundary.

## General formatting

- Use four spaces for indentation.
- Put the opening brace on the declaration line.
- Omit semicolons.
- Use `this.` for instance members.
- Use `::` only when deliberately addressing the root table or avoiding local shadowing.
- Keep entry points small: construct root objects, configure the side, and register only truly global behavior.
- Use BState lifecycle methods to acquire and release state-scoped resources. Explicitly clean up timers and other resources not owned by a binding.
