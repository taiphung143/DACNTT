# Public release readiness

Date: 2026-11-26  
Base HEAD: `98127d80d7589ee6a8c54a0f3fee3f6b70e300e7`  
State: local, uncommitted release candidate; no tag or DOI

## Verified package scope

The round-3 package contains 113 files total: 112 payload files described by
`MANIFEST_SHA256.csv` plus the manifest itself. Its independent standard-library
verifier passed both in place and in a clean-room directory containing only the
package:

- 112 file sizes/SHA-256 digests;
- 58 packaged-source hashes;
- 6 breadth-stopping trace rows;
- 7 headline primary summaries;
- 6 force-answer paired-table identities.

All 58 packaged code files matched the canonical source at build time and on an
independent post-build comparison. `SOURCE_PROVENANCE.json` records base HEAD,
dirty-worktree status, the source snapshot digest, and per-file hashes.

## Reproducibility level

- Level 1 (checksum verification): **PASS**.
- Level 2 (CSV/trace-based result verification): **PASS**.
- Level 3 (full raw-generation replay): **NOT PROVIDED**.

Primary raw JSONL, model weights/caches, benchmark text beyond allowed
manifests, and some author freeze records are intentionally absent. Therefore
the package must not be described as “fully reproducible.”

## Builder safety

`scripts/build_round3_release_package.py` now builds an explicit allowlist into
a new staging directory, creates and verifies the complete manifest, then swaps
the verified candidate into place. An old package is not removed before the
replacement passes verification. Stale files cannot survive the rebuild.

## Security and publication decision

Current candidate scans found no strong token/private-key signature and no
generic credential-assignment candidate. The existing Git history is not safe
for direct public conversion because it contains large generated dependencies,
sample private-key material, reviewer material, and oversized archives.

Recommended release path:

1. Keep `DACNTT` private.
2. Review the clean allowlist described in `docs/PUBLIC_RELEASE_SECURITY_AUDIT.md`.
3. Create a new public repository from that snapshot only after all authors
   approve licenses, privacy, paper policy, and included artifacts.
4. Run `python code/scripts/verify_round3_release.py --package .` in a fresh
   clone/archive.
5. Create a real release commit/tag; rebuild provenance with the final commit.
6. Upload to Zenodo only after manual approval, then verify the downloaded
   archive and update the paper with the real URL/DOI.

## Authorization still required

Author approval is required to create/commit/push a clean public repository,
change GitHub visibility, publish a release/tag, upload Zenodo, distribute raw
generations, or rewrite existing Git history. None of these actions was taken.
