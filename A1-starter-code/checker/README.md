# Part B Checker

## Evaluate

To evaluate your Part B solver (`part_b.py`), run from the project root (`A1-starter-code`):

```bash
python checker/check_b.py evaluate
```
(or `python checker/check_a.py evaluate`)

## Key Features

- **Part B Execution**: Automatically executes `part_b.py` on test cases.
- **10-Minute Timeout**: Each test case is granted a 10-minute (600 seconds) timeout limit.
- **Fairness Score Reporting**: For valid roster solutions, the checker displays the per-test Fairness Score (Cost $C$) along with integer objective $9 \times C$.
- **Fairness Statistics**: After evaluation, summary statistics (Average, Minimum, Maximum fairness scores) across test cases are displayed.

## Overwrite Model Solutions

To regenerate model solutions using `part_b.py`:

```bash
python checker/check_b.py overwrite
```