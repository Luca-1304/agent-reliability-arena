# Agent Contract Compiler v0.1.0 — Implementation Record

Date: 2026-07-22  
Tracking issue: #5  
Status: Locally complete and independently clarified; standalone publication pending repository creation

## Implemented product

The standalone implementation converts a bounded controlled-language source into:

- canonical contract JSON and domain-separated SHA-256 identity;
- proof-obligation graph and verification checklist;
- deterministic ambiguity, contradiction, unsupported and unverifiable diagnostics;
- intent-preservation report;
- weak-contract mutants and near-miss execution witnesses;
- dependency-free Completion Verifier and Evidence Ledger adapter outputs;
- transactional manifested output bundles;
- `contract-compile`, `contract-lint` and `contract-explain` commands;
- deterministic reference corpus and static employer-facing workbench.

The trusted core performs no model, network, shell, environment-expansion, file-inclusion or database operation.

## Final local source

Feature branch: `feat/contract-compiler-v0.1.0`  
Final commit: `2b47bc7fb16d2b9a6f8157371a340b8145dbb10f`

## Verification evidence

- complete local source suite: 46 tests;
- release verifier: 45 independently selected tests;
- deterministic corpus: 16 scenarios across all 7 compilation states;
- successful manifested bundles: 4;
- retained text files scanned: 122;
- clean installed-wheel suite: 45 tests;
- downloadable-archive source suite: 45 tests;
- wheel rebuilt from downloadable archive: 45 tests;
- all three installed commands exercised;
- package import confirmed from clean `site-packages`, not the source tree;
- `pip check`: no broken requirements;
- static viewer HTTP smoke: passed;
- exact corpus and workbench regeneration: passed.

## Release artifacts

ZIP:

- name: `agent_contract_compiler_v0.1.0.zip`;
- files: 124;
- bytes: 122102;
- SHA-256: `2c21b767c74f27346e9fc2a2b8e2d76fcea3f8063d36869348a54bebe2ca51aa`.

Wheel:

- name: `agent_contract_compiler-0.1.0-py3-none-any.whl`;
- bytes: 24534;
- SHA-256: `0b618d06eb599edefa934cbbb8d7c7ccba94fb9fbe76f5288c3323dc2b63b98c`.

## Claims boundary

The release demonstrates deterministic compilation, supported-language structural explicitness, supported contradiction detection, proof-plan completeness and deterministic mutation coverage. It does not prove recovery of unstated human intent, actor identity, observer truth, correct future execution, external-model reliability, customer adoption, legal compliance or income.

## Publication status

`Luca-1304/agent-contract-compiler` did not exist at final verification time. The exact verified release is retained locally and is ready for publication after a blank standalone repository is created. Python 3.10–3.13 workflow definitions and Pages deployment are included, but public GitHub CI and Pages results are not claimed before that publication occurs.