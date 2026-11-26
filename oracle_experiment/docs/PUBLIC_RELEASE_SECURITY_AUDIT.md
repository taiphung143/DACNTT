# Public release security audit

Date: 2026-11-26  
Base HEAD: `98127d80d7589ee6a8c54a0f3fee3f6b70e300e7`

## Scans performed

- Strong token/private-key signature scan of the cleanup index: 0 matching paths.
- Generic credential-assignment scan of the cleanup index: 0 candidate paths.
- The same two scans over the round-3 release package: 0 candidate paths.
- All nine reachable commits were scanned for strong signatures and sensitive
  filenames without printing any matched secret content.
- Git history object inventory: 11,844 unique blobs, 1,269,544,300 bytes.

These regular-expression scans reduce risk but do not replace a dedicated
credential scanner or a human license/privacy review.

## History exposure

The existing history is not suitable for direct publication:

- 22 historical paths matched strong secret/private-key signatures. Most are
  vendored/minified dependency files and may be false positives, but the history
  also contains two `live-server/test/conf/server.key` files.
- `oracle_experiment/download.txt` contains reviewer material and student
  identifiers; redistribution permission is not established.
- The history contains generated dependencies and very large binaries, including
  a 461,216,956-byte `oracle_experiment.zip`, a 50,167,808-byte Tectonic binary,
  model/runtime DLLs, WASM and Node package trees.
- Adding `.gitignore` and staging `git rm --cached` does not remove any of these
  objects from prior commits.

No claim is made that a matched historical key is live. No plaintext secret is
reproduced in this report.

## Sensitive or restricted material

- Reviewer reports and private review correspondence: keep private.
- Primary raw model generations: keep local pending benchmark/output licensing
  and privacy review.
- Freeze-date records: useful provenance, but not independent preregistration.
- Historical thesis reports, slides, student records, and reference PDFs: require
  author-by-author copyright/privacy review before any public snapshot.

## Public options

| Criterion | A. Make current `DACNTT` public | B. New clean allowlisted repository |
|---|---|---|
| History exposure | High | Low |
| Repository size | Very high history | Small snapshot |
| Review clarity | Poor | Strong |
| Reproducibility | Possible but noisy | Curated Level 1–2 package plus source |
| Maintenance | Legacy baggage | Explicit release boundary |
| DOI stability | History remains oversized | Clean tag/archive is straightforward |

Recommendation: **Option B**. Keep `DACNTT` private and create a new repository
from a reviewed allowlist/clean snapshot. Do not copy `.git`, `.artifact_work`,
`tmp`, `.chart-data-*`, local `results/`, `download.txt`, thesis reports, or
unreviewed third-party PDFs. Include canonical source/tests, frozen split and
policy manifests, paper source/figures/final PDF as permitted, and the verified
round-3 reproducibility package.

No history rewrite, repository creation, visibility change, push, release, or
Zenodo upload was performed.
