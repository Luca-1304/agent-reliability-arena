# Agent Contract Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build a deterministic controlled-language compiler that turns explicit human-readable requirements into canonical contracts, proof plans, diagnostics, mutation suites and verifier-ready adapters.

**Architecture:** A standard-library Python package parses a bounded line-oriented language into immutable IR, resolves aliases into content-derived semantic IDs, performs contradiction/reachability/proof analysis, emits canonical JSON transactionally, and exposes compile/lint/explain CLIs. Blocked inputs produce diagnostics only and never receive an authoritative contract identity.

**Tech Stack:** Python 3.10–3.13 standard library, unittest, dataclasses, argparse, hashlib, pathlib, HTML/CSS/vanilla JavaScript, setuptools.

## Global constraints

- No model, network, shell, environment expansion, file inclusion or database in the trusted core.
- Signed integers only; no floats or decimals.
- Logical POSIX-relative paths only.
- Source aliases are mandatory for referencable declarations but do not affect semantic identity.
- Contract IDs and semantic IDs use domain-separated SHA-256 over canonical JSON.
- Blocked compilation emits no authoritative contract, manifest or contract ID.
- Output publication is transactional and symlink-safe.
- Claims are limited to supported-language structure, consistency, proof-plan completeness and deterministic mutation coverage.

## Milestones

1. Package boundary, canonical JSON and deterministic diagnostics.
2. Lexer, parser, source spans and typed IR.
3. Content-derived IDs, symbol resolution and contract identity.
4. Ambiguity, contradiction, outcomes, conditions and proof graph.
5. Intent preservation, weak-contract mutants, near-miss witnesses and adapters.
6. Transactional bundles plus `contract-compile`, `contract-lint` and `contract-explain`.
7. Deterministic corpus and dependency-free employer workbench.
8. Documentation, threat model, source/wheel/archive verification and Python 3.10–3.13 CI.

Each milestone is red-green tested and committed independently. The release is complete only after source, clean-wheel and downloadable-archive clarification passes.