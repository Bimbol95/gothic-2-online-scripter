# Gothic 2 Online Scripter

A reusable agent skill for creating and extending Gothic 2 Online (G2O) projects with Squirrel scripts and CEF interfaces. It provides an evidence-based workflow, versioned API snapshots, standalone technical references, and API lookup tools.

## Features

- Client, shared, and server architecture for new projects and existing gameplay features.
- Exact-version G2O API verification, including signatures, execution side, and availability.
- References for the modified Squirrel language, runtime lifecycle, streaming, synchronization, configuration, and native ZenGin objects.
- CEF interfaces and Squirrel integration.
- BStates, BPackets, and BNetReplicate integration guidance.
- Coding, encoding, script load-order, and validation rules.

The bundled API snapshots cover G2O **0.3.6, 0.3.7, 0.3.8, and 0.3.9**. The agent must use the project's exact version rather than substitute a nearby version.

## Installation in Codex

Copy or clone this repository into one of these directories, keeping `SKILL.md`, `references/`, and `scripts/` together:

- Project scope: `<project>/.agents/skills/gothic-2-online-scripter/`
- User scope: `~/.agents/skills/gothic-2-online-scripter/`

On Windows, the user-scoped location is typically `%USERPROFILE%\.agents\skills\gothic-2-online-scripter\`.

The resulting structure should look like this:

```text
gothic-2-online-scripter/
├── SKILL.md
├── README.md
├── LICENSE
├── references/
└── scripts/
```

Codex detects installed skills automatically. If it does not appear, restart Codex. See the official [skill documentation](https://learn.chatgpt.com/docs/build-skills) for discovery and configuration details.

The skill is self-contained: the original gamemode and library source repositories used to prepare its references are not required to use it. Actual game projects still need their selected runtime libraries and assets.

## Usage

Open the target project in Codex and explicitly mention the skill in your request:

```text
$gothic-2-online-scripter

Extend this existing G2O 0.3.9 server with a team-selection system.
Use Windows-1250 for Gothic/G2O runtime text files.
Keep team assignment and validation on the server, synchronize team state
with BNetReplicate, and provide a CEF team-selection panel.
Inspect the existing manifests and implementations before editing.
```

For a new project:

```text
$gothic-2-online-scripter

Create a minimal G2O 0.3.9 deathmatch project with client, shared, and
server directories. Use Windows-1250 for Gothic/G2O runtime text files.
Include respawning and a CEF scoreboard. Verify the API calls and script
load order, and report what still needs testing in the game.
```

Provide the target G2O version, the exact regional Windows code page, desired gameplay, UI requirements, and any persistence or networking requirements. The example code page is a project choice, not a universal default.

## Boundaries and validation

The skill requires documented APIs and checks every G2O symbol against the matching local snapshot. It preserves client/server authority boundaries and reports missing evidence rather than inventing behavior.

You supply `data.xml`, `mds.xml`, and `.vdf` assets; the skill does not create or edit them. It prefers CEF for UI and uses native presentation when performance requires it.

Static checks do not establish runtime success. Server, game-client, CEF, and multiplayer validation require a runnable environment and must be reported separately.

## API tools

The scripts use Python 3.10 or newer and the standard library. No pip packages are required. Run these commands from this repository's root:

```sh
python scripts/g2o_api.py available
python scripts/g2o_api.py verify
python scripts/g2o_api.py search 0.3.9 setPlayerWorld --exact --json
```

Run the API tool's unit tests with:

```sh
python -m unittest discover -s scripts -p "test_*.py"
```

To refresh the bundled API snapshots and CEF search index from their authoritative sources:

```sh
python scripts/sync_reference_docs.py
```

Refreshing requires network access and modifies the bundled reference data. Review the resulting changes before committing them. Refresh only when current documentation is needed or a required version is missing. Source URLs and hashes are recorded in `references/g2o-api/sources.json`.

## Reference sources

- [Gothic Online API version index](https://gothic-online.gitlab.io/platform/docs/versions.json)
- [Gothic Online versioned manual](https://docs.gothic-online.com/0.3.9/)
- [CEF module documentation](https://gothic-online.gitlab.io/modules/cef/)
- [Modified Squirrel language](https://gothic-online.gitlab.io/dependencies/squirrel/differences/index.html)
- Included BStates, BPackets, and BNetReplicate references under `references/libraries/`.

Use manual pages for the target project's version; the linked manual is an example for 0.3.9.

## License

Original material in this repository is licensed under the **GNU General Public License, version 3.0** (`GPL-3.0-only`). See [LICENSE](LICENSE) for the full text.

Bundled third-party documentation, API snapshots, and any upstream excerpts remain subject to their respective copyright notices and license terms; this license does not replace those terms.
