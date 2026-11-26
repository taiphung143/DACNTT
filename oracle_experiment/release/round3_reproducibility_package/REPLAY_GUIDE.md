# GPU-free replay and audit

From the repository root, in the documented `oracle_slm` environment:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python scripts/final_scientific_audit.py
python scripts/round3_reviewer_audit.py
python -m pytest -q
```

The two audit scripts read existing CSV/JSON/JSONL artifacts and do not invoke
the model. Their paper-facing outputs are written to `paper/audit_outputs/` in
the full repository. In this package, expected outputs are included under
`audit_outputs/`.

To verify the package itself, recompute SHA-256 for every file listed in
`MANIFEST_SHA256.csv` and compare the digest. Do not treat the author-maintained
freeze dates as independent registration timestamps.
