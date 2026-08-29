import csv
import json
import sys
import time


#..................................................read the input CSV..................................................................................
def parse_input(input_csv):
    """Reads the CSV and initializes problem variables."""
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        row = next(reader)

        N = int(row['N'])
        D = int(row['D'])
        N_s = int(row['N_s'])
        N_g = int(row['N_g'])
        m = int(row['m'])
        a = int(row['a'])
        e = int(row['e'])
        T = float(row['T'])
        days = row['days']
        max_shifts = int(row['K'])
        leaves = row['leaves']

    return N, D, N_s, N_g, m, a, e, T, days, max_shifts, leaves


#..................................................initialize the standalone part a state..................................................................................
def initialize_problem(input_csv):
    global N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves, output_file
    global SHIFT, is_surgical, on_leave, is_surgical_nurse, Domain, Assignment
    global morning_count, afternoon_count, evening_count, shifts_worked, b_count
    global consecutive_work, prev_consecutive

    N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves = parse_input(input_csv)
    output_file = None

    SHIFT = {'M', 'A', 'E', 'R', 'B', 'XX'}
    sys.setrecursionlimit(max(10000, N * D + 100))

    is_surgical = [days[j] == 'S' for j in range(D)]
    on_leave = [[leaves[i * D + j] == 'L' for j in range(D)] for i in range(N)]
    is_surgical_nurse = [i < Ns for i in range(N)]

    Domain = []
    for i in range(N):
        Domain.append([])
        if i < Ns:
            for j in range(D):
                if days[j] == 'S':
                    Domain[i].append({'M', 'A', 'E', 'R', 'B'})
                else:
                    Domain[i].append({'M', 'A', 'E', 'R'})
        else:
            for j in range(D):
                Domain[i].append({'M', 'A', 'E', 'R'})

        for j in range(D):
            if leaves[i * D + j] == 'L':
                Domain[i][j] = {'R'}

    Assignment = [['XX' for j in range(D)] for i in range(N)]
    morning_count = [0 for _ in range(D)]
    afternoon_count = [0 for _ in range(D)]
    evening_count = [0 for _ in range(D)]
    shifts_worked = [0 for _ in range(N)]
    b_count = [0 for _ in range(D)]
    consecutive_work = [0 for _ in range(N)]
    prev_consecutive = [[] for _ in range(N)]


#..................................................update the current assignment.................................................................................
def add_shift(nurse_id, day, shift):
    Assignment[nurse_id][day] = shift
    prev_consecutive[nurse_id].append(consecutive_work[nurse_id])

    if shift == 'M':
        morning_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1

    elif shift == 'A':
        afternoon_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1

    elif shift == 'E':
        evening_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1

    elif shift == 'B':
        morning_count[day] += 1
        afternoon_count[day] += 1
        b_count[day] += 1
        shifts_worked[nurse_id] += 2
        consecutive_work[nurse_id] += 1

    elif shift == 'R':
        consecutive_work[nurse_id] = 0


#..................................................update assignment for backtracking.................................................................................
def remove_shift(nurse_id, day, shift):
    Assignment[nurse_id][day] = 'XX'

    if shift == 'M':
        morning_count[day] -= 1
        shifts_worked[nurse_id] -= 1

    elif shift == 'A':
        afternoon_count[day] -= 1
        shifts_worked[nurse_id] -= 1

    elif shift == 'E':
        evening_count[day] -= 1
        shifts_worked[nurse_id] -= 1

    elif shift == 'B':
        morning_count[day] -= 1
        afternoon_count[day] -= 1
        b_count[day] -= 1
        shifts_worked[nurse_id] -= 2

    consecutive_work[nurse_id] = prev_consecutive[nurse_id].pop()


#..................................................hard constraint check..................................................................................
def is_consistent(assignment, domain, nurse_id, day, shift):
    if shift not in domain[nurse_id][day]:
        return False

    if (
        morning_count[day] == m
        and afternoon_count[day] == a
        and evening_count[day] == e
        and shift != 'R'
    ):
        return False

    if shift in {'M', 'B'} and day > 0:
        if assignment[nurse_id][day - 1] in {'M', 'B'}:
            return False

    if shift in {'M', 'B'} and day > 0:
        if assignment[nurse_id][day - 1] == 'E':
            return False

    if shift in {'M', 'B'}:
        if morning_count[day] + 1 > m:
            return False

    if shift in {'A', 'B'}:
        if afternoon_count[day] + 1 > a:
            return False

    if shift == 'E':
        if evening_count[day] + 1 > e:
            return False

    if shift != 'R' and consecutive_work[nurse_id] >= 5:
        return False

    if day > 0 and assignment[nurse_id][day - 1] == 'B':
        if shift == 'M' or shift == 'A':
            return False

    if shift == 'B':
        if shifts_worked[nurse_id] + 2 > max_shifts:
            return False
    elif shift in {'M', 'A', 'E'}:
        if shifts_worked[nurse_id] + 1 > max_shifts:
            return False

    if on_leave[nurse_id][day] and shift != 'R':
        return False

    if shift == 'B' and (not is_surgical_nurse[nurse_id] or not is_surgical[day]):
        return False

    return True


#..................................................daily constraint validation..................................................................................
def check_day_constraints(assignment, day):
    if morning_count[day] != m:
        return False
    if afternoon_count[day] != a:
        return False
    if evening_count[day] != e:
        return False
    if is_surgical[day] and b_count[day] < 1:
        return False
    return True


#..................................................select and check for next assignment..................................................................................
def select_and_check(assignment, domain, day):
    best_nurse_id = -1
    best_domain_size = float('inf')
    best_consistent_shifts = []
    unassigned_nurses = 0
    possible_m = 0
    possible_a = 0
    possible_e = 0
    possible_b = False
    surgical_day = is_surgical[day]

    for nurse_id in range(N):
        if assignment[nurse_id][day] == 'XX':
            unassigned_nurses += 1
            consistent_shifts = []
            can_m = False
            can_a = False
            can_e = False

            for shift in domain[nurse_id][day]:
                if is_consistent(assignment, domain, nurse_id, day, shift):
                    consistent_shifts.append(shift)
                    if shift == 'M' or shift == 'B':
                        can_m = True
                    if shift == 'A' or shift == 'B':
                        can_a = True
                    if shift == 'E':
                        can_e = True
                    if shift == 'B' and surgical_day and b_count[day] == 0:
                        possible_b = True

            domain_size = len(consistent_shifts)
            if domain_size == 0:
                return nurse_id, day, False, []

            if can_m:
                possible_m += 1
            if can_a:
                possible_a += 1
            if can_e:
                possible_e += 1

            if domain_size < best_domain_size:
                best_domain_size = domain_size
                best_nurse_id = nurse_id
                best_consistent_shifts = consistent_shifts

    remaining_m = m - morning_count[day]
    remaining_a = a - afternoon_count[day]
    remaining_e = e - evening_count[day]

    if possible_m < remaining_m:
        return best_nurse_id, day, False, []
    if possible_a < remaining_a:
        return best_nurse_id, day, False, []
    if possible_e < remaining_e:
        return best_nurse_id, day, False, []

    if surgical_day and b_count[day] == 0 and not possible_b:
        return best_nurse_id, day, False, []

    if remaining_m + remaining_a + remaining_e > 2 * unassigned_nurses:
        return best_nurse_id, day, False, []

    return best_nurse_id, day, True, best_consistent_shifts


#..................................................select unassigned variable via MRV..................................................................................
def select_unassigned_variable(assignment, domain, day):
    best_nurse_id = -1
    best_domain_size = float('inf')
    best_day = -1

    for nurse_id in range(N):
        if assignment[nurse_id][day] == 'XX':
            domain_size = 0
            for shift in domain[nurse_id][day]:
                if is_consistent(assignment, domain, nurse_id, day, shift):
                    domain_size += 1

            if domain_size == 0:
                return nurse_id, day

            if domain_size < best_domain_size:
                best_domain_size = domain_size
                best_nurse_id = nurse_id
                best_day = day

    return best_nurse_id, best_day


#..................................................order domain values using LCV..................................................................................
def order_domain_values(assignment, domain, nurse_id, day, consistent_shifts):
    if len(consistent_shifts) <= 1:
        return consistent_shifts

    value_scores = {}
    unassigned_others = [
        other_id for other_id in range(N)
        if other_id != nurse_id and assignment[other_id][day] == 'XX'
    ]

    if not unassigned_others:
        return consistent_shifts

    for shift in consistent_shifts:
        add_shift(nurse_id, day, shift)
        total_remaining_choices = 0
        valid = True

        for other_nurse_id in unassigned_others:
            choices = 0
            for other_shift in domain[other_nurse_id][day]:
                if is_consistent(assignment, domain, other_nurse_id, day, other_shift):
                    choices += 1
            if choices == 0:
                valid = False
                break
            total_remaining_choices += choices

        remove_shift(nurse_id, day, shift)

        if valid:
            value_scores[shift] = total_remaining_choices
        else:
            value_scores[shift] = -1

    ordered_shifts = sorted(
        consistent_shifts,
        key=lambda shift: value_scores.get(shift, -1),
        reverse=True
    )
    return ordered_shifts


#..................................................forward check pruning..................................................................................
def forward_check(assignment, domain, day):
    unassigned_nurses = 0
    possible_m = 0
    possible_a = 0
    possible_e = 0
    possible_b = False
    is_surgical_day = is_surgical[day]

    for other_nurse_id in range(N):
        if assignment[other_nurse_id][day] == 'XX':
            unassigned_nurses += 1
            has_value = False
            can_m = False
            can_a = False
            can_e = False

            for shift in domain[other_nurse_id][day]:
                if is_consistent(assignment, domain, other_nurse_id, day, shift):
                    has_value = True
                    if shift == 'M' or shift == 'B':
                        can_m = True
                    if shift == 'A' or shift == 'B':
                        can_a = True
                    if shift == 'E':
                        can_e = True
                    if shift == 'B' and is_surgical_day and b_count[day] == 0:
                        possible_b = True

            if not has_value:
                return False
            if can_m:
                possible_m += 1
            if can_a:
                possible_a += 1
            if can_e:
                possible_e += 1

    remaining_m = m - morning_count[day]
    remaining_a = a - afternoon_count[day]
    remaining_e = e - evening_count[day]

    if possible_m < remaining_m:
        return False
    if possible_a < remaining_a:
        return False
    if possible_e < remaining_e:
        return False

    if is_surgical_day and b_count[day] == 0 and not possible_b:
        return False

    if remaining_m + remaining_a + remaining_e > 2 * unassigned_nurses:
        return False

    return True


#..................................................backtracking search..................................................................................
def backtrack(assignment, domain, day):
    if day == D:
        return assignment

    all_assigned = True
    for nurse_id in range(N):
        if assignment[nurse_id][day] == 'XX':
            all_assigned = False
            break

    if all_assigned:
        if not check_day_constraints(assignment, day):
            return None
        return backtrack(assignment, domain, day + 1)

    nurse_id, _, feasible, consistent_shifts = select_and_check(assignment, domain, day)
    if nurse_id == -1 or not feasible:
        return None

    ordered_shifts = order_domain_values(assignment, domain, nurse_id, day, consistent_shifts)

    for shift in ordered_shifts:
        add_shift(nurse_id, day, shift)
        if forward_check(assignment, domain, day):
            result = backtrack(assignment, domain, day)
            if result is not None:
                return result
        remove_shift(nurse_id, day, shift)

    return None


#..................................................write the output JSON..................................................................................
def write_output(solution, output_file):
    if solution is None:
        with open(output_file, 'w') as f:
            json.dump({}, f)
        return

    output = {}
    for i in range(N):
        for j in range(D):
            output[f'N{i}_{j}'] = solution[i][j]

    with open(output_file, 'w') as f:
        json.dump(output, f)


#..................................................standalone part a solver..................................................................................
def solve_part_a():
    result = backtrack(Assignment, Domain, 0)

    if result is not None:
        print('Solution found:')
        for row in result:
            print(row)
        write_output(result, output_file)
    else:
        print('No solution exists.')
        write_output(None, output_file)


#..................................................part b cost functions..................................................................................
def reset_globals():
    global Assignment, morning_count, afternoon_count, evening_count
    global b_count, shifts_worked, consecutive_work, prev_consecutive

    Assignment = [['XX' for _ in range(D)] for _ in range(N)]
    morning_count = [0 for _ in range(D)]
    afternoon_count = [0 for _ in range(D)]
    evening_count = [0 for _ in range(D)]
    b_count = [0 for _ in range(D)]
    shifts_worked = [0 for _ in range(N)]
    consecutive_work = [0 for _ in range(N)]
    prev_consecutive = [[] for _ in range(N)]


#..................................................count shifts per nurse..................................................................................
def compute_shift_counts_for_nurse(assignment, nurse_id):
    counts = {'M': 0, 'A': 0, 'E': 0}
    for shift in assignment[nurse_id]:
        if shift in {'M', 'B'}:
            counts['M'] += 1
        if shift in {'A', 'B'}:
            counts['A'] += 1
        if shift == 'E':
            counts['E'] += 1
    return counts


#..................................................compute mean shift count..................................................................................
def compute_mean_shift_count(counts):
    return (counts['M'] + counts['A'] + counts['E']) / 3.0


#..................................................compute per nurse cost..................................................................................
def compute_nurse_cost(counts):
    mean = compute_mean_shift_count(counts)
    return (
        (counts['M'] - mean) ** 2
        + (counts['A'] - mean) ** 2
        + (counts['E'] - mean) ** 2
    ) / 3.0


#..................................................compute total cost..................................................................................
def compute_cost(assignment):
    if assignment is None or not assignment:
        return float('inf')

    total = 0.0
    num_nurses = len(assignment)
    for nurse_id in range(num_nurses):
        counts = compute_shift_counts_for_nurse(assignment, nurse_id)
        total += compute_nurse_cost(counts)

    return (9.0 / num_nurses) * total if num_nurses else 0.0


#..................................................validate the whole roster against hard constraints..................................................................................
def is_valid_assignment(assignment):
    if not assignment or not assignment[0]:
        return False

    num_nurses = len(assignment)
    num_days = len(assignment[0])

    for i in range(num_nurses):
        if len(assignment[i]) != num_days:
            return False
        for j in range(num_days):
            shift = assignment[i][j]
            if shift == 'XX':
                return False
            if shift not in Domain[i][j]:
                return False
            if on_leave[i][j] and shift != 'R':
                return False
            if shift == 'B' and (not is_surgical_nurse[i] or not is_surgical[j]):
                return False

    for day in range(num_days):
        morning = 0
        afternoon = 0
        evening = 0
        b_count_day = 0
        for i in range(num_nurses):
            shift = assignment[i][day]
            if shift in {'M', 'B'}:
                morning += 1
            if shift in {'A', 'B'}:
                afternoon += 1
            if shift == 'E':
                evening += 1
            if shift == 'B':
                b_count_day += 1

        if morning != m or afternoon != a or evening != e:
            return False
        if is_surgical[day] and b_count_day < 1:
            return False

    for i in range(num_nurses):
        run = 0
        for j in range(num_days):
            shift = assignment[i][j]
            if shift in {'M', 'A', 'E', 'B'}:
                run += 1
                if run > 5:
                    return False
            else:
                run = 0

        total_shift_load = 0
        for j in range(num_days):
            shift = assignment[i][j]
            if shift == 'B':
                total_shift_load += 2
            elif shift in {'M', 'A', 'E'}:
                total_shift_load += 1
        if total_shift_load > max_shifts:
            return False

        for j in range(num_days):
            shift = assignment[i][j]
            if shift in {'M', 'B'} and j > 0:
                if assignment[i][j - 1] in {'M', 'B'}:
                    return False
            if shift in {'M', 'B'} and j > 0:
                if assignment[i][j - 1] == 'E':
                    return False
            if j > 0 and assignment[i][j - 1] == 'B':
                if shift == 'M' or shift == 'A':
                    return False

    return True


#..................................................generate valid neighboring states..................................................................................
def get_valid_neighbors(current_state):
    if current_state is None:
        return []

    neighbors = []
    num_nurses = len(current_state)
    num_days = len(current_state[0])

    for day in range(num_days):
        for nurse_id in range(num_nurses):
            current_shift = current_state[nurse_id][day]
            for candidate in Domain[nurse_id][day]:
                if candidate == current_shift:
                    continue
                new_state = [row[:] for row in current_state]
                new_state[nurse_id][day] = candidate
                if is_valid_assignment(new_state):
                    neighbors.append(new_state)

        for i in range(num_nurses):
            for j in range(i + 1, num_nurses):
                if (i < Ns) != (j < Ns):
                    continue
                s1 = current_state[i][day]
                s2 = current_state[j][day]
                if s1 == s2:
                    continue
                new_state = [row[:] for row in current_state]
                new_state[i][day], new_state[j][day] = new_state[j][day], new_state[i][day]
                if is_valid_assignment(new_state):
                    neighbors.append(new_state)

    return neighbors


#..................................................improve the current solution using local search..................................................................................
def local_search_optimize(time_budget):
    deadline = time.time() + time_budget

    current = backtrack(Assignment, Domain, 0)
    if current is None:
        return None

    best = [row[:] for row in current]
    best_cost = compute_cost(best)
    current_cost = best_cost

    while time.time() < deadline:
        improved = False
        neighbors = get_valid_neighbors(current)

        for neighbor in neighbors:
            neighbor_cost = compute_cost(neighbor)
            if neighbor_cost < current_cost - 1e-9:
                current = neighbor
                current_cost = neighbor_cost
                improved = True

                if neighbor_cost < best_cost - 1e-9:
                    best = [row[:] for row in neighbor]
                    best_cost = neighbor_cost
                break

        if not improved:
            reset_globals()
            initialize_problem(CURRENT_INPUT_CSV)
            restarted = backtrack(Assignment, Domain, 0)
            if restarted is None:
                break
            current = [row[:] for row in restarted]
            current_cost = compute_cost(current)
            if current_cost < best_cost - 1e-9:
                best = [row[:] for row in current]
                best_cost = current_cost

    return best


#..................................................main entry point..................................................................................
def main():
    if len(sys.argv) != 3:
        raise ValueError('Usage: python part_b.py <input_csv> <output_json>')

    input_csv = sys.argv[1]
    output_file = sys.argv[2]

    global CURRENT_INPUT_CSV
    CURRENT_INPUT_CSV = input_csv

    initialize_problem(input_csv)
    time_budget = 0.95 * T
    result = local_search_optimize(time_budget)

    if result is None:
        with open(output_file, 'w') as f:
            json.dump({}, f)
        return
    
    write_output(result, output_file)
    print(f'Fairness cost: {compute_cost(result)}')


if __name__ == '__main__':
    main()

