# Thinking versus non-thinking: frozen Validation comparison

This is paired supplementary development evidence on the same Validation-20 items. It does not modify the frozen Test-100 claims.

| Dataset | k,L | Thinking | Non-thinking | Accuracy gap | Token saving | McNemar p | Holm p |
|---|---:|---:|---:|---:|---:|---:|---:|
| gsm8k | 1x2048 | 13/20 (65.0%), 986.15 tok | 1/20 (5.0%), 31.30 tok | -60.0 pp | 96.8% | 0.0004883 | 0.0004883 |
| gsm8k | 2x2048 | 14/20 (70.0%), 1969.70 tok | 1/20 (5.0%), 84.85 tok | -65.0 pp | 95.7% | 0.0002441 | 0.0004883 |
| gsm8k | 4x2048 | 15/20 (75.0%), 3593.85 tok | 1/20 (5.0%), 143.65 tok | -70.0 pp | 96.0% | 0.0001221 | 0.0003662 |
| math500 | 1x4096 | 11/20 (55.0%), 2388.70 tok | 8/20 (40.0%), 471.90 tok | -15.0 pp | 80.2% | 0.5078 | 1 |
| math500 | 2x4096 | 13/20 (65.0%), 4700.50 tok | 8/20 (40.0%), 923.40 tok | -25.0 pp | 80.4% | 0.125 | 0.375 |
| math500 | 4x4096 | 13/20 (65.0%), 8979.10 tok | 11/20 (55.0%), 1972.50 tok | -10.0 pp | 78.0% | 0.625 | 1 |

Holm adjustment is applied across k={1,2,4} separately within each dataset. Failure to reject is not evidence of equivalence.
