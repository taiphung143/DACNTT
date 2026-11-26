# Zenodo release guide (manual authorization required)

1. Confirm that the intended source revision contains every paper-relevant
   change. The verified cleanup base HEAD is
   `98127d80d7589ee6a8c54a0f3fee3f6b70e300e7`. The package records that base,
   whether uncommitted modifications were present, and exact packaged-source
   hashes in `SOURCE_PROVENANCE.json`. Do not label it immutable until a real
   release commit/tag exists.
2. Review dataset licenses and the permissibility of distributing raw model
   outputs. Remove any artifact that cannot be redistributed.
3. Search the package for credentials and personal/sensitive data. Confirm that
   no cache, model weight, environment, or build directory is present.
4. Rebuild `MANIFEST_SHA256.csv`, recompute every digest independently, and
   archive the package without changing file contents afterward.
5. Create a Zenodo deposition manually, upload the reviewed archive, add the
   authors/title/license/version metadata, and reserve or publish the DOI only
   after all authors approve.
6. Download the deposited archive in a clean session, verify its checksum and
   replay instructions, then record the real DOI and immutable source commit.
7. Only after the DOI and unauthenticated repository access are verified should
   the manuscript claim public availability.

No upload, repository-visibility change, release, or DOI creation is performed
by this guide.
