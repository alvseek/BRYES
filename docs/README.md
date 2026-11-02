# docs/ — what lives where

One folder per kind of document. The [orientation map](orientation-map.md) indexes the
artifacts themselves; this file says where a new one belongs.

| Folder | Holds |
|---|---|
| [`architecture/`](architecture/) | How the system is built: [architecture-overview.md](architecture/architecture-overview.md) and the three structure maps (`modularity`, `modularity-target`, `loop-dispatch`). |
| [`flows/`](flows/) | How it behaves: [agent-loop-flow.md](flows/agent-loop-flow.md), the per-step sequence. |
| [`standards/`](standards/) | Rules the code follows: [python-conventions.md](standards/python-conventions.md), [quality-standard.md](standards/quality-standard.md). |
| [`tech-debts/`](tech-debts/) | What is known-broken, planned or unproven: [backlog.md](tech-debts/backlog.md). |
| [`interfaces/`](interfaces/) | Contracts between modules. Empty until one is written down. |
| [`modules/`](modules/) | Per-module documentation. Empty until a module needs more than its own README. |
| [`procedures/`](procedures/) | Step-by-step operator procedures, also served as skills. |
| [`adr/`](adr/) | Architecture Decision Records, append-only. |

[`context-index.md`](context-index.md) and [`orientation-map.md`](orientation-map.md) stay at
this level because the context and map loaders name those exact paths.

Moving a document means rewriting every live reference, and leaving `.agents/session/` alone
because it is the append-only record. The traps that make a docs move look finished while its
links are broken are written down in [.agents/knowledge/docs-layout.md](../.agents/knowledge/docs-layout.md).
