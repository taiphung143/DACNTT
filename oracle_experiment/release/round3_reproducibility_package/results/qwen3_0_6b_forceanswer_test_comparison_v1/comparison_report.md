# Standard versus force-answer: frozen Test comparison

This is paired supplementary evidence on the same Test items, sample seeds, prompts, and parser. The primary thesis results remain unchanged.

| Dataset | k,L | Standard | Force-answer | Accuracy gap | Token saving | Parse fail S/F | Trunc. S/F | McNemar p | Holm p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gsm8k | 1x512 | 42/100 (42.0%), 454.31 tok | 52/100 (52.0%), 380.72 tok | +10.0 pp | +16.2% | 54.0%/9.0% | 55.0%/1.0% | 0.006348 | 0.01904 |
| gsm8k | 2x512 | 47/100 (47.0%), 912.46 tok | 54/100 (54.0%), 762.45 tok | +7.0 pp | +16.4% | 59.0%/10.5% | 57.5%/1.5% | 0.09229 | 0.1846 |
| gsm8k | 4x512 | 53/100 (53.0%), 1811.51 tok | 56/100 (56.0%), 1519.05 tok | +3.0 pp | +16.1% | 58.2%/10.5% | 56.0%/1.5% | 0.5488 | 0.5488 |
| math500 | 1x1024 | 13/100 (13.0%), 984.67 tok | 42/100 (42.0%), 785.84 tok | +29.0 pp | +20.2% | 86.0%/1.0% | 86.0%/6.0% | 3.725e-09 | 7.451e-09 |
| math500 | 2x1024 | 15/100 (15.0%), 1968.96 tok | 43/100 (43.0%), 1570.78 tok | +28.0 pp | +20.2% | 86.5%/1.5% | 86.5%/6.5% | 7.451e-09 | 7.451e-09 |
| math500 | 4x1024 | 17/100 (17.0%), 3933.58 tok | 49/100 (49.0%), 3150.40 tok | +32.0 pp | +19.9% | 85.8%/1.5% | 85.8%/7.2% | 4.657e-10 | 1.397e-09 |

Holm adjustment is applied across all registered (k,L) profiles within the dataset. Failure to reject is not evidence of equivalence or non-inferiority.
