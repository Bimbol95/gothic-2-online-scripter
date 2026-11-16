# G2O runtime and script lifecycle

Use this reference when a task depends on startup order, script loading, `onInit`, player lifecycle events, shutdown, or hot reload.

## Script workflow at a glance

The following order is the default mental model for implementing a feature. "Top-level" means statements executed while a `.nut` file is loaded, outside callbacks.

| Phase | Server scripts | Client scripts |
|---|---|---|
| Preparation | Parse configuration and ordered imports; create VM and bind server/shared API; load native modules | Connect, download resources and scripts, create local player, load Gothic world; create VM and bind client/shared API; load native modules |
| Script load | Execute server/shared files in configured order; run each file's reload callback after its top-level code | Execute client/shared files in archive order; run each file's reload callback after its top-level code |
| Initial callbacks | Validate instances, then `onInit` | Apply initial world state and call `onWorldEnter`; later call `onInit`, then `onPlayerCreate(heroId)` |
| Runtime | Process timers and `onTick`; invoke join, packet, streaming, damage, NPC and other event handlers as events occur | Process timers; invoke `onRender`, packet, input, create/spawn/unspawn, world and other client handlers as events occur |
| Teardown | `onPlayerDisconnect` precedes player removal; server `onExit` precedes VM destruction | Entity unspawn/destroy and script cleanup occur before the VM is destroyed |

Client globals `heroId`, `GameWorld`, and `WorldTimer` are bound during VM setup before any client `.nut` file is executed. Their *names* are therefore available to top-level client code. This does not mean that the local hero has already been spawned as a Gothic NPC: the initial `onPlayerCreate(heroId)` occurs after `onInit`, and spawning is a separate lifecycle step. See `client-zengin.md` for the values and object lifetimes.

Practical placement:

- Top-level code may define constants, functions/classes and register event handlers after their dependencies have loaded. It must not assume that `onInit` has already run.
- Top-level client code may refer to `heroId` and `GameWorld` because they have already been bound. Defer actions that require a spawned hero or completed feature initialization to the appropriate event; test for a live engine object before using it.
- Use `onInit` for one-time startup work requiring a fully initialized runtime. On the initial client load, `onWorldEnter` has already fired, so a feature needing both events must handle that ordering explicitly.
- Construct dependencies eagerly. If an object needs `onInit`, instantiate it explicitly inside a local startup handler; keep global managers/state machines in the `core` composed by `main.nut`. For objects without global access, use a local variable and retain them through their owner as needed. UI can be constructed earlier when its API prerequisites are satisfied. Do not replace lifecycle-aware construction with lazy getters or first-use initialization unless the user asks for lazy loading.
- Use `onPlayerCreate` for per-entity metadata, `onPlayerSpawn` for operations requiring the live Gothic NPC/Vob, and `onPlayerUnspawn`/`onPlayerDestroy` to release the corresponding resources.
- Use reload callbacks for setup that must also repeat after editing a reloadable script. Undo its handlers, timers, UI and engine objects in the unload callback. Reloading a single script does not rerun global `onInit`.
- Put shared definitions and custom NPC action registrations in the same deterministic order on both sides. A `shared` file executes independently in both VMs; it does not share its mutable variables.

## Runtime architecture

Gothic 2 Online has three relevant runtime layers:

- The launcher selects a server/version and starts `Gothic2.exe` with connection parameters. The supplied project description says a DLL-proxy chain chooses and injects the matching client DLL. This launcher detail is background context; the script lifecycle begins in the loaded client and the server.
- The client is an injected native DLL running inside Gothic II: Night of the Raven 2.6. It patches and hooks ZenGin, owns the client Squirrel VM, downloads server resources/scripts, renders presentation, reads input, and synchronizes the local simulation.
- The server is a standalone process. It owns connection admission, authoritative entity state, world/virtual-world membership, streaming decisions, script callbacks, NPC host assignment, and redistribution of synchronized state.
- The shared native layer defines wire packets, serialization, synchronization settings, common script bindings, action formats, and utilities used by both sides. It does not mean that arbitrary Squirrel state is automatically shared.

## Server lifecycle

The important order is:

1. The server reads its XML configuration (`config.xml` by default), including ordered imports, scripts, streamer settings, and synchronization settings.
2. It prepares networking, resource delivery, entity storage, and the streamer. The maximum number of player slots comes from `max_slots`.
3. It creates the server Squirrel VM and registers shared and server functions, classes, constants, and events.
4. It loads server native modules, executes server/shared `.nut` files in configured order, and validates the client/shared scripts for distribution.
5. It validates the required Gothic instance definitions.
6. Only then does it call script `onInit`.

During runtime the server processes incoming packets, script timers, hot reload, `onTick`, synchronization, and streamer refreshes. Network or world events invoke their registered script handlers when they occur.

Shutdown calls script `onExit` before destroying script state. World items and entity/grid registries are cleared before the Squirrel VM so native objects cannot call into an already-destroyed VM.


## Client lifecycle

The important order is:

1. The injected client starts inside Gothic, prepares the engine integration and reads connection settings.
2. It authorizes with the server, downloads required resources and the client script archive, and receives initial world and synchronization settings.
3. It creates the local player wrapper and loads the configured Gothic world.
4. It creates the client Squirrel VM and registers shared/client API, including the exposed ZenGin classes and globals such as `heroId` and `GameWorld`.
5. It loads client native modules and executes client/shared `.nut` files from the archive in configured order.
6. It applies initial world time/weather, then calls client `onWorldEnter`.
7. When gameplay becomes ready, it signals readiness to the server, calls client `onInit`, then `onPlayerCreate(heroId)`, and begins handling regular gameplay packets.

Therefore `onInit` means "all required runtime parts and all scripts have been initialized," not "the first script code executed." Top-level Squirrel statements run during script loading before `onInit`. Do not access state that is only created by another script's `onInit` from top-level code.

During ready-state frames, the client updates local-NPC range streaming, hosted-NPC synchronization, script timers/events, sounds, and projectiles. On disconnect it unspawns and releases entities and script-held objects before destroying the VM. On final game shutdown the state machine, hooks, and integrations are released.


## Script discovery and load order

Server configuration is traversed in XML order, including imported XML files at their position. A `<script>` entry has a side (`server`, `client`, or `shared`) and optional reload behavior.

- Server/shared scripts are executed in the server VM in discovered order.
- Client/shared scripts are compiled/validated by the server, packed into the client script archive, and listed in `scripts.xml` in discovered order.
- The client loads and executes that list in order.
- A native `<module side="server">` is loaded into the server process. Client modules are declared for the client download/load path.

Load dependencies before consumers on every applicable side. If shared code registers packet schemas, state definitions, or custom NPC action classes, it must precede handlers that use them. Custom NPC action IDs depend on identical registration order on server and client.

## Player lifecycle in scripts

Do not collapse creation, spawning, and connection into one event.

### Server flow

1. A transport connection and handshake validate client/build, bans, capacity, and create a pending connection.
2. The client patches/downloads resources and requests initial state. The server returns player ID, max slots, world, script password, time, weather, debug values, and synchronization settings.
3. After the initialized client signals readiness, the server creates its player record, sets nickname/world/credentials and default stream radius, announces creation to clients, inserts it into the streamer, then calls `onPlayerJoin(playerId)`.
4. The player starts unspawned. Scripts can keep the client in a login/character-setup UI while server rules validate and prepare it, then call `spawnPlayer(playerId)` to admit it to the streamed world. `unspawnPlayer(playerId)` returns it to the unspawned state without disconnecting. Stream radius is reset from configuration at join, so a custom radius belongs in `onPlayerJoin` or later.
5. Grid visibility later causes per-viewer spawn/unspawn messages. Server `onPlayerSpawnForPlayer(viewerId, entityId)` is cancellable and runs before a new directed visibility relationship is installed; the matching unspawn event runs when it is removed.
6. On disconnect, `onPlayerDisconnect(playerId, reason)` runs while the player still exists. The server then removes grid relations, broadcasts destruction, and destroys the registry entry.

`onPlayerConnect` appears among registered event names, but the analyzed implementation does not invoke it. Use `onPlayerJoin` for the first fully joined player callback and verify the target runtime if a feature depends on `onPlayerConnect`.

### Client flow

- `onPlayerCreate(id)` means the logical entity wrapper/metadata exists. It fires for the local hero after client `onInit`, for remote players/NPCs on create messages, and for locally created negative-ID NPCs.
- `onPlayerSpawn(id)` means a Gothic `oCNpc` has been materialized/enabled in the current world. It may occur repeatedly after unspawn.
- `onPlayerUnspawn(id)` means the world representation is being removed/disabled, but the logical remote entity may still exist.
- `onPlayerDestroy(id)` means the logical entity is being removed from the client registry. Destruction of a spawned entity first produces unspawn, then destroy.
- `onWorldEnter(world)` is distinct from `onInit`: it fires after initial world preparation and again after later world transitions.

Keep persistent per-entity metadata across spawn/unspawn, but release engine-object references on unspawn/destroy. Do not assume `onPlayerCreate` provides a valid `oCNpc`/Vob representation yet.

## Hot reload lifecycle

`<script ... reload="true" />` enables the server file watcher for that script. The watcher debounces changes (approximately 250 ms).

For a server/shared script reload:

1. The old script's `setUnloadCallback` callback runs, if registered.
2. The old compiled closure and its registered reload/unload callbacks are released and garbage collection runs.
3. The changed file is compiled and executed again, recreating top-level functions/classes/objects.
4. Its new `setReloadCallback` callback runs.
5. The client archive is regenerated when necessary.

For a client/shared script change, the server sends the changed source to all joined clients on the scripts channel; each client replaces that script with the same unload/compile/run/reload sequence. The regenerated archive is also used by future connections.

Important consequences:

- A reload does not automatically undo external registrations or engine objects created by the old script.
- The unload callback must remove event handlers, timers, projectors, UI, engine objects, and references owned by that script.
- Put initialization that must work both initially and after reload in the reload callback. In this implementation the reload callback also runs immediately after the first successful load.
- Avoid state split across reloadable files unless ownership and cleanup are explicit.

Official background: <https://docs.gothic-online.com/0.3.9/multiplayer/hot-reload/>.

## Implementation rules derived from the lifecycle

- Put cross-script registrations in deterministic load order; never depend on filesystem enumeration.
- Use `onInit` for work that requires the complete API, world, local hero, and all loaded scripts.
- Use `onPlayerJoin` for authoritative server initialization of a fully joined player.
- Separate logical entity lifetime from streamed Gothic-object lifetime.
- Make all reloadable scripts idempotent: one unload must reverse one initialization.
- Never report a client behavior as server-authoritative merely because the server redistributes it; check who produces and who validates the data.
