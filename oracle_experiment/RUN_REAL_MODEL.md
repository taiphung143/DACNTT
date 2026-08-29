```bash
cd oracle_experiment
conda create -n oracle_slm python=3.11 pip -y
conda activate oracle_slm
python -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
python run_grid.py --num-problems 3 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --validate-only
python run_grid.py --num-problems 3 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n3
python run_grid.py --num-problems 3 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n3 --resume
python analyze_grid.py --experiment qwen3_1_7b_gsm8k_n3
python run_grid.py --num-problems 10 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n10
python run_grid.py --num-problems 10 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n10 --resume
python analyze_grid.py --experiment qwen3_1_7b_gsm8k_n10
python run_grid.py --num-problems 30 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n30
python run_grid.py --num-problems 30 --k-values 1 2 4 --l-values 512 1024 2048 --seed 42 --experiment-id qwen3_1_7b_gsm8k_n30 --resume
python analyze_grid.py --experiment qwen3_1_7b_gsm8k_n30
```
