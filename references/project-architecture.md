# Preferred project architecture

Use root `client`, `server`, and `shared` directories. Do not create the alternative `client-scripts`, `server-scripts`, or `shared-scripts` naming variant.

## Baseline tree

```text
project/
|-- scripts.xml
|-- settings.nut
|-- shared/
|   |-- meta.xml
|   |-- enums.nut
|   |-- messages/
|   `-- replicated/
|-- server/
|   |-- meta.xml
|   |-- main.nut
|   |-- player/
|   `-- states/
|-- client/
|   |-- meta.xml
|   |-- main.nut
|   |-- states/
|   `-- ui/
|-- content/                 optional shared content definitions
`-- libs/                    only libraries actually used
```

Create only directories justified by the requested project. Small projects do not need empty `player`, `content`, `messages`, `replicated`, or `ui` layers.

Write Squirrel scripts, XML manifests, and other text files consumed directly by Gothic/G2O using the project's exact regional `Windows-12xx` code page, never UTF-8. Resolve that code page before creating the tree.

## Responsibility split

- `shared`: enums, immutable content definitions needed on both sides, packet message classes, BNetReplicate type declarations, and shared utilities.
- `server`: authoritative rules, validation, player/session ownership, state transitions, interest management, and handling client-originated requests.
- `client`: presentation, input, local state, CEF integration, view models, and reactions to replicated state or packets.
- `content`: optional shared definitions that are large enough to deserve a separate domain area.
- `libs`: the library implementation and its own manifest when the target project vendors a library.

A shared definition can describe a value used on both sides; it does not permit a client-only or server-only G2O call to execute on the wrong side.

## Logical flow and state ownership

Use a direct, readable call flow:

```text
Event or packet handler
  -> Orchestrator (for example GameFlow)
    -> State
      -> Service
        -> Helper classes
```

The orchestrator decides where execution goes next and coordinates transitions between domains. This is especially useful on the server when multiple sessions or domains are active rather than one global active state. A state owns the current domain/session context. Services implement cohesive operations against that state; they must not keep independent copies of it. Pass state or references to its owner instead of mirroring mutable values in services.

Omit an orchestrator or state layer when a handler can clearly delegate directly to a service. Split large state logic across services and local helper classes while preserving one owner of mutable state. Keep the execution path explicit; avoid chains of callbacks or indirection that obscure what runs and when.

## Root composition in `main.nut`

Keep globally accessible managers, services, and state machines under one global object named `core`. Client and server may each have their own `core` in their separate VMs. Define its class locally in that side's `main.nut` and compose dependencies eagerly.

This server composition example assumes its domain classes have already loaded:

```js
local class Core {
    lobby = null
    match = null
    browser = null
    flow = null
    players = null

    constructor(max_slots) {
        this.lobby = this.createLobbyState()
        this.match = this.createMatchState()
        this.browser = {
            service = BrowserService(this.lobby.manager, this.match.manager)
        }
        this.flow = GameFlow(this.browser.service, this.lobby.service, this.match.service)
        this.players = PlayerManager(max_slots)
    }

    function createLobbyState() {
        local manager = ::LobbyManager()
        local service = ::LobbyService(manager)

        return {manager = manager, service = service}
    }

    function createMatchState() {
        local manager = ::MatchManager()
        local service = ::MatchService(manager)

        return {manager = manager, service = service}
    }
}

///////////////////////////////////////////
/// Events
///////////////////////////////////////////

local function init_handler() {
    core <- Core(getMaxSlots())
}

addEventHandler("onInit", init_handler)
```

Treat the domain class names as project definitions, not built-in G2O APIs. Adjust dependency order to the actual constructor requirements. Attach any global state machine as a member of `core` as well. Access managers through `core.players` or `core.lobby.manager`, rather than adding parallel global `server`/`client` registries.

For a feature that needs initialization only at `onInit` and does not need global access, construct its object in a local variable in that handler. Ensure a real owner or registered callback retains it if it must outlive the handler. Prefer local functions and helper classes; expose only interfaces needed across files.

Do not use lazy creation. If runtime prerequisites require delayed startup, construct the complete object at the appropriate explicit lifecycle event. UI may be constructed earlier when its APIs allow it. See `references/runtime-lifecycle.md` for event ordering.

## Player and NPC API naming

Many stat, visual, equipment, animation, and state functions retain `setPlayer*`/`getPlayer*` names from the period before full NPC support. Their name does not necessarily restrict them to connected players: many resolve an ID through the common NPC registry and can operate on a player or a remote NPC. Client functions may also support negative-ID local NPCs, subject to their own restrictions.

When laying out a feature, choose the owning side and the actual entity kind first. Then verify each function's accepted ID, side, and behavior in the target-version API snapshot. Keep server-owned player/remote-NPC rules in `server`, client-only local-NPC and engine presentation in `client`, and shared definitions in `shared`. Do not invent a parallel `setNpc*` name simply because the target is an NPC.

## Root manifest pattern

This example shows the supported dependency order. Remove imports for unused libraries and ensure every referenced path exists.

```xml
<server>
    <!-- Libraries -->
    <import src="libs/bpackets/meta.xml" />
    <script src="libs/breplicate/config.nut" type="shared" />
    <import src="libs/breplicate/meta.xml" />
    <import src="libs/bstates/meta.xml" />

    <!-- Project settings and code -->
    <script src="settings.nut" type="shared" />
    <import src="shared/meta.xml" />
    <import src="content/meta.xml" />
    <import src="server/meta.xml" />
    <import src="client/meta.xml" />
</server>
```

The important order is:

1. BPackets before BNetReplicate because replicated fields use BPacket serializers.
2. BNetReplicate before the optional BStates replication binding.
3. Library-specific configuration before that library's manifest.
4. Shared project types before server and client consumers.
5. Side-specific entry points after their dependencies.

## Side manifests

A modular shared manifest can load foundations before messages and replicated types:

```xml
<server>
    <script src="enums.nut" type="shared" />
    <script src="utils.nut" type="shared" />
    <import src="content/meta.xml" />
    <import src="messages/meta.xml" />
    <import src="replicated/meta.xml" />
</server>
```

A server manifest should load models and services before handlers and its entry point:

```xml
<server>
    <import src="player/meta.xml" />
    <script src="states/base/manager.nut" type="server" />
    <import src="states/lobby/meta.xml" />
    <import src="states/match/meta.xml" />
    <script src="flow.nut" type="server" />
    <script src="main.nut" type="server" />
</server>
```

A client manifest should load UI and state definitions before constructing the client root:

```xml
<server>
    <import src="ui/meta.xml" />
    <import src="states/meta.xml" />
    <script src="main.nut" type="client" />
</server>
```

These are composition examples, not mandatory file lists. Do not emit an import for a layer that the project does not contain.

The project settings file is always `settings.nut` and defines `settings <- { ... }`. Library-owned configuration files keep the filenames required by their libraries.

Document every generated setting inline with its purpose and units. Load `settings.nut` before any constructor or definition that reads it.

## Internal organization choices

Use a simple state-oriented structure for a compact round-based project:

```text
server/states/lobby.nut
server/states/round.nut
client/states/lobby.nut
client/states/round.nut
shared/messages/lobby.nut
shared/messages/round.nut
```

Use a modular service-oriented structure when a domain has multiple operations and validation rules:

```text
server/states/lobby/object.nut
server/states/lobby/player-state.nut
server/states/lobby/manager.nut
server/states/lobby/service.nut
server/states/lobby/handlers.nut
```

In the modular pattern:

- object: server-owned domain data and behavior;
- player-state: the player's membership/context in that domain;
- manager: create, find, register, and destroy domain instances;
- service: validated operations and transitions, using concise method names that do not repeat the service's domain;
- handlers: thin G2O event and packet entry points that resolve a player and delegate to services.

Keep event and packet entry points in the feature-local `handlers.nut`. Load it after the feature's models, manager, service, and state classes. Place each `addEventHandler` directly below the local handler function it registers.

Do not force this five-file split onto a feature that has only one or two operations.

Use complete architectural names in files and identifiers: `manager`, `service`, `handlers`, and `player_state`, never clipped forms such as `mgr` or `svc`.

Extract repeated helper functions into an appropriately scoped `utils.nut`. Split oversized classes into focused classes, using `local class` when the helper is private to a file. For a class selector, keep input/selection and simple camera changes in `ClassSelector`, and presentation/layout in `ClassSelectorUI`.

## Fixed exclusions

Do not create or edit `data.xml`, `mds.xml`, or `.vdf` files. They are outside this skill's project-generation responsibility.
