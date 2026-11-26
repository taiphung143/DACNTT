# GPU-free replay and audit

## Standalone package verification

From the package root, using Python 3.10 or newer (standard library only):

```powershell
python code/scripts/verify_round3_release.py --package .
```

This verifies every manifest checksum, packaged-source hashes, all six
breadth-stopping rows, seven headline policy summaries, and six force-answer
paired-table identities. It is a Level 1--2 verification and does not require
the full repository, GPU, model weights, or raw generation JSONL.

## Full-repository audit

Only from the complete private repository, in the documented `oracle_slm`
environment:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python scripts/final_scientific_audit.py
python scripts/round3_reviewer_audit.py
python -m pytest -q
```

The two full audit scripts read local CSV/JSON/JSONL artifacts and do not invoke
the model, but they are not standalone package commands because the package
intentionally omits required raw records. Their paper-facing outputs are
included under `audit_outputs/` for checksum and trace-level verification.

Do not treat the author-maintained freeze dates as independent registration
timestamps.
