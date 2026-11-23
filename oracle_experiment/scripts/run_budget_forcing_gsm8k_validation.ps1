$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repositoryRoot

$env:PYTHONUNBUFFERED = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:MPLBACKEND = "Agg"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"

$pythonExecutable = "D:\miniconda\envs\oracle_slm\python.exe"
$experimentId = "qwen3_0_6b_gsm8k_validation_n20_forceanswer_v2"
$manifestPath = Join-Path $repositoryRoot "results\$experimentId\experiment_manifest.json"

$runArguments = @(
    "-m", "adaptive_compute.cli.run_grid",
    "--dataset-name", "gsm8k",
    "--num-problems", "20",
    "--phase2-split-manifest", "data/splits/phase2_gsm8k_split_v1.json",
    "--phase2-partition", "validation",
    "--problem-snapshot", "results/qwen3_0_6b_gsm8k_validation_n20_contract_v3/raw_samples.jsonl",
    "--gsm8k-contract-version", "v4",
    "--k-values", "1", "2", "4",
    "--l-values", "512", "1024",
    "--decoding-strategy", "force_answer",
    "--answer-reserve-tokens", "128",
    "--experiment-id", $experimentId,
    "--generation-cache", "results/generation_cache.jsonl"
)

if (Test-Path -LiteralPath $manifestPath) {
    $runArguments += "--resume"
}

& $pythonExecutable @runArguments
exit $LASTEXITCODE
