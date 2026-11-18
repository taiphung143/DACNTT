# Environment Validation — 2026-11-16

## Outcome

The `oracle_slm` environment is sufficient for the current Qwen3-0.6B
inference, analysis, plotting, lightweight depth-baseline, and unit-test code.
The complete test suite passes in this single environment.

## Validated system

- Operating system: Windows
- Python: 3.11.15
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU, 8 GB VRAM
- NVIDIA driver observed during validation: 610.88
- PyTorch: 2.9.1+cu128
- CUDA runtime reported by PyTorch: 12.8
- CUDA available to PyTorch: yes

## Validated Python packages

| Package | Version |
|---|---:|
| transformers | 5.15.1 |
| datasets | 4.8.5 |
| accelerate | 1.14.0 |
| matplotlib | 3.11.1 |
| scikit-learn | 1.6.1 |
| scipy | 1.17.1 |
| joblib | 1.6.0 |
| pytest | 8.4.2 |

`python -m pip check` reported no broken requirements.

## Test evidence

Command, run from the repository root:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
D:\miniconda\envs\oracle_slm\python.exe -m pytest -q
```

Result:

```text
180 passed, 1 warning in 10.64s
```

The warning originates from scikit-learn's use of SciPy L-BFGS-B options that
are scheduled for removal in SciPy 1.18. It does not indicate a failed test or
an observed change in the experiment results.

## Collection safeguard

`pytest.ini` restricts collection to `tests/`. This prevents temporary document
rendering dependencies under `tmp/` from being mistaken for project tests and
does not exclude any repository test module.

## Interpretation

This validation establishes software readiness, not scientific completeness.
The saved inference artifacts and analysis outputs still require an artifact
inventory and result-to-manuscript consistency audit before final submission.
