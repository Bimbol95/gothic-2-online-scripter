# Versioned G2O API

Authoritative sources:

- versions: <https://gothic-online.gitlab.io/platform/docs/versions.json>
- API template: `https://gothic-online.gitlab.io/platform/docs/${VERSION}/api.json`

Local snapshots live in `references/g2o-api/`. `sources.json` records their origin and hashes.

The HTML manual at `https://docs.gothic-online.com/<version>/...` is also versioned. Links to a specific manual version in other references are examples: replace the version segment with the project's target version, open the page, and verify that the topic exists. Do not use a different version's page as evidence for exact symbol availability or signatures.

## Lookup procedure

1. Determine the project's target version from the user or project evidence.
2. Confirm that the version is available:

   ```text
   python <skill-dir>/scripts/g2o_api.py available
   python <skill-dir>/scripts/g2o_api.py verify
   ```

3. Search the exact version:

   ```text
   python <skill-dir>/scripts/g2o_api.py search 0.3.9 setPlayerWorld --exact --json
   ```

4. Read the matched record, including declaration, execution side, version information, deprecation status, parameters, return value, notes, and parent class where applicable.
5. Use the declaration exactly as documented. Do not transfer a symbol from a different version.

Use a broad search only to discover candidate names. Before writing code, repeat the lookup with `--exact` and inspect the JSON record. Class members can be qualified, for example `Camera.setPosition`, to avoid selecting a same-named method from another class.

## Side metadata

`client`, `server`, and `shared` project folders do not override API metadata. A shared definition may describe data used by both sides, but a concrete call must execute only on a side allowed by its API record.

## Refreshing snapshots

Run this only when current documentation is required or a requested version is missing:

```text
python <skill-dir>/scripts/sync_reference_docs.py
```

Refreshing is a source update, not a routine implementation step. Review changed versions and API records before changing code because documentation can evolve independently of the project.

