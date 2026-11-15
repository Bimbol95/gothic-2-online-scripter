# BPackets reference

BPackets defines typed Squirrel message classes over G2O `Packet` objects. Use it for discrete messages, commands, notifications, and correlated request/response flows. Library internals use `Packet`; project code must not instantiate or manually serialize a raw `Packet`.

## Load order

The library manifest loads shared files in this order:

1. `types.nut`
2. `message.nut`
3. `request.nut`

Load project message declarations on both sides in the same order. Concrete `BPacketMessage` subclasses receive sequential internal IDs when their classes are inherited; the serialized header is `100 + internal_id`. Different declaration order between client and server can map one header to different classes.

## Field serializers

| Serializer | Value |
|---|---|
| `BPacketBool` | Boolean |
| `BPacketInt8`, `BPacketUInt8` | Signed/unsigned 8-bit integer |
| `BPacketInt16`, `BPacketUInt16` | Signed/unsigned 16-bit integer |
| `BPacketInt32`, `BPacketUInt32` | Signed/unsigned 32-bit integer |
| `BPacketFloat` | Float |
| `BPacketString` | String |
| `BPacketAny` | Runtime-tagged supported value |
| `BPacketArray(type = BPacketAny)` | Typed array |
| `BPacketTable(index_type = BPacketAny, value_type = BPacketAny)` | Typed table |
| `BPacketInstance` | Squirrel class instance |
| A `BPacketMessage` subclass | Nested message |

`BPacketAny` recognizes `null`, Boolean, integer, float, string, array, table, instance, and `BPacketMessage`. Its dynamic arrays and tables encode their count as `UInt8`; typed `BPacketArray` and `BPacketTable` encode their count as `UInt16`.

## Declaring a message

Every serialized instance member needs a `type` attribute:

```js
class LobbyChatMessage extends BPacketMessage {
    </ type = BPacketUInt16 />
    player_id = -1

    </ type = BPacketString />
    text = ""

    </ type = BPacketString, optional = true />
    channel = null
}
```

The inherited constructor assigns positional arguments in field declaration order:

```js
local message = LobbyChatMessage(4, "Hello", null)
```

`serialize()` creates a `Packet`, writes the `UInt16` message header, then writes fields in declaration order.

## Optional fields

An optional field is encoded only when its value is not `null`:

```js
</ type = BPacketInt32, optional = true />
time_left_ms = null
```

The library writes an optional-field bit mask before the fields. It supports at most 32 optional fields and throws when that limit is exceeded. Use `null` to omit an optional value; a non-null default is transmitted.

## Arrays, tables, nested messages, and instances

```js
class BonusMessage extends BPacketMessage {
    </ type = BPacketInt32 />
    value = 0
}

class InventoryMessage extends BPacketMessage {
    </ type = BPacketArray(BonusMessage) />
    bonuses = null

    </ type = BPacketTable(BPacketString, BPacketInt32) />
    amounts = null
}
```

`BPacketInstance` writes the instance's class name and its members. During reading, the class must be resolvable from the root table unless an alias was registered:

```js
BPacketInstance.register_class("Friend", Friend)
```

Deserialization creates an instance, attempts its parameterless constructor, and then fills its fields. Use this only for classes whose serialized members and construction behavior are safe and stable on both sides.

## Sending and receiving

Server to one client:

```js
LobbyChatMessage(player_id, text).serialize().send(player_id, RELIABLE)
```

Client to server:

```js
local message = LobbyChatMessage(-1, text)
message.serialize().send(RELIABLE)
```

Verify the exact G2O `Packet.send` declaration and transport constant in the target-version API snapshot.

Bind a client receiver:

```js
LobbyChatMessage.bind(function (message) {
    print(message.text)
})
```

Bind a server receiver:

```js
LobbyChatMessage.bind(function (player_id, message) {
    // Validate player_id and message before acting.
})
```

`bind(callback)` returns the callback. `unbind(callback)` removes that handler after the next cleanup pass, and `clear()` removes all handlers for the message class. BPackets also emits `BPacket:onReceive`: the client event receives `message`; the server event receives `player_id, message`.

## Request and response

Both request and response classes extend `BPacketRequest`, because the library carries an internal request ID in each serialized request message.

```js
class CreateLobbyRequest extends BPacketRequest {
    </ type = BPacketString />
    name = ""
}

class CreateLobbyResponse extends BPacketRequest {
    </ type = BPacketBool />
    success = false

    </ type = BPacketString, optional = true />
    error = null
}
```

Client request:

```js
CreateLobbyRequest("Arena").request(function (response) {
    if (!response.success) {
        print(response.error)
        return
    }

    print("Lobby created")
})
```

Server response:

```js
CreateLobbyRequest.bind(function (player_id, request) {
    if (request.name == "") {
        request.response(player_id, CreateLobbyResponse(false, "empty_name"))
        return
    }

    request.response(player_id, CreateLobbyResponse(true))
})
```

On the client, `request(callback)` sends reliably to the server and registers a one-shot callback. On the server, the symmetric form is `request(player_id, callback)`. Response signatures are `response(message)` on the client and `response(player_id, message)` on the server. When the matching response arrives, the callback runs and is then unregistered.

## Additional API

- `MessageClass.fromObject(table_or_instance)` copies fields by name and skips absent optional fields.
- `message.format()` prints the internal packet ID and declared fields for debugging.
- `MessageClass.deserialize(packet, skip_header = false)` reads a message.
- `MessageClass.getByHeader(header)` returns the registered message class or `null`.
- A class declared with an `abstract` inheritance attribute does not receive a concrete message ID.

## Reliability constraints

- Declare wire classes in shared code and preserve identical load order on both sides.
- Treat every client-originated field as untrusted and validate it on the server.
- Do not change field order or serializer type without considering wire compatibility.
- Use optional fields for omitted values, not for silently accepting incompatible schemas.
- Use BNetReplicate instead when the real requirement is persistent synchronized state rather than discrete communication.
