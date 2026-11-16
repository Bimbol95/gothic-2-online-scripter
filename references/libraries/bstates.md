# BStates reference

BStates is a shared state-stack library. Use it when behavior has a clear enter/exit lifecycle or when event, packet, or replication handlers should exist only while a state is active.

## Load order

The library manifest loads these shared files in order:

1. `machine.nut`
2. `bindings.nut`
3. `state.nut`
4. `bindings/events.nut`
5. `bindings/bpackets.nut`
6. `bindings/bnetreplication.nut`

The BPackets binding stops loading when `BPacketMessage` is absent. The replication binding stops loading when `BNetReplication` is absent. Therefore import BPackets and BNetReplicate before BStates when those bindings are needed.

## `BStateMachine`

| Member | Behavior |
|---|---|
| `BStateMachine()` | Creates an empty stack. |
| `push(state)` | Pushes the state and enters it. |
| `pop()` | Pops and exits the current state; does nothing when empty. |
| `change(state)` | Calls `pop()` and then `push(state)`. |
| `current()` | Returns the top state or `null`. |

`push` does not automatically exit the previous state. Use it for a stacked state that should later reveal the previous one. Use `change` when replacing the current state.

## `BState` lifecycle

Subclass `BState` and override `onEnter` and `onExit`:

```js
local update_interval_ms = 200

class LobbyState extends BState {
    _timer = -1

    function onEnter() {
        this._timer = setTimer(this.onUpdate.bindenv(this), update_interval_ms, 0)
    }

    function onExit() {
        if (this._timer != -1) {
            killTimer(this._timer)
            this._timer = -1
        }
    }

    function onUpdate() {
        // State-specific work.
    }
}
```

Entry order is:

1. create binding instances and bind annotated methods;
2. assign the owning machine to `state.machine`;
3. call `onEnter()`.

Exit order is:

1. call `onExit()`;
2. unbind registered handlers;
3. clear the state binding list.

Annotations manage their own handlers, but not arbitrary resources created in `onEnter`. Explicitly release timers and similar resources in `onExit`.

## Event binding

Annotate a state method with `event` and optional `priority`:

```js
class LobbyState extends BState {
    </ event = "onPlayerJoin", priority = 10 />
    function onPlayerJoin(player_id) {
        // Active only while this state is on the machine.
    }
}
```

If `priority` is omitted, the binding passes `9999` to `addEventHandler`. On exit it calls `removeEventHandler` with the same event name and bound closure.

## BPackets binding

Use a message class as the annotation value:

```js
class LobbyState extends BState {
    </ packet = LobbyChatMessage />
    function onLobbyChat(player_id, message) {
        // Server-side callback signature.
    }
}
```

On the client, the callback receives only `message`. On the server, it receives `player_id, message`. The binding calls the message class's `bind` on state entry and `unbind` on state exit.

## BNetReplicate binding

Bind one signal:

```js
</ replication = NetLobby.onUpdate />
function onLobbyUpdate(lobby, changes) {
    // Class-level client signal.
}
```

Or bind multiple signals to one method:

```js
</ replication = [NetLobby.onCreate, NetLobby.onDestroy, NetLobby.onUpdateRelated] />
function onLobbyChanged(...) {
    // Handle the signatures of the selected signals.
}
```

The binding accepts either a single signal or an array. It calls `bind` for every signal on entry and `unbind` on exit.

## State transition example

```js
class LobbyState extends BState {
    </ packet = StartMatchMessage />
    function onStartMatch(message) {
        this.machine.change(MatchState(message))
    }
}

local states = BStateMachine()
states.push(LobbyState())
```

Declare `StartMatchMessage` before this state and load BPackets before BStates so the packet binding exists.

## Custom bindings

Custom bindings extend `BStateBinding`, set a unique `name`, implement `bind(member, attrs)` and `unbind()`, and register their class with:

```js
::BStateBinding.register(CustomBinding)
```

`BState` looks for an annotation attribute whose name matches the binding's `name`. A binding stores the bound closures or signals in `this.handlers` so it can undo registration on exit.

## Constraints

- A state method is bound only when it is a function with attributes.
- Binding methods receive `member.bindenv(state)`, so `this` inside the handler is the state instance.
- BStates does not clean up resources it did not register.
- Do not use state-scoped bindings for handlers that must remain active across every state unless they live in a persistent parent state by design.
