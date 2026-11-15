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

## Fixed exclusions

Do not create or edit `data.xml`, `mds.xml`, or `.vdf` files. They are outside this skill's project-generation responsibility.
