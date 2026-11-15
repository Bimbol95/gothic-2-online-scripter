---
name: gothic-2-online-scripter
description: Create and extend Gothic 2 Online projects with source-verified Squirrel, client/server lifecycles, streaming and synchronization, native ZenGin classes, CEF, BStates, BPackets, and BNetReplicate. Use for G2O project layout, gameplay features, client World/Vob/Mob/VisualFX/UI work, NPC actions, configuration, versioned API verification, and validation without inventing undocumented behavior.
---

# Gothic 2 Online Scripter

Create or extend Gothic 2 Online projects using only evidence from the user's project and this skill's standalone references and authoritative documentation snapshots.

## Source discipline

Read `references/source-policy.md` before designing or editing code. Treat it as a hard constraint.

- Never invent G2O functions, classes, events, constants, XML elements, library APIs, paths, or runtime behavior.
- Determine the target G2O version from the user's requirement or project evidence. If it cannot be determined, ask before writing version-dependent code.
- Verify every G2O symbol against the matching local API snapshot with `scripts/g2o_api.py`. Check its exact signature, side, availability, and deprecation metadata.
- Treat the version segment in official documentation URLs as a replaceable path component. For a different target version, check the corresponding page before using its guidance; see `references/source-policy.md`.
- Verify BStates, BPackets, and BNetReplicate behavior against the detailed library references included with this skill.
- When sources do not establish a required fact, state the gap and request the missing information instead of filling it with a plausible guess.

## Required workflow

1. Establish whether the task creates a new project or extends an existing one.
2. Identify the target G2O version, exact regional Windows code page, required gameplay behavior, client/server ownership, UI needs, persistence needs, and networking needs.
3. For an existing project, inspect its manifests and nearby implementations first. Preserve unrelated structure, but apply `references/coding-style.md` to all new and modified project code.
4. For a new project, read `references/project-architecture.md` and use root `client`, `server`, and `shared` directories. Select the simple state-oriented or modular service-oriented internal structure described there according to the requested scope. Check whether the project root is itself a Git repository before acquiring libraries; see `references/libraries.md`.
5. Read only the task-relevant references:
   - For every script implementation, first read the script execution order, event timing, player lifecycle, and hot-reload rules in `references/runtime-lifecycle.md`
   - Streamer, player/NPC synchronization, NPC actions, packets, and script context: `references/streaming-and-synchronization.md`
   - Server XML, synchronization settings, and engine/network limits: `references/configuration-and-limits.md`
   - Client globals (`heroId`, `GameWorld`, `WorldTimer`), ZenGin objects, VisualFX, 3D projection, and native UI: `references/client-zengin.md`
   - Player/NPC `setPlayer*` and `getPlayer*` naming and script layout: `references/project-architecture.md`
   - Squirrel fork features: `references/squirrel-fork.md`
   - G2O API lookup: `references/g2o-api.md`
   - Libraries and networking choice: `references/libraries.md`, then the selected file under `references/libraries/`
   - CEF UI and bridge: `references/cef.md`
   - Project conventions: `references/coding-style.md`
6. Split the feature by authority:
   - put authoritative game rules and validation on the server;
   - put definitions needed by both sides in shared scripts;
   - put rendering, input, local presentation, and CEF integration on the client.
   Do not move a concrete API call to a side not allowed by its API metadata.
   A newly joined player remains unspawned until the server calls `spawnPlayer`; use this deliberately for login or character setup UI. `unspawnPlayer` removes the player from streamed visibility, while `setPlayerInvisible` hides a spawned player/NPC from others without preventing an invisible player from seeing them. Read `references/streaming-and-synchronization.md` before using these states.
7. Choose BNetReplicate, BPackets, and BStates according to `references/libraries.md`; do not add a library without a concrete role in the requested feature. For a new project, obtain each selected library missing from `libs/` from its verified upstream repository. Add it as a Git submodule when the project root is a Git repository; otherwise include it as ordinary project files.
8. Plan script load order and callback timing before implementation. Load definitions and shared schemas before consumers, register handlers after their dependencies, initialize runtime objects only when the required client/server state exists, and pair reloadable registrations with unload cleanup. Top-level code and reload callbacks run before `onInit`; initial client `onWorldEnter` also runs before `onInit`.
9. Implement the smallest complete change that satisfies the request. Treat `references/coding-style.md` as the required project-code standard.
10. Validate according to `references/testing.md`. Never report the game or server as tested unless it was actually launched and its output was inspected.

## Project boundaries

- Do not create or edit `data.xml`; the user supplies it.
- Do not create or edit `mds.xml`; the user supplies it.
- Do not create, edit, or package `.vdf` files; the user supplies them.
- Encode text files consumed directly by Gothic/G2O with the exact regional `Windows-12xx` code page. Never save those files as UTF-8 or UTF-8 with BOM. If the code page is not established by the user or project, ask instead of guessing.
- Store project configuration in `settings.nut` as `settings <- { ... }`; use `snake_case` for settings keys.
- Use `snake_case` for local variables, function parameters, and class attributes. Keep class methods `lowerCamelCase` and classes `PascalCase`.
- Prefer concise, contextual function and method names: do not repeat the receiver's responsibility (`player_service.respawn`, not `player_service.playerRespawn`). Never shorten words into unclear forms such as `mgr`; write `manager`. Preserve established acronyms in uppercase inside class and method names, for example `TDMService` and `findNPC`.
- Use shared `Color`, `Vec3`, `Vec2`, and `Vec2i` values instead of ad-hoc tables when those types represent the value.
- Keep feature event and packet entry points in a local `handlers.nut`, with each `addEventHandler` directly below its named handler function.
- Never instantiate or manually serialize G2O's raw `Packet` class in project code. Use BPackets, adding BNetReplicate for persistent synchronized state in larger projects.
- Do not confuse engine objects with network entities. Client-created Vobs, VisualFX, Labels, Sprites, Projector3d instances, and negative-ID local NPCs are local unless project code explicitly communicates their state.
- Prefer CEF for UI. Use native game UI only for performance-critical presentation such as projected billboards or labels updated every frame.
- Prefer BNetReplicate over BPackets for state that should remain synchronized and does not require very frequent or highly dynamic custom updates. Use BPackets for discrete messages, requests/responses, or cases not modeled as replicated state.

## API lookup

Resolve `<skill-dir>` to the directory containing this file, then use:

```text
python <skill-dir>/scripts/g2o_api.py available
python <skill-dir>/scripts/g2o_api.py verify
python <skill-dir>/scripts/g2o_api.py search <version> <query>
python <skill-dir>/scripts/g2o_api.py search <version> <symbol> --exact --json
```

Do not substitute another version just because it contains the desired symbol. See `references/g2o-api.md` for interpretation rules.

## Completion report

Report:

- which client, shared, server, UI, and manifest files changed;
- which G2O version was targeted;
- which exact Windows code page was used for Gothic/G2O text files;
- which authoritative API entries or standalone library references justified non-local APIs;
- which checks actually ran and their results;
- any behavior that still requires a real server, game client, CEF module, or user-supplied files to validate.

