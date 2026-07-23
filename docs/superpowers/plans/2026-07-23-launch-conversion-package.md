# Launch and career conversion package implementation plan

## Goal

Publish an audience-specific career and distribution package that cites the locked public showcase without modifying its evidence bundle or widening its claims.

## Implementation sequence

1. Add tests for the exact launch-package manifest schema, canonical digest, public file allow-list and distribution states.
2. Add adversarial tests for credential-shaped content, local paths, private-evidence markers, provider identifiers, internal notes, enabled policies, unsupported claims and false external-publication states.
3. Confirm the tests fail because the launch-package verifier and files do not yet exist.
4. Implement `agent_reliability_arena.launch_package` with:
   - canonical manifest hashing;
   - safe relative-path and symlink checks;
   - exact file-digest verification;
   - leak and claim scanning;
   - distribution-register validation;
   - required authorship, AI-assistance and deterministic-fixture markers.
5. Add the audience-specific public documents and distribution register.
6. Capture the exact SHA-256 values of the listed public files through a temporary CI artifact, then remove the temporary workflow.
7. Add `scripts/verify_launch_package.py` and installed command `arena-verify-launch-package`.
8. Run the verifier from source, editable install and clean wheel in the permanent four-version CI matrix.
9. Add `LAUNCH.md` and a README link without changing the locked showcase manifest.
10. Update the pull-request record with red, repair and final-green evidence.
11. Merge only the unchanged final head and record the repository publication URL and limitations on issue #25.

## Verification target

Python 3.10, 3.11, 3.12 and 3.13 must all pass:

- complete source tests;
- base release verifier;
- disclosure verifier;
- repeated-experiment verifier;
- showcase verifier;
- launch-package verifier;
- installed command checks;
- wheel build;
- complete clean-wheel tests and all release verifiers;
- dependency validation.

## Safety boundary

No external account post, recruiter email, GitHub Pages setting change, provider request, credential use or paid action is part of this implementation. External actions remain explicitly marked `prepared` or `blocked` until verifiable URL/date evidence exists.
