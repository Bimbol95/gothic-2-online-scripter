# CEF module

Authoritative source: <https://gothic-online.gitlab.io/modules/cef/>

The local documentation search index is stored at `references/cef/search_index.json` for exact offline lookup.

## Role and side

CEF provides in-game browser UI using HTML, CSS, and JavaScript, controlled from client-side Squirrel. Prefer it for UI unless the display is performance-critical and updated every frame, such as projected labels or billboards.

## Documented Squirrel surface

The documentation describes client-side `BrowserSettings`, `Browser`, and `JSPromise` APIs.

`Browser` is constructed with virtual position, virtual size, a URL, and an optional accelerated-mode flag. Its documented surface includes visibility and URL state, FPS and mute control, color/alpha, virtual and pixel position/size, z-order, active-browser control, focus information, table conversion policy, JavaScript calls/evaluation, and load/render/cursor/focus callbacks. Look up the exact declaration in the local search index before using a member.

`BrowserSettings` exposes documented global settings including volume, FPS, and waiting for pending GPU commands; availability is versioned in the module documentation.

`JSPromise` supports resolving or rejecting an asynchronous JavaScript-to-Squirrel call. A promise must be completed; after completion its `valid` property becomes false.

## Bridge directions

- Squirrel calls JavaScript through `browser.call(functionName, ...)`.
- JavaScript calls registered Squirrel functions through `squirrel.call(functionName, ...)`, which returns a JavaScript promise.
- A project can wrap browser calls in a client-side UI class and route JavaScript actions to active BStates through a custom BState binding.

Verify exact argument conversion and table conversion policy in the documentation before choosing a representation.

## Client wrapper example

Keep direct browser operations behind one client-side class:

```js
local virtual_extent = 8192

class CEFUI {
    browser = null

    constructor(url, fps) {
        this.browser = Browser(0, 0, virtual_extent, virtual_extent, url)
        this.browser.visible = false
        this.browser.fps = fps
        this.browser.muted = false
        this.browser.setTableToMap(false)
        this.browser.top()
    }

    function resize() {
        this.browser.setPosition(0, 0)
        this.browser.setSize(virtual_extent, virtual_extent)
    }

    function setVisible(visible) {
        this.browser.visible = visible
        if (visible) {
            Browser.setActive(this.browser)
        }
    }

    function setInteractive(interactive) {
        setCursorVisible(interactive)
        if (interactive) {
            Browser.setActive(this.browser)
        }
    }

    function setView(name, data = null) {
        this.browser.call("ui.setView", name, data)
    }

    function patchView(data) {
        this.browser.call("ui.patchView", data)
    }
}
```

Before using this example, verify `Browser` members and `setCursorVisible` against the relevant documentation and target G2O API snapshot.

## Construction and resolution changes

Create the browser eagerly in the UI constructor. If its prerequisites require `onInit`, construct the UI explicitly there. Do not create it on the first `show`, input event, or bridge call. UI may be constructed earlier when the documented API allows it.

Handle client `onChangeResolution` for CEF as well as native UI. In the included G2O 0.3.9 API this event has no parameters. Put the handler in the relevant client feature's `handlers.nut`; access the UI through its owner:

```js
local function change_resolution_handler() {
    core.ui.resize()
}

addEventHandler("onChangeResolution", change_resolution_handler)
```

This example assumes `core.ui` is the initialized wrapper above. Set up the owner at an explicit startup point before its handlers can consume it. Adapt `resize()` to the actual viewport/layout, recompute pixel-based dimensions when used, and ensure the web document responds to the new viewport. Keep existing browser instances; do not recreate them as a resize mechanism.

## Routing JavaScript actions to active BStates

JavaScript can send one named action through a stable Squirrel entry point:

```js
await squirrel.call("cef_action_handler", "lobby.create", name, password)
```

A custom BState binding can make annotated handlers active only while their state is active:

```js
if (!("Browser" in getroottable())) return

local active_states = {}

function cef_action_handler(name, ...) {
    local queue = []
    foreach (handlers, _ in active_states) {
        foreach (handler in handlers) {
            if (handler.name == name) {
                queue.push(handler.closure)
            }
        }
    }

    foreach (closure in queue) {
        closure.vcall(this, vargv)
    }
}

local class CEFBinding extends BStateBinding {
    name = "cef"

    function bind(closure, attrs) {
        this.handlers.push({name = attrs.cef, closure = closure})
        if (!active_states.rawin(this.handlers)) {
            active_states.rawset(this.handlers, true)
        }
    }

    function unbind() {
        if (active_states.rawin(this.handlers)) {
            active_states.rawdelete(this.handlers)
        }
    }
}

::BStateBinding.register(CEFBinding)
```

Use it from a client state:

```js
class LobbyViewState extends BState {
    </ cef = "lobby.create" />
    function onLobbyCreate(name, password) {
        // Send a validated request to the server.
    }
}
```

Load this binding after BStates and only on projects that load the CEF module. The example deliberately routes the action; it does not define the server request or authorize trusting browser input.

## URL protocols

The documentation describes:

- `cef://` for files placed in Gothic's virtual filesystem under `_WORK/DATA/WEB/`;
- `vdfs://` for an absolute path inside the game directory;
- `file://` for debug-server use when `<debug>true</debug>` is enabled;
- HTTP/S access subject to the configured whitelist.

The documentation discourages VDF for nested CEF assets because of its flat structure. This skill separately forbids creating or editing `.vdf` files because the user supplies them.

## Debugging evidence

With module debug mode enabled, the documentation describes Chromium remote inspection at `chrome://inspect#devices` with `localhost:9222`. It also documents two common diagnostics: incorrectly typed characters can be related to the system ACP/locale, and a bad IPC message can indicate incompatible CEF launcher/DLL files requiring a G2O reinstall.

Do not assume the module is installed or that a web development server is available. Use a development URL or build command only when it is present in the user's project.

