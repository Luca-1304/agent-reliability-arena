# Reliability Gate v2 — CI Dependency Closure Decision

**Status:** Accepted  
**Date:** 2026-08-06  
**Supersedes:** the three-package bootstrap described in Task 3 of the initial implementation plan.

## Evidence

The red-phase runner log showed that `wheel==0.47.0` declares `packaging>=24.0`. A lock containing only pip, setuptools, and wheel is therefore not a complete dependency closure and cannot honestly be installed with pip's `--require-hashes` mode without either resolving an unhashed transitive package or suppressing dependency resolution.

## Decision

The CI bootstrap is a four-package closed set:

| Package | Version | Allowed wheel SHA-256 |
|---|---:|---|
| packaging | 26.3 | `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c` |
| pip | 26.2.1 | `71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e` |
| setuptools | 83.0.0 | `29b23c360f22f414dc7336bb39178cc7bcbf6021ed2733cde173f09dba19abb3` |
| wheel | 0.47.0 | `212281cab4dff978f6cedd499cd893e1f620791ca6ff7107cf270781e587eced` |

`requirements/ci-tools.txt` contains exactly those four entries. Repository tests require the package names, exact versions, one SHA-256 hash per permitted wheel, and no unlisted transitive dependency.

## Rejected alternatives

1. **Install wheel with `--no-deps`.** Rejected because it would conceal the declared dependency relationship and make the bootstrap contract misleading.
2. **Allow pip to resolve packaging without a hash.** Rejected because it defeats `--require-hashes` and permits an unreviewed artifact into the CI trust boundary.
3. **Remove wheel from the toolchain.** Technically possible with modern setuptools, but rejected for this release because the repository explicitly verifies wheel construction and keeping the build frontend named and locked makes the evidence easier to audit.
4. **Use broad version ranges.** Rejected because identical source revisions could receive different build tooling on different dates.

## Review rule

Any version or digest change must be made through a pull request that:

- verifies the release metadata from the official package index;
- updates this decision record and `requirements/ci-tools.txt` together;
- proves the four-version Python matrix remains green;
- proves editable/wheel parity and cross-pass determinism remain green;
- does not combine the toolchain change with product behaviour changes.
