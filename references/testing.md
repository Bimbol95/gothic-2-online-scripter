# Validation and runtime testing

State exactly what was tested. Static validation, server startup, game-client validation, and multiplayer behavior are different evidence levels.

## Static checks

For every change:

1. Confirm every new file is referenced by the intended XML manifest when the chosen layout requires it.
2. Check dependency order against `references/project-architecture.md` and the detailed library references.
3. Look up every new G2O symbol in the exact target-version API snapshot.
4. Verify library classes, annotations, callback signatures, and send/request methods in the matching file under `references/libraries/`.
5. Search for references to renamed or removed symbols.
6. Confirm project settings are loaded from `settings.nut`, defined as `settings <- { ... }`, and use `snake_case` keys.
7. Confirm new event and packet entry points live in the relevant feature-local `handlers.nut`, and every `addEventHandler` immediately follows its named local handler function.
8. Search project code for direct `Packet()` construction or manual raw-packet serialization; replace it with BPackets.
9. Verify every Gothic/G2O runtime text file decodes strictly with the selected regional Windows code page, contains no UTF-8 BOM, and was not silently rewritten as UTF-8. Treat unrepresentable characters as errors rather than replacing them.
10. Check new and modified code for `snake_case` local variables, parameters, and class attributes; keep only class names in `PascalCase` and class methods in `lowerCamelCase`.
11. Review method names for redundant receiver context and clipped words: prefer `player_service.respawn` over `player_service.playerRespawn`, and `manager` over `mgr`. Preserve established acronyms in uppercase in class/method names.
12. Check eager construction and explicit lifecycle initialization; lazy loading is allowed only when requested by the user. Keep global managers and state machines under `core` and verify services do not mirror state owned elsewhere.
13. Check documented settings, named file-local values for non-obvious literals, appropriately scoped utilities for repeated helpers, and responsibility splits for large classes.
14. Confirm native UI and CEF have a feature-local `onChangeResolution` handler that updates the existing UI layout.
15. Run project-provided formatters, linters, builds, or tests only when their documented commands are present and preserve the required Windows encoding.

Static inspection does not prove that a Squirrel script loads in G2O.

## Server startup

Start the server only when the project or user provides the executable, working directory, configuration, and launch command, or when an available tool exposes an explicit server-start capability. Do not invent command-line arguments or configuration files.

When startup is available:

1. capture the full startup output;
2. identify script parse/load/runtime errors and their file locations;
3. fix only errors within the requested scope;
4. restart and confirm the relevant errors no longer appear;
5. stop the process cleanly if the provided workflow supports it.

Do not edit user-supplied `data.xml`, `mds.xml`, or `.vdf` files to make startup pass.

## Game and CEF validation

Launch or control the game client only when a runnable installation and an explicit automation/control path are available. Validate the smallest observable scenario that exercises the feature. For CEF, distinguish a successful web build from successful rendering and bridging inside the game.

For UI features, change the game resolution and check layout, bounds, alignment, and input targeting for native elements and CEF. Confirm resize handling updates existing elements without reconstructing the UI or losing its current state.

If interactive or visual behavior cannot be automated, provide a short manual test scenario with expected observations derived from the requirement. Label it as unexecuted.

## Report language

Use precise claims such as:

- "API and manifest checks passed";
- "the server started and produced no script errors during startup";
- "the client joined and the requested state transition was observed";
- "not runtime-tested because no server executable or game-control interface was provided."

Never collapse these into an unsupported claim that the feature "works."

