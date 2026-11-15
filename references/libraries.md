# Library selection

The detailed library references are self-contained:

- `references/libraries/bstates.md` — state stack, lifecycle, scoped event/packet/replication bindings, and load order.
- `references/libraries/bpackets.md` — typed messages, serializers, optional fields, binding signatures, and request/response flows.
- `references/libraries/bnet-replicate.md` — replicated objects/arrays, interest, events, client requests, and server validation.

Read only the files for libraries the feature actually needs.

These references document the interfaces and composition rules; they are not the library implementation. Before adding an import, confirm that the corresponding library files exist in the project. Do not fabricate missing library implementation files from the interface documentation.

## Acquiring libraries for a new project

1. Check whether the **project root itself** is a Git repository: compare the resolved project root with `git -C <project-root> rev-parse --show-toplevel`. Being inside a parent repository does not make the new project a repository for this decision.
2. Check which selected libraries are already present under `libs/`. For a Git project, also inspect `.gitmodules` for libraries that are declared but not initialized. Reuse existing libraries; initialize missing submodule working trees with `git submodule update --init --recursive` instead of adding duplicates.
3. Obtain each missing, selected library from its primary upstream repository. Existing G2O project manifests identify these upstreams: BStates at `https://gitlab.com/bcore1/bstates.git`, BPackets at `https://gitlab.com/bcore1/bpackets.git`, and BNetReplicate (repository and directory name `breplicate`) at `https://gitlab.com/bcore1/breplicate.git`. Verify that the upstream URL is currently reachable and contains the expected library before using it; if an upstream has moved, find the maintained primary repository rather than guessing a replacement.
4. If the project root is a Git repository, add each absent library as a submodule under `libs/` (`libs/bstates`, `libs/bpackets`, or `libs/breplicate`) and check that `.gitmodules` records the correct upstream. If the project root is not a Git repository, include the upstream library as ordinary files under the same `libs/` path; do not create a nested Git repository or initialize Git for the project without a project requirement.
5. Add manifest imports only after the library files are available. Keep the library load order described in `references/project-architecture.md`.

Never use G2O's raw `Packet` class directly in project code. BPackets is the required abstraction for simple communication. For a larger project, use BNetReplicate for persistent synchronized models and retain BPackets for discrete actions and request/response flows.

## Decision table

| Need | Use |
|---|---|
| Gameplay phase with enter/exit lifecycle and temporary handlers | BStates |
| One-off command, notification, or typed event | BPackets message; never raw `Packet` |
| One-shot correlated request and response | BPackets request |
| Persistent server-owned model observed by clients | BNetReplicate |
| Model visible only to selected players | BNetReplicate interest management |
| Client proposes a change to replicated state | `BNetMode.SHARED` plus server validation |

Prefer BNetReplicate over manual BPackets synchronization for state that should remain synchronized and does not require very frequent or highly dynamic custom updates. Use BPackets for discrete communication or custom update streams that should not be modeled as persistent replicated state.

Libraries may be combined when each has a distinct role. A typical combination uses BNetReplicate for lobby state, BPackets for actions and correlated responses, and BStates for client views or gameplay phases whose handlers should be active only while that phase is current.
