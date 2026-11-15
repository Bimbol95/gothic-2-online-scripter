# Streaming and synchronization

Use this reference for visibility, player/NPC movement, NPC actions, packets, script context, and choosing client/server authority.

## Three different mechanisms

Keep these concepts separate:

1. **Creation/destruction** controls whether an entity ID and metadata exist in registries.
2. **Streaming (spawn/unspawn)** controls which created server entities have a live Gothic representation on a particular client.
3. **Synchronization** transports changing state for entities that already exist and, normally, are streamed to the receiver.

A created remote entity may be unspawned. An unspawn does not imply destroy. A client-created Vob or negative-ID local NPC is not made networked by the server streamer.

## Server spawn state and visibility

After joining, a player exists in the server registry but starts **unspawned**. Creating a remote NPC also leaves it unspawned. The server script must call `spawnPlayer(id)` for either kind of entity before the grid can stream it to other clients. Calling `unspawnPlayer(id)` later reverses that state without destroying the entity.

For a player, unspawn has two directions of effect: other players no longer see this player, and this player's client no longer receives streamed players and world items. Existing directed stream relationships are removed on the grid refresh, and the network worker clears its recipient routes for the unspawned entity. Its movement is therefore not forwarded to viewers. The connection and server-side entity still exist; do not confuse exclusion from streamed synchronization with a disconnect or removal of every incoming packet.

This is useful for a client UI stage such as login, character selection, or character setup: keep the joined player unspawned while the UI runs, then validate completion on the server, initialize the character, and call `spawnPlayer(id)`. To return to that stage, call `unspawnPlayer(id)` and restore the UI client-side. Do not use local UI visibility alone as the authority for entering the world.

`setPlayerInvisible(id, true)` is a different server-side control. It marks a spawned player or remote NPC as ineligible to be streamed **to other players**; already visible clients unspawn it on refresh. An invisible player can still receive and see other visible entities. `setPlayerInvisible(id, false)` permits normal streaming again, subject to spawn state, world, virtual world, distance, and the streamer's next refresh. It does not substitute for `spawnPlayer`: an unspawned entity remains unspawned even when invisibility is false.

## Server streamer

The server grid is a spatial hash. Each player is both a streamed entity and a receiver with a directed visibility set.

For receiver `A` and candidate `B`, validation requires:

- the same world and virtual world;
- `B` is marked spawned and not invisible;
- horizontal X/Z distance from `A`'s streamer position is within `A.stream_radius`;
- absolute vertical difference is within configured streamer height.

The streamer position comes from the receiver's camera sync, not necessarily the hero's feet. On the client it normally follows the camera target; with free/no-target camera it can use the camera Vob and falls back to the hero.

Visibility is directed. If players have different stream radii or camera positions, `A` may stream `B` while `B` does not stream `A`.

At each grid refresh:

1. Existing directed relations that fail validation are removed; the server calls the unspawn-for-player callback and sends unspawn.
2. Nearby chunks are scanned for new candidates.
3. Before adding a candidate, server `onPlayerSpawnForPlayer(receiverId, candidateId)` may cancel that one spawn.
4. The server sends a full player/NPC spawn snapshot.
5. It records the relationship in both entities and updates the network worker's fast routing table.

`sendStreamed(entityId, ...)` sends to the entity's current streamed receivers. It is not a distance query performed at send time.

Optional streamer-info broadcasts are different: they periodically send minimal information about non-streamed same-world entities, in batches, and do not spawn them.


## Player synchronization flow

The local client is the producer of moment-to-moment movement; the server validates context, stores a mirror, and redistributes it only to streamed viewers.

### Local client -> server

At the configured player interval (`foot_ms`), the client builds a compact movement packet containing position, angle, movement/animation flags, water/standing/diving/death state, weapon/walk mode, focus, animation progress, health/mana, and two guards:

- `time_context` invalidates movement from an older teleport/world/position epoch;
- `stats_context` prevents stale health/mana from overwriting a newer authoritative stats change.

Movement uses an unreliable sequenced delivery mode so newer state supersedes older state. Animation/state transitions, equipment, face animations, overlays, and similar discrete changes have their own packets/rates and may use reliable delivery.

The camera/streamer position is sent at `camera_ms`; equipment is checked at `wear_ms`.

### Server processing

The server finds the sender's player record, rejects mismatched time contexts, updates its authoritative mirror, and only accepts health/mana when the stats context matches. Script/server setters advance or preserve the relevant contexts and emit explicit change packets so delayed client movement cannot undo them.

The network worker forwards movement only along the streamer's routing table. It calculates a distance zone from `broadcast-zone-distance`; farther recipients receive fewer packets.

### Server -> viewing client

The receiver rejects stale time contexts, applies modes/stats/focus, and interpolates position/angle over approximately `foot_ms * streamer_zone`. Thus increasing the player interval or receiving a farther-zone update lengthens interpolation and lowers traffic.


## NPC identity and ownership

| Kind | ID space | Created by | Core networked | Streamed by |
|---|---:|---|---|---|
| Player | `0 .. max_slots-1` | server connection flow | yes | server grid |
| Remote NPC | `>= max_slots` (non-negative) | server `createNpc` flow | yes | server grid |
| Local NPC | `-1, -2, ...` | client script | no | client's local range spawner |

Remote NPC IDs are allocated after the reserved player slots. Client classification uses `id >= maxPlayers`. Local NPCs live in a separate client registry vector and only local-NPC APIs may create, destroy, or explicitly spawn them.

On the server, `createNpc(name, instance)` allocates the remote ID, sets its initial world, inserts it into the grid, broadcasts the logical create message, and fires `onNpcCreated(id)`. It is not spawned by default; a later `spawnPlayer` call makes it eligible for streaming. `destroyNpc(id)` removes it from the grid/registry, broadcasts destroy, and then fires `onNpcDestroyed(id)`. Because that callback is after registry removal, keep any metadata needed for cleanup separately or perform it before destruction.

The client local range spawner checks negative-ID NPCs roughly every 250 ms and enables/disables their Gothic Vobs around a fixed local range. Its `onPlayerSpawn`/`onPlayerUnspawn` events are client-local and unrelated to server grid relations.

Never send a negative local NPC ID to server APIs or assume another client can observe it. To share an NPC, create it on the server as a remote NPC.

## Remote NPC synchronization and host assignment

The server owns a remote NPC's identity, authoritative script-visible state, world/virtual world, spawn state, and action queue, but delegates live ZenGin simulation to one connected client called the host.

Host selection normally chooses the nearest player among clients currently streaming that NPC. It is reconsidered when the host no longer streams it, stops responding/times out, or during periodic host refresh. A manually selected host remains locked until it becomes invalid or times out.

When host changes:

1. The server sends a host-change message.
2. The old client removes the NPC from its hosted set; the new client adds it.
3. Client `onNpcChangeHost(npcId, isHost)` reflects the transition.
4. The new host begins producing movement/state/action results.

The host sends NPC movement batches at `npc_ms` (up to 16 entries per movement packet, unreliable sequenced). It sends state/action progress on a reliable ordered path. The server updates its NPC mirror and forwards movement to streamed clients except the host. Viewers interpolate over the configured NPC interval.

The server is still responsible for validating the sender/host and for distributing state. Hosting is delegated simulation, not ownership transfer to scripts on that client.


## NPC action model

NPC actions are ordered commands, not ordinary replicated properties.

Server flow:

1. A script/native call enqueues actions in the NPC's pending queue with monotonically increasing handles.
2. The server batches pending serialized actions and sends them to clients currently streaming the NPC.
3. Sent actions move to a waiting-for-result queue.
4. The assigned host executes the queue in the Gothic engine and reports result handles/data.
5. The server drains completed actions in handle order, calls completion logic/callbacks, and removes them from the waiting queue.

Client flow:

1. Every streamed client deserializes action batches in the same order for deterministic presentation.
2. The front action gets `onInit`, then `onUpdate` each frame until finished, then `getResult` and `onDeinit`.
3. Only the current host's result is authoritative and sent back to the server.

Built-in and custom actions share this ordered model. For a custom `NpcAction`:

- register the class on both sides in exactly the same script/load order;
- server side serializes parameters and handles completion;
- client side deserializes, initializes, updates, returns a result, and deinitializes;
- do not perform non-deterministic authoritative game rules independently on every viewing client;
- always clean client engine state in `onDeinit`, including interruption/failure paths.

Custom action numeric IDs are assigned by registration order and are limited by `MAX_SCRIPT_NPC_ACTIONS` (16384 in this source). A server/client order mismatch deserializes the wrong action class.

Official model: <https://docs.gothic-online.com/0.3.9/multiplayer/npc-action-model/>.

## Script packet communication

Native G2O uses typed internal packets and distinct RakNet ordering channels. Squirrel exposes the lower-level `Packet` API:

- client `Packet.send(reliability)` sends to the server on the scripts channel;
- server `send(playerId, reliability)` targets one joined player;
- server `sendStreamed(entityId, reliability)` targets the current streamed viewers of that player entity;
- server `sendToAll(reliability)` targets joined players;
- receiver events are client `onPacket(packet)` and server `onPacket(playerId, packet)`.

Read/write order and exact scalar widths must match. `onPacket` resets the packet read offset before each handler invocation, allowing independently registered handlers to inspect the same payload, but handlers still need an application-level message ID/schema.

For project code governed by this skill, use BPackets instead of raw `Packet`; use BNetReplicate for persistent, lower-frequency shared state. The raw layer is documented here to explain transport flow, not to override the project policy.

Reliability selection matters:

- unreliable sequenced for replaceable high-frequency snapshots;
- reliable/ordered for commands, creation/destruction, inventory, actions, and state transitions that must not be lost or reordered.

Do not broadcast information that only streamed viewers need, and never trust client-provided authoritative values without server validation.


## Script context

Script context is an integer correlation field attached to selected built-in multiplayer operations. It is not an ambient networked dictionary.

The analyzed implementation defines two context slots:

- `DAMAGE_CTX`: client hit packets carry the attacker's context; the server exposes it while processing the damage callback.
- `EQUIPMENT_CTX`: equipment/item-use synchronization carries context so the receiving side can identify project-specific item state when a Daedalus instance alone is insufficient.

Client `setContext(type, value)` writes the local player's outgoing/internal context. `getContext(type)` reads the context made current while a matching incoming operation/callback is processed. Server player/NPC context accessors store/expose the corresponding values. Missing/cleared context returns `-1`.

Use it as follows:

1. Assign a stable project identifier before the built-in damage/equipment operation.
2. Let G2O attach it to that operation's packet.
3. Read it only in the corresponding server/client callback.
4. Treat `-1` as no custom context and do not assume the value persists for unrelated events.

Official background: <https://docs.gothic-online.com/0.3.9/multiplayer/script-context/>.

