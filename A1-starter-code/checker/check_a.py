import contextlib
import csv
import io
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECKER = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def read_json(path):
    with path.open(encoding='utf-8') as file:
        return json.load(file)


def suites():
    test_root = CHECKER / 'test-cases'
    if not test_root.is_dir():
        return []
    return sorted(path for path in test_root.iterdir() if path.is_dir() and any(path.glob('*.csv')))


def expected_type(input_path):
    model_path = CHECKER / 'model-solutions' / input_path.parent.name / f'{input_path.stem}.json'
    try:
        return 'empty' if read_json(model_path) == {} else 'valid'
    except (OSError, json.JSONDecodeError):
        return 'valid'


def verify_solution(verifier, instance, solution):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return verifier.verify_solution(instance, solution)
    except (KeyError, TypeError, ValueError):
        return False


def is_correct(verifier, instance, input_path, solution):
    if expected_type(input_path) == 'empty':
        return solution == {}
    return verify_solution(verifier, instance, solution)


def timeout_for(input_path):
    try:
        with input_path.open(newline='', encoding='utf-8') as file:
            timeout = float(next(csv.DictReader(file))['T'])
        return max(600.0, timeout)
    except (KeyError, OSError, StopIteration, ValueError):
        return 600.0


def solve_to_temp(input_path, directory, timeout=None):
    directory.mkdir(parents=True, exist_ok=True)
    temporary_path = directory / f'.{input_path.stem}.{uuid.uuid4().hex}.tmp'
    command = [sys.executable, str(ROOT / 'part_b.py'), str(input_path), str(temporary_path)]
    timeout = timeout or timeout_for(input_path)
    solver_output = ""
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        solver_output = (completed.stdout or "") + (completed.stderr or "")
    except subprocess.TimeoutExpired as e:
        temporary_path.unlink(missing_ok=True)
        timeout_out = (e.stdout or b"").decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else (e.stdout or "")
        timeout_err = (e.stderr or b"").decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else (e.stderr or "")
        return None, f'timeout after {timeout:g}s', timeout_out + timeout_err
    if completed.returncode != 0 or not temporary_path.exists():
        temporary_path.unlink(missing_ok=True)
        return None, f'solver failed (exit code {completed.returncode})', solver_output
    try:
        solution = read_json(temporary_path)
    except (OSError, json.JSONDecodeError):
        temporary_path.unlink(missing_ok=True)
        return None, 'invalid JSON', solver_output
    return (temporary_path, solution), None, solver_output


def overwrite_models():
    import verifier

    started_at = time.time()
    updated = 0
    failures = 0
    attempted = 0
    for suite in suites():
        model_dir = CHECKER / 'model-solutions' / suite.name
        for input_path in sorted(suite.glob('*.csv')):
            attempted += 1
            result, error, solver_output = solve_to_temp(input_path, model_dir, timeout=600.0)
            if solver_output and solver_output.strip():
                print(f"--- Output for {suite.name}/{input_path.name} ---")
                print(solver_output.strip())
            if error:
                failures += 1
                print(f'FAIL {suite.name}/{input_path.name}: {error}')
                print(f'Progress: {updated} out of {attempted} correct so far in {time.time() - started_at:.2f} seconds', flush=True)
                continue
            temporary_path, solution = result
            instance = verifier.read_input(str(input_path))
            if not is_correct(verifier, instance, input_path, solution):
                temporary_path.unlink(missing_ok=True)
                failures += 1
                print(f'FAIL {suite.name}/{input_path.name}: solver output is not correct')
                print(f'Progress: {updated} out of {attempted} correct so far in {time.time() - started_at:.2f} seconds', flush=True)
                continue
            temporary_path.replace(model_dir / f'{input_path.stem}.json')
            updated += 1
            print(f'Progress: {updated} out of {attempted} correct so far in {time.time() - started_at:.2f} seconds', flush=True)
        print(f'{suite.name}: overwritten')
    print(f'Model solutions updated: {updated}; failures: {failures}')
    return failures == 0


def evaluate():
    import verifier
    started_at = time.time()
    correct = 0
    attempted = 0
    all_scores = []
    
    for suite in suites():
        suite_correct = 0
        suite_total = 0
        suite_scores = []
        solution_dir = CHECKER / 'solutions' / suite.name
        for input_path in sorted(suite.glob('*.csv')):
            suite_total += 1
            attempted += 1
            result, error, solver_output = solve_to_temp(input_path, solution_dir)
            if solver_output and solver_output.strip():
                print(f"--- Output for {suite.name}/{input_path.name} ---")
                print(solver_output.strip())
            if error:
                print(f'FAIL {suite.name}/{input_path.name}: {error}')
                print(f'Progress: {correct} out of {attempted} correct so far in {time.time() - started_at:.2f} seconds', flush=True)
                continue
            temporary_path, candidate = result
            temporary_path.replace(solution_dir / f'{input_path.stem}.json')
            instance = verifier.read_input(str(input_path))
            candidate_correct = is_correct(verifier, instance, input_path, candidate)
            if candidate_correct:
                correct += 1
                suite_correct += 1
                if candidate != {}:
                    obj = verifier.calculate_objective(instance, candidate)
                    fairness_score = obj / instance['N']
                    suite_scores.append(fairness_score)
                    all_scores.append(fairness_score)
                    print(f'PASS {suite.name}/{input_path.name}: valid | Fairness Score (Cost): {fairness_score:.4f} (Obj: {obj})')
                else:
                    print(f'PASS {suite.name}/{input_path.name}: correct empty solution')
            else:
                print(f'FAIL {suite.name}/{input_path.name}: incorrect solver output')
            print(f'Progress: {correct} out of {attempted} correct so far in {time.time() - started_at:.2f} seconds', flush=True)
        
        if suite_scores:
            s_avg = sum(suite_scores) / len(suite_scores)
            s_min = min(suite_scores)
            s_max = max(suite_scores)
            print(f'{suite.name}: correct {suite_correct}/{suite_total} | Score Stats -> Avg: {s_avg:.4f}, Min: {s_min:.4f}, Max: {s_max:.4f}')
        else:
            print(f'{suite.name}: correct {suite_correct}/{suite_total}')

    print('\n==================== EVALUATION SUMMARY ====================')
    print(f'Total Solved / Attempted: {correct}/{attempted}')
    if all_scores:
        avg_score = sum(all_scores) / len(all_scores)
        min_score = min(all_scores)
        max_score = max(all_scores)
        print(f'Fairness Score Statistics across {len(all_scores)} valid roster solution(s):')
        print(f'  - Average Fairness Score: {avg_score:.4f}')
        print(f'  - Best (Min) Fairness Score: {min_score:.4f}')
        print(f'  - Worst (Max) Fairness Score: {max_score:.4f}')
    else:
        print('No valid roster solutions to report fairness scores.')
    print('============================================================\n')
    return correct == attempted


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {'overwrite', 'evaluate'}:
        print('Usage: python checker/check_a.py overwrite|evaluate  (or check_b.py)')
        return 2
    if sys.argv[1] == 'overwrite':
        return 0 if overwrite_models() else 1
    return 0 if evaluate() else 1


if __name__ == '__main__':
    raise SystemExit(main())
