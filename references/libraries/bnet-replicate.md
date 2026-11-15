# BNetReplicate reference

The library is commonly described as BNetReplicate; its global facade is `BNetReplication`. It synchronizes server-owned objects and arrays to interested clients and batches create, update, and destroy changes into delta messages.

Use it when clients need a durable view of server state without manually coordinating packets for every lifecycle change.

## Prerequisites and configuration

BNetReplicate uses BPackets serializers, so load BPackets first. Load the replication configuration before the replication manifest. The supplied defaults are:

```js
const BNET_SYNC_INTERVAL = 200
const BNET_OBJECT_INDEX_BITS = 20
const BNET_OBJECT_GENERATION_BITS = 12
```

Do not change object-ID bit allocation casually; both sides must share the configuration and existing IDs rely on that representation.

Load BStates after BNetReplicate when the BStates replication annotation is needed.

## Core model

- `BNetObject`: base class for replicated objects.
- `BNetArray(type, attributes = null)`: creates a replicated array type.
- `BNetMode.SERVER`: default server-owned mode.
- `BNetMode.SHARED`: permits client change requests after server validation.
- `BNetInterest(players = null)`: server-side visibility set.
- `BNetReplication`: global runtime facade.

The server remains authoritative. `BNetMode.SHARED` does not grant a client direct authority; it only enables a request path.

## Defining replicated types

```js
class NetLobbyMember extends BNetObject {
    </ type = BPacketUInt16 />
    player_id = -1

    </ type = BPacketInt8, mode = BNetMode.SHARED />
    team_id = -1

    </ type = BPacketBool, mode = BNetMode.SHARED />
    is_ready = false
}

NetLobbyMemberArray <- BNetArray(NetLobbyMember)

class NetLobby extends BNetObject {
    </ type = BPacketUInt16 />
    id = -1

    </ type = BPacketString />
    name = null

    </ type = NetLobbyMemberArray />
    members = null

    constructor(id, name) {
        base.constructor()
        this.id = id
        this.name = name
        this.members = ::NetLobbyMemberArray()
    }
}
```

Field serializers use the same serializer types as BPackets. Referenced net objects and net arrays are transmitted by object ID and resolved through the runtime registry.

## Server mutation

The server changes fields through normal assignment:

```js
lobby.name = "Arena #1"
member.is_ready = true
```

Server-side arrays support:

```js
lobby.members.push(member)
lobby.members.insert(0, member)
lobby.members.set(0, replacement)
lobby.members.remove(0)
lobby.members.clear()
```

`values()` returns the current backing array directly. Store a frequently used array type in a named variable instead of constructing the array type repeatedly.

Direct client structural mutation through `push`, `insert`, `set`, `remove`, or `clear` is blocked. Clients use `replicate(...)` only on arrays declared with `BNetMode.SHARED`.

## Interest and visibility

An object is created only for players included in at least one attached interest source:

```js
local lobby_interest = BNetInterest()
lobby_interest.insert(player_id)

lobby.net_state.addInterest(lobby_interest)
```

Remove a player or detach the source:

```js
lobby_interest.remove(player_id)
lobby.net_state.removeInterest(lobby_interest)
```

The final visible set is the union of every interest source attached to the object. If a player disappears from all attached interests, the object is destroyed on that client.

Propagate an interest to referenced children:

```js
lobby.net_state.addInterest(lobby_interest, true)
lobby.net_state.removeInterest(lobby_interest, true)
lobby.net_state.clearInterests(true)
```

Referenced fields and reference arrays inherit interest by default. Disable inheritance for an independently visible child:

```js
</ type = NetPrivateState, inherit_interest = false />
private_state = null

NetDetachedMemberArray <- BNetArray(NetLobbyMember, {
    inherit_interest = false
})
```

When an inherited reference is replaced or removed on the server, the old child has the parent's current interest sources detached automatically. Interest entries include player-slot generation, preventing a disconnected session's stale entry from applying to a later session that reuses the same player ID.

## Client lifecycle events

Global events:

```js
addEventHandler("BNetReplication:onCreate", function (instance) {
    print("created: " + instance)
})

addEventHandler("BNetReplication:onUpdate", function (instance, changes) {
    print("updated: " + changes.len())
})

addEventHandler("BNetReplication:onDestroy", function (instance) {
    print("destroyed: " + instance)
})
```

Class-level signals:

```js
NetLobby.onCreate.bind(function (lobby) {
    return true
})

NetLobby.onUpdate.bind(function (lobby, changes) {
    return true
})
```

Instance-level signals omit the instance argument where it is already known:

```js
lobby.onUpdate.bind(function (changes) {
    foreach (change in changes) {
        print(change)
    }

    return true
})
```

Object updates contain a field name and value. Array updates contain an operation and, where relevant, an index and value. Payloads are normalized by the serializer before events are emitted.

## Related updates

`onUpdate` is emitted for the object or array whose own state changed. Referencing parents receive `onUpdateRelated` when a child or descendant changes.

```js
NetLobby.onUpdateRelated.bind(function (lobby, changes) {
    foreach (change in changes) {
        print(change.source)
        print(change.updates.len())
    }

    return true
})
```

Each related entry has this shape:

```js
{
    source = child_or_descendant,
    updates = [/* normalized updates */]
}
```

Duplicate references from one parent are counted. Removing one reference does not detach the relationship while another reference remains.

## Client object lists

Each replicated class maintains a client-side list of live instances:

```js
foreach (lobby in NetLobby.objects.all()) {
    print(lobby.name)
}

if (NetLobby.objects.has(lobby)) {
    print("still tracked")
}
```

The client runtime updates this list when create and destroy messages arrive.

## Client change requests

Request a `BNetMode.SHARED` object field change:

```js
member.replicate("is_ready", true)
```

Declare a shared array before requesting structural changes:

```js
NetRequestedNameArray <- BNetArray(BPacketString, {
    mode = BNetMode.SHARED
})

class NetParty extends BNetObject {
    </ type = NetRequestedNameArray />
    requested_names = null

    constructor() {
        base.constructor()
        this.requested_names = ::NetRequestedNameArray()
    }
}
```

Request operations on an instance of that array type:

```js
party.requested_names.replicate(BNetArrayOperation.PUSH, "Patryk")
party.requested_names.replicate(BNetArrayOperation.INSERT, 0, "Patryk")
party.requested_names.replicate(BNetArrayOperation.SET, 0, "New name")
party.requested_names.replicate(BNetArrayOperation.REMOVE, 0)
party.requested_names.replicate(BNetArrayOperation.CLEAR)
```

The client sends intent. The server resolves references, verifies the field/array mode, emits validation signals, and applies only accepted changes.

## Server request validation

Request handlers receive `player_id`, the target instance, and one parsed change.

Object change:

```js
{
    field = "name",
    value = "New name"
}
```

Array changes use `operation` plus `index` and/or `value` as required by the operation.

Prefer class-level or instance-level validation for domain rules:

```js
NetLobbyMember.onRequestUpdate.bind(function (player_id, member, change) {
    if (change.field == "is_ready") {
        return member.player_id == player_id
    }

    return false
})
```

Class-level and instance-level validators return `true` to accept and `false` to reject. If any signal rejects, the change is not applied.

The global event can reject with `cancelEvent()`:

```js
addEventHandler("BNetReplication:onRequestUpdate", function (player_id, instance, change) {
    if (instance instanceof NetLobbyMember && instance.player_id != player_id) {
        cancelEvent()
    }
})
```

If the global event does not cancel, validation continues to class-level and instance-level signals. Never accept a request solely because its field is marked `SHARED`; validate ownership, current player state, allowed values, and relevant domain invariants.

## Runtime facade

```js
BNetReplication.flush()
BNetReplication.registry.getObject(object_id)
BNetReplication.awaitCreate(object_id, callback)
BNetReplication.awaitUpdate(object_id, callback)
```

- `flush()` immediately flushes pending replication work or client requests.
- `awaitCreate` runs immediately when the client already has the object; otherwise it waits for its create delta.
- `awaitUpdate` registers only when the object already exists. Its callback is removed after it returns anything except `false`; return `false` to wait for another update.

Each instance exposes:

```js
object.net_state.object_id
object.net_state.addInterest(interest, true)
object.net_state.removeInterest(interest, true)
object.net_state.clearInterests(true)
object.net_meta.type_id
```

Prefer public fields, signals, replication methods, and interest methods over direct mutation of internal runtime state.

## Object IDs

Object IDs are generation-tagged 32-bit values. Lower bits identify the registry slot and higher bits identify its generation. When a slot is released, its generation advances before reuse so stale references from old packets, callbacks, or requests do not target the new object.

## Appropriate uses and limits

Appropriate state includes lobbies, parties, match data, scoreboards, inventories, and lightweight world objects observed by multiple clients.

Do not use BNetReplicate as a substitute for:

- server-side validation;
- an extremely frequent custom synchronization stream;
- a one-off action that is clearer as a BPackets message or request;
- visibility rules that have not been expressed through interest sets.
