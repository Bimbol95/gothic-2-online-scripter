# Source policy

This skill must remain evidence-bound. A convincing but undocumented implementation is a failure.

## Precedence

Use sources in this order:

1. The user's current request and the project being edited.
2. The local API snapshot for the project's exact G2O version.
3. The detailed BStates, BPackets, and BNetReplicate references included with this skill.
4. The CEF and modified-Squirrel references included with this skill.
5. The G2O runtime, synchronization, configuration, and ZenGin behavior references included with this skill.
6. The standalone project architecture and coding-style references included with this skill.

If two sources at the same level conflict, do not silently choose one. Describe the conflict and ask for direction when it affects the result.

## What the references establish

The reference examples establish concrete composition and usage patterns. They do not establish that every snippet is correct for every G2O version or that every optional layer is mandatory.

Before using a G2O symbol from any example, verify it in the target version's API snapshot. Before using a library symbol, verify it in the matching detailed library reference. Preserve a local convention when extending a project unless it conflicts with verified API or library behavior.

The runtime references establish ownership, order, and internal flow for G2O scripting across the 0.3 line. They are not substitutes for exact versioned API lookup. If a project's build differs in a behavior that affects correctness, verify that behavior against the target runtime. Where the published manual disagrees with the analyzed implementation, the references record the discrepancy; do not silently copy a documented default that differs from the target runtime.

## Unknowns

Do not infer missing details from names or from experience with another multiplayer framework. In particular, do not invent:

- G2O API names or signatures;
- client/server availability;
- events or callback parameters;
- XML configuration elements;
- the regional Windows code page;
- module installation or launch commands;
- files expected from the user;
- runtime success from static inspection.

When a missing fact is required to continue, identify exactly what evidence is missing. When it is optional, implement only the evidenced portion and record the limitation.

## External documentation

The URLs recorded in `references/g2o-api/sources.json` are the authoritative inputs for the local API and CEF snapshots. Local snapshots make lookups deterministic, but may become stale. Refresh them with `scripts/sync_reference_docs.py` only when the user asks for current documentation or the target version is absent. Review snapshot changes before allowing them to alter generated code.

### Versioned manual pages

An official manual URL such as `https://docs.gothic-online.com/0.3.9/multiplayer/hot-reload/` is an example for a particular version, not a limit on which versions this skill can use. When the project targets another version, replace only the version path segment and open the resulting page, for example `https://docs.gothic-online.com/0.3.8/multiplayer/hot-reload/`. This pattern has been confirmed for those two versions, but a given page or version may be absent.

1. Determine the target version from the user or project.
2. For a relevant linked manual topic, form `https://docs.gothic-online.com/<target-version>/<same-topic-path>/` and check that the page actually exists and describes the intended topic. If it does not, use the site's version navigation or report that the exact page is unavailable.
3. Read that version's content. Do not assume text, examples, defaults, or feature availability are identical across versions.
4. For exact Squirrel symbols and signatures, use the matching local API snapshot and `scripts/g2o_api.py`; a manual page is explanatory, not a substitute for API metadata. Do not silently substitute a nearby version when the requested version is unavailable.

The versioned URL can be changed for configuration, lifecycle topics, NPC action model, limits, and script context alike. Keep the topic path only when the target version actually serves that page.

