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
    global SHIFT, is_surgical, on_leave, is_surgical_nurse, sole_surg_nurses, Domain, Assignment
    global morning_count, afternoon_count, evening_count, shifts_worked, b_count
    global consecutive_work, prev_consecutive, cM, cA, cE, backtrack_calls

    N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves = parse_input(input_csv)
    output_file = None

    SHIFT = {'M', 'A', 'E', 'R', 'B', 'XX'}
    sys.setrecursionlimit(max(10000, N * D + 100))

    is_surgical = [days[j] == 'S' for j in range(D)]
    on_leave = [[leaves[i * D + j] == 'L' for j in range(D)] for i in range(N)]
    is_surgical_nurse = [i < Ns for i in range(N)]

    sole_surg_nurses = {}
    for j in range(D):
        if is_surgical[j]:
            avail = [i for i in range(Ns) if leaves[i * D + j] != 'L']
            if len(avail) == 1:
                sole_surg_nurses[j] = avail[0]

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

    cM = [0 for _ in range(N)]
    cA = [0 for _ in range(N)]
    cE = [0 for _ in range(N)]
    backtrack_calls = 0



#...............................................add_shift: update counters when a shift is assigned.......................................................................................
def add_shift(nurse_id, day, shift):

    Assignment[nurse_id][day] = shift

    # ....................................save current consecutive_work before modifying, so remove_shift can restore it in O(1).......................................................
    prev_consecutive[nurse_id].append(consecutive_work[nurse_id])

    if shift == 'M':
        morning_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1
        cM[nurse_id] += 1

    elif shift == 'A':
        afternoon_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1
        cA[nurse_id] += 1

    elif shift == 'E':
        evening_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1
        cE[nurse_id] += 1

    elif shift == 'B':
        morning_count[day] += 1
        afternoon_count[day] += 1
        b_count[day] += 1
        shifts_worked[nurse_id] += 2
        consecutive_work[nurse_id] += 1
        cM[nurse_id] += 1
        cA[nurse_id] += 1

    elif shift == 'R':
        consecutive_work[nurse_id] = 0

#...............................................remove_shift: update counters when a shift is unassigned.......................................................................................
def remove_shift(nurse_id, day, shift):

    Assignment[nurse_id][day] = 'XX'

    if shift == 'M':
        morning_count[day] -= 1
        shifts_worked[nurse_id] -= 1
        cM[nurse_id] -= 1

    elif shift == 'A':
        afternoon_count[day] -= 1
        shifts_worked[nurse_id] -= 1
        cA[nurse_id] -= 1

    elif shift == 'E':
        evening_count[day] -= 1
        shifts_worked[nurse_id] -= 1
        cE[nurse_id] -= 1

    elif shift == 'B':
        morning_count[day] -= 1
        afternoon_count[day] -= 1
        b_count[day] -= 1
        shifts_worked[nurse_id] -= 2
        cM[nurse_id] -= 1
        cA[nurse_id] -= 1

    # ....................................restore consecutive_work in O(1) using the saved stack instead of an O(D) backward scan.......................................................
    consecutive_work[nurse_id] = prev_consecutive[nurse_id].pop()

#.......................................delta cost calculation for LCV / candidate sorting................................................................
def delta_cost(nurse_id, shift):
    m_val, a_val, e_val = cM[nurse_id], cA[nurse_id], cE[nurse_id]
    old_cost = (m_val - a_val)**2 + (a_val - e_val)**2 + (e_val - m_val)**2
    if shift == 'M': m_val += 1
    elif shift == 'A': a_val += 1
    elif shift == 'E': e_val += 1
    elif shift == 'B': m_val += 1; a_val += 1
    new_cost = (m_val - a_val)**2 + (a_val - e_val)**2 + (e_val - m_val)**2
    return new_cost - old_cost

#.......................................function to check if an assignment is consistent or not................................................................
def is_consistent(assignment, domain, nurse_id, day, shift):

    if shift not in domain[nurse_id][day]:
        return False

    if shift != 'R':
        if shifts_worked[nurse_id] >= max_shifts:
            return False
        if shift == 'B' and shifts_worked[nurse_id] + 2 > max_shifts:
            return False
        if consecutive_work[nurse_id] >= 5:
            return False

    prev_shift = assignment[nurse_id][day - 1] if day > 0 else 'XX'

    if shift in {'M', 'B'}:
        if morning_count[day] >= m:
            return False
        if prev_shift in {'M', 'B', 'E'}:
            return False

    if shift in {'A', 'B'}:
        if afternoon_count[day] >= a:
            return False

    if shift == 'E':
        if evening_count[day] >= e:
            return False

    if prev_shift == 'B' and shift in {'M', 'A'}:
        return False

    return True


#..................................................function to check if the daily constraints are satisfied.........................................................................
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


#..............................................Selecting unassigned variable using MRV........................................................................
def select_unassigned_variable(assignment, domain, day):

    best_nurse_id = -1
    best_domain_size = float('inf')
    best_day = -1
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

                if is_consistent(
                    assignment,
                    domain,
                    nurse_id,
                    day,
                    shift
                ):
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
                return nurse_id, day, []

            if can_m:
                possible_m += 1

            if can_a:
                possible_a += 1

            if can_e:
                possible_e += 1

            if domain_size < best_domain_size:

                best_domain_size = domain_size
                best_nurse_id = nurse_id
                best_day = day
                best_consistent_shifts = consistent_shifts

            elif domain_size == best_domain_size:
                best_is_surg = (surgical_day and b_count[day] == 0 and is_surgical_nurse[best_nurse_id])
                curr_is_surg = (surgical_day and b_count[day] == 0 and is_surgical_nurse[nurse_id])

                if curr_is_surg and not best_is_surg:
                    best_nurse_id = nurse_id
                    best_consistent_shifts = consistent_shifts
                elif curr_is_surg == best_is_surg:
                    if shifts_worked[nurse_id] < shifts_worked[best_nurse_id]:
                        best_nurse_id = nurse_id
                        best_consistent_shifts = consistent_shifts

    # ....................................capacity forward checking: prune if remaining unassigned nurses cannot fulfill day requirements.......................................................
    remaining_m = m - morning_count[day]
    remaining_a = a - afternoon_count[day]
    remaining_e = e - evening_count[day]

    if possible_m < remaining_m or possible_a < remaining_a or possible_e < remaining_e:
        return -2, day, []

    if surgical_day and b_count[day] == 0 and not possible_b:
        return -2, day, []

    if remaining_m + remaining_a + remaining_e > 2 * unassigned_nurses:
        return -2, day, []

    return best_nurse_id, best_day, best_consistent_shifts                               #return the best nurse id, best day, and consistent shifts for that nurse


#..................................................Ordering domain values................................................................................ me
def order_domain_values(assignment, domain, nurse_id, day, consistent_shifts):

    if len(consistent_shifts) <= 1:
        return consistent_shifts

    value_scores = {}                                                                     #dictionary to store the scores for each shift based on the number of remaining choices for other nurses

    unassigned_others = [
        other_id for other_id in range(N)
        if other_id != nurse_id and assignment[other_id][day] == 'XX'
    ]

    if not unassigned_others:
        return consistent_shifts

    sample_others = set(unassigned_others[:8]) if len(unassigned_others) > 8 else set(unassigned_others)

    for shift in consistent_shifts:                                                       #for each consistent shift, check the remaining choices for other nurses

        add_shift(                                                                        #incrementally assign the shift to the nurse for the day to check the remaining choices for other nurses
            nurse_id,
            day,
            shift
        )

        total_remaining_choices = 0                                                       #variable to store the total remaining choices for other nurses on the same day after assigning the shift to the selected nurse
        valid = True

        for other_nurse_id in unassigned_others:

            choices = 0

            for other_shift in domain[other_nurse_id][day]:

                if is_consistent(
                    assignment,
                    domain,
                    other_nurse_id,
                    day,
                    other_shift
                ):
                    choices += 1

            if choices == 0:
                valid = False
                break

            if other_nurse_id in sample_others:
                total_remaining_choices += choices

        remove_shift(                                                                      #decrementally unassign the shift from the nurse for the day to restore the assignment state for the next iteration
            nurse_id,
            day,
            shift
        )

        if valid:
            value_scores[shift] = total_remaining_choices

        else:
            value_scores[shift] = -1

    ordered_shifts = sorted(                                                               #sort the shifts in the domain of the selected nurse for the current day based on their scores in descending order, prioritizing active working shifts over rest 'R' to fulfill daily shift quotas first
        consistent_shifts,
        key=lambda shift: (shift == 'R', -value_scores.get(shift, -1))
    )

    return ordered_shifts


# .................................................Backtracking search algorithm........................................................................
def backtrack(assignment, domain, day, restart_idx=0, allow_multi_b=False):
    global backtrack_calls
    backtrack_calls += 1
    if backtrack_calls > 15000:
        return None

    if day == D:                                                                          #if all days have been assigned, return the assignment as a solution
        return assignment

    # ....................................fast shortcut: if daily active shift quotas are fulfilled, batch assign 'R' to all remaining nurses and advance to day + 1.......................................................
    if (
        morning_count[day] == m
        and afternoon_count[day] == a
        and evening_count[day] == e
        and (not is_surgical[day] or b_count[day] >= 1)
    ):
        unassigned = [
            i for i in range(N) if assignment[i][day] == 'XX'
        ]

        if not unassigned:
            if not check_day_constraints(assignment, day):
                return None
            return backtrack(assignment, domain, day + 1, restart_idx, allow_multi_b)

        valid = True
        for nid in unassigned:
            if not is_consistent(assignment, domain, nid, day, 'R'):
                valid = False
                break

        if not valid:
            return None

        for nid in unassigned:
            add_shift(nid, day, 'R')

        result = backtrack(assignment, domain, day + 1, restart_idx, allow_multi_b)

        if result is not None:
            return result

        for nid in unassigned:
            remove_shift(nid, day, 'R')

        return None

    target_shift = None
    if is_surgical[day] and allow_multi_b and morning_count[day] < m and afternoon_count[day] < a:
        target_shift = 'B'
    elif is_surgical[day] and b_count[day] == 0:
        target_shift = 'B'
    elif morning_count[day] < m:
        target_shift = 'M'
    elif afternoon_count[day] < a:
        target_shift = 'A'
    elif evening_count[day] < e:
        target_shift = 'E'

    if target_shift is not None:
        rem_req = (D - day) * (m + a + e) - (morning_count[day] + afternoon_count[day] + evening_count[day])
        rem_avail = sum(max_shifts - shifts_worked[i] for i in range(N))
        if rem_avail < rem_req:
            return None

        for j in range(day, D):
            if is_surgical[j] and b_count[j] == 0 and j in sole_surg_nurses:
                sole_nurse = sole_surg_nurses[j]
                if shifts_worked[sole_nurse] + 2 > max_shifts:
                    return None

        rem_surg_days = sum(1 for j in range(day, D) if is_surgical[j] and b_count[j] == 0)
        avail_surg_budget = sum(2 * ((max_shifts - shifts_worked[i]) // 2) for i in range(Ns))
        if avail_surg_budget < 2 * rem_surg_days:
            return None

        if target_shift == 'B':
            candidates = [
                i for i in range(Ns)
                if assignment[i][day] == 'XX' and is_consistent(assignment, domain, i, day, 'B')
            ]
        else:
            candidates = [
                i for i in range(N)
                if assignment[i][day] == 'XX' and is_consistent(assignment, domain, i, day, target_shift)
            ]

        if not candidates:
            return None

        nurse_offset = restart_idx % N
        if target_shift == 'B':
            candidates.sort(key=lambda i: (shifts_worked[i], delta_cost(i, 'B'), (i + nurse_offset) % N))
        elif rem_surg_days > 0 and Ns <= 5:
            candidates.sort(key=lambda i: (is_surgical_nurse[i], shifts_worked[i], delta_cost(i, target_shift), (i + nurse_offset) % N))
        else:
            candidates.sort(key=lambda i: (shifts_worked[i], delta_cost(i, target_shift), (i + nurse_offset) % N))

        for cand in candidates:
            add_shift(cand, day, target_shift)
            result = backtrack(assignment, domain, day, restart_idx, allow_multi_b)
            if result is not None:
                return result
            remove_shift(cand, day, target_shift)

        return None

    all_assigned = True

    for nurse_id in range(N):

        if assignment[nurse_id][day] == 'XX':                                             #if there is at least one nurse who is unassigned for the current day, set all_assigned to False and break the loop
            all_assigned = False
            break

    if all_assigned:

        if not check_day_constraints(assignment, day):                                    #if all nurses have been assigned for the current day, check if the daily constraints are satisfied. If not, return None, as this means that the assignment is not consistent and cannot be completed
            return None

        return backtrack(assignment, domain, day + 1, restart_idx, allow_multi_b)                                     #if the daily constraints are satisfied, move on to the next day and continue the backtracking search

    nurse_id, _, consistent_shifts = select_unassigned_variable(
        assignment,
        domain,
        day
    )

    if nurse_id < 0:                                                                     #if no unassigned nurse was found or capacity failed, return None
        return None

    if len(consistent_shifts) <= 1:
        ordered_shifts = consistent_shifts

    else:
        ordered_shifts = order_domain_values(                                                 #order the shifts in the domain of the selected nurse for the current day using the least constraining value heuristic, so that the shift with the least impact on other nurses' choices is tried first
            assignment,
            domain,
            nurse_id,
            day,
            consistent_shifts
        )

    for shift in ordered_shifts:
        if is_consistent(
            assignment,
            domain,
            nurse_id,
            day,
            shift
        ):
            add_shift(
                nurse_id,
                day,
                shift
            )
            result = backtrack(
                assignment,
                domain,
                day,
                restart_idx,
                allow_multi_b
            )
            if result is not None:
                return result
            remove_shift(
                nurse_id,
                day,
                shift
            )

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

    objective = 0
    num_nurses = len(assignment)
    num_days = len(assignment[0])
    for nurse_id in range(num_nurses):
        mornings = sum(assignment[nurse_id][day] in {'M', 'B'} for day in range(num_days))
        afternoons = sum(assignment[nurse_id][day] in {'A', 'B'} for day in range(num_days))
        evenings = sum(assignment[nurse_id][day] == 'E' for day in range(num_days))
        total = mornings + afternoons + evenings
        objective += 3 * (mornings ** 2 + afternoons ** 2 + evenings ** 2) - total ** 2

    return objective


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


#..................................................function to check problem feasibility upfront................................................................ me
def is_problem_feasible():
    if m > N or a > N or e > N or (m + a + e) > N:
        return False

    if D * (m + a + e) > N * max_shifts:
        return False

    for j in range(D):
        avail_nurses = sum(1 for i in range(N) if leaves[i * D + j] != 'L')
        min_needed = (m + a + e - 1) if is_surgical[j] else (m + a + e)
        if avail_nurses < min_needed:
            return False

        if is_surgical[j]:
            avail_surg = sum(1 for i in range(Ns) if leaves[i * D + j] != 'L')
            if avail_surg < 1:
                return False

    return True


def is_nurse_valid(assignment, nurse_id):
    sw = sum(2 if s == 'B' else (1 if s != 'R' else 0) for s in assignment[nurse_id])
    if sw > max_shifts:
        return False
    run = 0
    for s in assignment[nurse_id]:
        if s != 'R':
            run += 1
            if run > 5:
                return False
        else:
            run = 0
    for d in range(D):
        s = assignment[nurse_id][d]
        if s not in Domain[nurse_id][d]:
            return False
        if d > 0:
            p = assignment[nurse_id][d - 1]
            if s in {'M', 'B'} and p in {'M', 'B', 'E'}:
                return False
            if p == 'B' and s in {'M', 'A'}:
                return False
    return True


def nurse_cost(assignment, i):
    cM = sum(1 for s in assignment[i] if s in {'M', 'B'})
    cA = sum(1 for s in assignment[i] if s in {'A', 'B'})
    cE = sum(1 for s in assignment[i] if s == 'E')
    tot = cM + cA + cE
    return 3 * (cM**2 + cA**2 + cE**2) - tot**2


def fast_local_search(state, deadline):
    curr = [row[:] for row in state]
    cM_curr = [sum(1 for s in curr[i] if s in {'M', 'B'}) for i in range(N)]
    cA_curr = [sum(1 for s in curr[i] if s in {'A', 'B'}) for i in range(N)]
    cE_curr = [sum(1 for s in curr[i] if s == 'E') for i in range(N)]

    def cost_delta(i, s_old, s_new):
        m, a, e = cM_curr[i], cA_curr[i], cE_curr[i]
        old_c = 3 * (m * m + a * a + e * e) - (m + a + e) ** 2
        if s_old in {'M', 'B'}: m -= 1
        if s_old in {'A', 'B'}: a -= 1
        if s_old == 'E': e -= 1
        if s_new in {'M', 'B'}: m += 1
        if s_new in {'A', 'B'}: a += 1
        if s_new == 'E': e += 1
        return (3 * (m * m + a * a + e * e) - (m + a + e) ** 2) - old_c

    def apply_shift(i, s_old, s_new):
        if s_old in {'M', 'B'}: cM_curr[i] -= 1
        if s_old in {'A', 'B'}: cA_curr[i] -= 1
        if s_old == 'E': cE_curr[i] -= 1
        if s_new in {'M', 'B'}: cM_curr[i] += 1
        if s_new in {'A', 'B'}: cA_curr[i] += 1
        if s_new == 'E': cE_curr[i] += 1

    curr_cost = compute_cost(curr)
    best = [row[:] for row in curr]
    best_cost = curr_cost

    sideways_count = 0
    max_sideways = 40
    visited = set()
    step = 0

    while step < 1000 and best_cost > 0 and time.time() < deadline:
        step += 1
        improved = False
        side_move = None

        # Move 1: Same-day shift swap between 2 nurses (L05 Page 11)
        for day in range(D):
            if time.time() >= deadline:
                break
            for i in range(N):
                s1 = curr[i][day]
                for j in range(i + 1, N):
                    s2 = curr[j][day]
                    if s1 == s2:
                        continue
                    if s2 not in Domain[i][day] or s1 not in Domain[j][day]:
                        continue
                    if s2 == 'B' and not is_surgical_nurse[i]:
                        continue
                    if s1 == 'B' and not is_surgical_nurse[j]:
                        continue

                    d_cost = cost_delta(i, s1, s2) + cost_delta(j, s2, s1)
                    if d_cost < 0:
                        curr[i][day], curr[j][day] = s2, s1
                        if is_nurse_valid(curr, i) and is_nurse_valid(curr, j):
                            apply_shift(i, s1, s2)
                            apply_shift(j, s2, s1)
                            curr_cost += d_cost
                            improved = True
                            sideways_count = 0
                            visited.clear()
                            if curr_cost < best_cost:
                                best = [row[:] for row in curr]
                                best_cost = curr_cost
                            break
                        curr[i][day], curr[j][day] = s1, s2
                    elif d_cost == 0 and not improved and sideways_count < max_sideways and side_move is None:
                        fp = (day, i, j, s2, s1)
                        if fp not in visited:
                            curr[i][day], curr[j][day] = s2, s1
                            if is_nurse_valid(curr, i) and is_nurse_valid(curr, j):
                                side_move = (day, i, j, s1, s2)
                            curr[i][day], curr[j][day] = s1, s2
                if improved:
                    break
            if improved:
                break

        if improved:
            continue

        # Move 2: 2-Nurse 2-Day reciprocal swap (if no improving Move 1)
        if time.time() < deadline:
            work_days = [[d for d in range(D) if curr[idx][d] != 'R'] for idx in range(N)]
            for i in range(N):
                if time.time() >= deadline or improved:
                    break
                for j in range(i + 1, N):
                    if time.time() >= deadline or improved:
                        break
                    days_union = sorted(set(work_days[i] + work_days[j]))
                    if len(days_union) < 2:
                        continue
                    for idx1 in range(len(days_union)):
                        d1 = days_union[idx1]
                        s11, s21 = curr[i][d1], curr[j][d1]
                        for idx2 in range(idx1 + 1, len(days_union)):
                            d2 = days_union[idx2]
                            s12, s22 = curr[i][d2], curr[j][d2]
                            if s11 == s21 or s12 == s22:
                                continue
                            if s21 not in Domain[i][d1] or s11 not in Domain[j][d1]:
                                continue
                            if s22 not in Domain[i][d2] or s12 not in Domain[j][d2]:
                                continue
                            if (s21 == 'B' or s22 == 'B') and not is_surgical_nurse[i]:
                                continue
                            if (s11 == 'B' or s12 == 'B') and not is_surgical_nurse[j]:
                                continue

                            old_pair = nurse_cost(curr, i) + nurse_cost(curr, j)
                            curr[i][d1], curr[j][d1] = s21, s11
                            curr[i][d2], curr[j][d2] = s22, s12
                            if is_nurse_valid(curr, i) and is_nurse_valid(curr, j):
                                new_pair = nurse_cost(curr, i) + nurse_cost(curr, j)
                                if new_pair < old_pair:
                                    apply_shift(i, s11, s21)
                                    apply_shift(j, s21, s11)
                                    apply_shift(i, s12, s22)
                                    apply_shift(j, s22, s12)
                                    curr_cost += (new_pair - old_pair)
                                    improved = True
                                    sideways_count = 0
                                    visited.clear()
                                    if curr_cost < best_cost:
                                        best = [row[:] for row in curr]
                                        best_cost = curr_cost
                                    break
                            curr[i][d1], curr[j][d1] = s11, s21
                            curr[i][d2], curr[j][d2] = s12, s22
                        if improved:
                            break
                    if improved:
                        break

        if improved:
            continue

        # Sideways Move (L05 Page 19): escape flat local minima / shoulders
        if side_move is not None:
            day, i, j, s1, s2 = side_move
            curr[i][day], curr[j][day] = s2, s1
            apply_shift(i, s1, s2)
            apply_shift(j, s2, s1)
            visited.add((day, i, j, s2, s1))
            visited.add((day, i, j, s1, s2))
            sideways_count += 1
        else:
            break

    return best, best_cost


def local_search_optimize(time_budget):
    global backtrack_calls
    if not is_problem_feasible():
        return None

    start_time = time.time()
    deadline = start_time + max(0.5, time_budget - 2.5)

    initialize_problem(CURRENT_INPUT_CSV)
    backtrack_calls = 0
    best = backtrack(Assignment, Domain, 0, restart_idx=0, allow_multi_b=False)
    if best is None:
        return None

    best, best_cost = fast_local_search(best, deadline)
    if best_cost == 0:
        return best

    # Systematic deterministic restarts using CSP variable/value ordering rotations (L04 & L05)
    max_restarts = 20
    for r in range(1, max_restarts):
        if time.time() >= deadline - 0.2:
            break
        initialize_problem(CURRENT_INPUT_CSV)
        backtrack_calls = 0
        multi_b = (r % 2 == 1 and D <= 7 and Ns * max_shifts >= 3 * D)
        candidate_state = backtrack(Assignment, Domain, 0, restart_idx=r, allow_multi_b=multi_b)
        if candidate_state is None:
            continue
        cand_opt, cand_cost = fast_local_search(candidate_state, deadline)
        if cand_cost < best_cost:
            best = [row[:] for row in cand_opt]
            best_cost = cand_cost
            if best_cost == 0:
                break

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
    time_budget = min(0.95 * T, 20.0)
    result = local_search_optimize(time_budget)

    if result is None:
        with open(output_file, 'w') as f:
            json.dump({}, f)
        return
    
    write_output(result, output_file)
    print(f'Fairness cost: {compute_cost(result)}')


if __name__ == '__main__':
    main()

