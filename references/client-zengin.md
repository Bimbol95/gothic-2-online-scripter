# Client ZenGin model

Use this reference for client tasks that touch Gothic's world, Vobs, Mobs, NPC engine objects, VisualFX/PFX, 3D projection, or native UI.

## Two object models coexist

Client scripts work with both:

- **G2O multiplayer entities**: integer IDs, registries, remote/local ownership, creation, streaming, synchronization, and script events.
- **ZenGin objects**: native `zCObject`-derived instances such as `oCWorld`, `zCVob`, `oCNpc`, Mobs, visuals, and UI views inside the Gothic process.

An entity ID is not a Vob pointer. A remote entity can exist while unspawned and therefore have no live `oCNpc`. A ZenGin Vob created or modified by client code is local unless project code explicitly synchronizes the intended state.

Never retain native pointers/references across `onPlayerUnspawn`, `onPlayerDestroy`, `onWorldEnter`, world change, disconnect, or hot reload unless the target API explicitly guarantees their lifetime.

## Built-in client globals

The client binds these names in the Squirrel root table while setting up the VM, after creating the local player wrapper and loading the initial Gothic world, but before executing any downloaded client/shared script. They are available without an import or custom declaration. They do not exist in the server VM.

| Global | Type | Meaning and use |
|---|---|---|
| `heroId` | `int` | ID of this client's local multiplayer player. Pass it to applicable `getPlayer*`/`setPlayer*` functions; it is an ID, not an `Npc`/Vob object. Different connected clients have their own local `heroId`. |
| `GameWorld` | `World&` | Borrowed wrapper for the current Gothic `oCWorld` bound when this client VM is created. Use its world/Vob search, picking, tracing, and metadata API where supported. It is an engine object, not a server virtual-world ID or a filename. |
| `WorldTimer` | `Timestep&` | Borrowed wrapper for the engine time-step object; exposes frame and elapsed timing properties. It is not a server tick counter. |

Availability has two levels. The globals themselves are registered before top-level `.nut` statements run, so a script can read `heroId` or use `GameWorld` during loading. The hero's live Gothic `Npc`/Vob representation has a separate spawn lifecycle; `onPlayerCreate(heroId)` initially fires after client `onInit`, and `onPlayerSpawn` is the event to use when a live world object is required. `GameWorld` is borrowed from the engine, so avoid caching its derived Vob pointers across world changes and recheck the current world in world-related callbacks. The implementation does not establish that a previously cached world reference is refreshed after a world transition.

For a new feature, look up the global's exact side/type in the target-version API snapshot before writing code. Do not invent server equivalents or infer that a `World&` can be sent over the network.

## World

`World` wraps the current Gothic `oCWorld`, which derives from `zCWorld`/`zCObject`. It is the engine container for the loaded `.ZEN` world, not a network entity.

Conceptually it contains:

- static level geometry organized through ZenGin's BSP world representation;
- the global Vob tree/list and active Vob collections;
- world name/file metadata;
- collision/raycast state, waynet/zones, and search facilities.

The G2O wrapper exposes world metadata, the Vob list, name searches, Vob-tree merging, scene picking, and ray tracing. The client global `GameWorld` is the wrapped object. The separate `getWorld()` function returns the current world path string.

Loading or merging a Vob tree mutates the local engine world. It does not make its Vobs server-streamed.


## Vob hierarchy

`Vob` wraps `zCVob`, ZenGin's base spatial world object. It derives from `Object` (`zCObject`) and carries transform, visual, bounding/collision, world/tree membership, and parent/child state.

A useful simplified hierarchy is:

```text
Object (zCObject)
├─ World (oCWorld)
└─ Vob (zCVob)
   ├─ Npc (oCNpc)
   ├─ Item (oCItem)
   ├─ VisualFX (oCVisualFX)
   ├─ lights, triggers, movers, ...
   └─ Mob (oCMOB)
      └─ MobInter (oCMobInter)
         ├─ MobBed / MobFire / MobLadder / MobSwitch / MobWheel
         └─ MobLockable (oCMobLockable)
            ├─ MobDoor (oCMobDoor)
            └─ MobContainer
```

The Squirrel wrapper intentionally flattens some native intermediate inheritance (for example `Mob` is exposed as derived from `Vob`). Use the exposed Squirrel hierarchy for type operations, and the native hierarchy to understand engine behavior.

Terminology matters:

- `oCMOB` is the generic focusable world-object base with name/focus metadata.
- `oCMobInter` adds the interactive state-machine behavior.
- `oCMobLockable` adds locking/key/picklock semantics.
- `oCMobDoor` is a lockable interactive Mob.

Do not describe every `Mob` as interactive; that behavior starts at `MobInter`.


## Entity and engine-object lifetime

For a remote player/NPC on a client:

```text
create message -> G2O registry object -> onPlayerCreate
stream spawn   -> create/attach oCNpc Vob -> onPlayerSpawn
stream unspawn -> remove/release oCNpc Vob -> onPlayerUnspawn
destroy message -> remove registry object -> onPlayerDestroy
```

There can be multiple spawn/unspawn cycles between create and destroy. Cache data by ID, not by `oCNpc` pointer. Acquire the current native object only while needed and null-check it.

For a negative-ID local NPC, the same conceptual create/spawn/unspawn/destroy callbacks exist, but creation and range streaming are entirely client-local.

## Visual effects (PFX/VFX)

`VisualFX` wraps ZenGin `oCVisualFX`, itself a Vob. `VisualFX.createAndPlay` resolves a Daedalus visual-effect instance, creates the native effect, attaches it to an origin/optional target, starts playback, and returns the created wrapper; failure can yield null at the native binding boundary.

The verified overloads are client-only:

```text
VisualFX.createAndPlay(instance, originPosition, targetVob = null,
                       level = 1, damage = 0, damageType = 0,
                       isProjectile = false)

VisualFX.createAndPlay(instance, originVob, targetVob = null,
                       level = 1, damage = 0, damageType = 0,
                       isProjectile = false)
```

Example for a purely positional local effect:

```squirrel
local effect = VisualFX.createAndPlay("MY_EFFECT_INSTANCE", Vec3(x, y, z));
```

Use an instance defined by the loaded Gothic/Daedalus resources. The Vob overload expects native Vob userpointers, not multiplayer IDs. Resolve and validate current origin/target engine objects first.

Effects created on one client are not automatically visible on others. For shared presentation, make the server validate/announce the event (prefer a streamed message) and let each receiving client create its local effect. Do not use client-created VFX damage as authoritative combat damage; damage belongs in server game rules, while VFX is presentation unless a verified built-in flow says otherwise.

Release script references and related callbacks during world changes/hot reload. Verify the exact API snapshot before using additional `VisualFX` properties because it exposes many internal ZenGin fields with engine-specific lifetime constraints.


## 3D-to-2D projection

`Projector3d(x, y, z, distance)` tracks a world point and calls script callbacks with screen-space information. Internally, each client frame/update:

1. Requires an active camera, connected camera Vob, local player, and loaded world.
2. Culls when the point is farther than `distance` from the local streamer's position.
3. Transforms the world point by the active camera matrix into camera space.
4. Culls when camera-space `z <= 0` (behind the camera).
5. Calls ZenGin camera projection to produce pixel coordinates.
6. Toggles `onVisibilityChange` and invokes `onUpdate(screenPositionPx, depth)` subject to the projector's `fps` throttle.

The second callback value is implemented as camera-space Z depth, even though generated docs describe it as distance to the player. Do not use it as exact Euclidean distance.

Projection only checks range and camera-facing depth. It does not perform an occlusion raycast or guarantee the point is inside all viewport bounds. If a label must disappear behind walls, add an appropriate world ray test. Clamp/position UI using pixel methods because projector output is in pixels.

Destroy the projector or clear its callbacks when its owner unloads; projectors register themselves in a global native update list.


## Native UI: View, Label, and Sprite

`View` wraps a `zCView`-based screen item and is the common base for native G2O UI.

- New views are not automatically visible. Setting `visible = true` inserts the view into Gothic's global screen; setting false removes it.
- `top`, `bottom`, `stepTop`, and `stepBottom` change render-queue order; `zIndex` reports it.
- Visibility/rendering is client-local.
- Holding the Squirrel object owns the wrapper. Release it and hide it during teardown/reload.

`Label(x, y, text)` renders text using a Gothic font. It exposes text/font/color, position, letter spacing, scale/rotation/pivot, per-letter color, and vertices. One glyph is represented by two triangles (six vertices).

`Sprite` renders a texture. The one-argument constructor supports a custom shape populated with vertices; the `(x, y, width, height, texture)` constructor creates a fixed rectangle. It exposes position/size, UV, color/alpha, rotation/pivot, viewport, filtering, and vertices.

Most base position/size methods use Gothic virtual screen coordinates. `*Px` variants use physical pixels. G2O converts between them through the active `screen` view. Use one coordinate system consistently; use pixel methods with `Projector3d` output.

Native UI is appropriate for lightweight elements updated every frame, especially projected nameplates/markers. Prefer CEF for complex layout, forms, and document-style UI.

Construct owned labels, sprites, and other UI elements eagerly in the UI class constructor. Keep input handling in the owning state/service and presentation/layout in a separate UI class when those responsibilities grow. Do not create UI on its first use unless the user explicitly requests lazy loading.

Always handle client `onChangeResolution` for native UI. The included 0.3.9 API defines this event without parameters. In the feature-local `handlers.nut`, delegate to the existing UI owner's layout method:

```js
local function change_resolution_handler() {
    core.ui.resize()
}

addEventHandler("onChangeResolution", change_resolution_handler)
```

Here `core.ui` represents the already constructed project UI. Implement its `resize()` method to recompute the feature's positions, dimensions, alignment, and pixel/virtual coordinate conversions from the current resolution. Keep the same UI objects and current display state. Apply the equivalent rule to CEF as described in `references/cef.md`.


## Working safely with exposed engine classes

- Verify the class/member in the exact G2O API snapshot; source wrappers are broad and version-sensitive.
- Treat wrappers without public constructors as borrowed/current engine objects.
- Keep authoritative rules on the server; engine wrappers exist only on the client.
- Reacquire Vob/NPC pointers after streaming or world changes.
- Null-check factory/search results and validate object type before casting userpointers.
- Pair every local object/callback registration with unload/world-exit cleanup.
- Follow the general `setPlayer*`/`getPlayer*` naming guidance in `project-architecture.md` when choosing operations for players or NPCs.
