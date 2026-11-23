$ErrorActionPreference = "Stop"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repositoryRoot

$env:PYTHONUNBUFFERED = "1"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
$env:MPLBACKEND = "Agg"
$env:OPENBLAS_NUM_THREADS = "1"
$env:OMP_NUM_THREADS = "1"

$pythonExecutable = "D:\miniconda\envs\oracle_slm\python.exe"
$experimentId = "qwen3_0_6b_math500_test_n100_forceanswer_v2"
$manifestPath = Join-Path $repositoryRoot "results\$experimentId\experiment_manifest.json"

$runArguments = @(
    "-m", "adaptive_compute.cli.run_grid",
    "--dataset-name", "math500",
    "--num-problems", "100",
    "--phase2-split-manifest", "data/splits/math500_split_v1.json",
    "--phase2-partition", "test",
    "--problem-snapshot", "results/qwen3_0_6b_math500_test_n100_contract_v1/raw_samples.jsonl",
    "--k-values", "1", "2", "4",
    "--l-values", "1024",
    "--decoding-strategy", "force_answer",
    "--answer-reserve-tokens", "256",
    "--experiment-id", $experimentId,
    "--generation-cache", "results/generation_cache.jsonl"
)

if (Test-Path -LiteralPath $manifestPath) {
    $runArguments += "--resume"
}

& $pythonExecutable @runArguments
exit $LASTEXITCODE
