```bash
cd oracle_experiment
conda create -n oracle_slm python=3.11 pip -y
conda activate oracle_slm
python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
python -m adaptive_compute.cli.run_grid --num-problems 3 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --validate-only
python -m adaptive_compute.cli.run_grid --num-problems 3 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n3
python -m adaptive_compute.cli.run_grid --num-problems 3 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n3 --resume
python -m adaptive_compute.cli.analyze_grid --experiment qwen3_1_7b_gsm8k_n3
python -m adaptive_compute.cli.run_grid --num-problems 10 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n10
python -m adaptive_compute.cli.run_grid --num-problems 10 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n10 --resume
python -m adaptive_compute.cli.analyze_grid --experiment qwen3_1_7b_gsm8k_n10
python -m adaptive_compute.cli.run_grid --num-problems 30 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n30
python -m adaptive_compute.cli.run_grid --num-problems 30 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n30 --resume
python -m adaptive_compute.cli.analyze_grid --experiment qwen3_1_7b_gsm8k_n30
```
