# CLI contracts

`cli-contracts.json` indexes actual argparse declarations and source-reviewed input/output, exit and side-effect contracts. The JSON inventory is authoritative for the current entry count. Helper modules without CLI arguments are excluded. Source review does not exhaustively test every error path; inspect structured result scope even after exit 0.

New record validator:

| Item | Contract |
|---|---|
| Input | UTF-8 JSON record; explicit optional kind, reference base and link checks |
| Output | JSON stdout; source and referenced files unchanged |
| Exit 0 | Structurally valid; inspect nested links status, which may be PARTIAL |
| Exit 1 | Invalid structure or inconsistent local references |
| Exit 2 | Input, unsupported version/type, dependency or usage error |
| Side effects | Reads files, including model bytes for requested hashes; no output files, engine calls or remote access |
| Limits | Declarations and evidence linkage only; no scientific acceptance or runtime compatibility certification |

Detailed format limits remain in [capabilities](capabilities.md), [local inspection](local-first.md), [local toolchain](local-toolchain.md) and [record contracts](record-contracts.md). The AST inventory test detects argument drift. Local behavior tests cover preparation, inspection, analysis, delivery and record handling; these do not establish any remote runtime or scientific acceptance.
