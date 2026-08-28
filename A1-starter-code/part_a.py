import sys
import csv
import json


def parse_input(input_csv):
    """Reads the CSV and initializes problem variables."""
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        row = next(reader)
        print(row)

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


if __name__ == '__main__':
    N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves = parse_input(sys.argv[1])
    output_file = sys.argv[2]


SHIFT = {'M', 'A', 'E', 'R', 'B', 'XX'}


# ====================================================================================================
# CHANGED: increase recursion limit for large N*D instances
# ====================================================================================================

sys.setrecursionlimit(max(10000, N * D + 100))


# assignment will be a vector of size N*D
# each element is a vector of size D and in total N elements

Domain = []

for i in range(N):

    Domain.append([])

    if i < Ns:

        for j in range(D):

            # ====================================================================================================
            # CHANGED: B is only allowed on surgical days
            # ====================================================================================================

            if days[j] == 'S':
                Domain[i].append({'M', 'A', 'E', 'R', 'B'})
            else:
                Domain[i].append({'M', 'A', 'E', 'R'})

    else:

        for j in range(D):
            Domain[i].append({'M', 'A', 'E', 'R'})


# ====================================================================================================
# CHANGED: leave days only have R in their domain
# ====================================================================================================

for i in range(N):

    for j in range(D):

        if leaves[i * D + j] == 'L':
            Domain[i][j] = {'R'}


Assignment = [['XX' for j in range(D)] for i in range(N)]


# ====================================================================================================
# CHANGED: maintain daily staffing counts
# ====================================================================================================

morning_count = [0 for _ in range(D)]
afternoon_count = [0 for _ in range(D)]
evening_count = [0 for _ in range(D)]


# ====================================================================================================
# CHANGED: maintain total shifts worked by each nurse
# B counts as 2 shifts
# ====================================================================================================

shifts_worked = [0 for _ in range(N)]


# ......................................................................................................
def is_consistent(assignment, domain, nurse_id, day, shift):

    # Check if the shift is in the nurse's domain
    if shift not in domain[nurse_id][day]:
        return False

    # ====================================================================================================
    # CHANGED: B also counts as a morning shift
    # ====================================================================================================

    # No nurse can have two consecutive morning shifts
    if shift in {'M', 'B'} and day > 0:
        if assignment[nurse_id][day - 1] in {'M', 'B'}:
            return False

    # ====================================================================================================
    # CHANGED: B also contains a morning shift, so E -> B is forbidden
    # ====================================================================================================

    # No nurse can have a morning shift immediately after an evening shift
    if shift in {'M', 'B'} and day > 0:
        if assignment[nurse_id][day - 1] == 'E':
            return False

    # ====================================================================================================
    # CHANGED: use maintained daily counts instead of scanning all nurses
    # ====================================================================================================

    if shift in {'M', 'B'}:
        if morning_count[day] + 1 > m:
            return False

    if shift in {'A', 'B'}:
        if afternoon_count[day] + 1 > a:
            return False

    if shift == 'E':
        if evening_count[day] + 1 > e:
            return False

    # No nurse works more than 5 consecutive days
    if day >= 5 and shift != 'R':

        consecutive_days = 0

        for i in range(day - 5, day):

            if assignment[nurse_id][i] != 'R':
                consecutive_days += 1
            else:
                break

        if consecutive_days >= 5:
            return False

    # After B, M or A cannot be assigned
    if day > 0 and assignment[nurse_id][day - 1] == 'B':

        if shift == 'M' or shift == 'A':
            return False

    # ====================================================================================================
    # CHANGED: use maintained shift count instead of scanning all D days
    # ====================================================================================================

    if shift == 'B':

        if shifts_worked[nurse_id] + 2 > max_shifts:
            return False

    elif shift in {'M', 'A', 'E'}:

        if shifts_worked[nurse_id] + 1 > max_shifts:
            return False

    # Leave constraint
    if leaves[nurse_id * D + day] == 'L' and shift != 'R':
        return False

    return True


# Check the final assignment is valid
def check_day_constraints(assignment, day):

    # ====================================================================================================
    # CHANGED: use maintained daily counts
    # ====================================================================================================

    if morning_count[day] != m:
        return False

    if afternoon_count[day] != a:
        return False

    if evening_count[day] != e:
        return False

    # If surgical day then at least one surgical nurse has B
    if days[day] == 'S':

        surgical_nurse_has_B = False

        for i in range(Ns):

            if assignment[i][day] == 'B':
                surgical_nurse_has_B = True
                break

        if not surgical_nurse_has_B:
            return False

    return True


# Selecting unassigned variable using MRV
def select_unassigned_variable(assignment, domain, day):

    best_nurse_id = -1
    best_domain_size = float('inf')
    best_day = -1

    for nurse_id in range(N):

        if assignment[nurse_id][day] == 'XX':

            domain_size = 0

            for shift in domain[nurse_id][day]:

                if is_consistent(
                    assignment,
                    domain,
                    nurse_id,
                    day,
                    shift
                ):
                    domain_size += 1

            if domain_size < best_domain_size:

                best_domain_size = domain_size
                best_nurse_id = nurse_id
                best_day = day

    return best_nurse_id, best_day


# ====================================================================================================
# CHANGED: cheaper value ordering based on the remaining staffing requirements
# ====================================================================================================

def order_domain_values(assignment, domain, nurse_id, day):

    remaining_m = m - morning_count[day]
    remaining_a = a - afternoon_count[day]
    remaining_e = e - evening_count[day]

    def value_score(shift):

        score = 0

        if shift == 'B':

            if remaining_m > 0:
                score += 2

            if remaining_a > 0:
                score += 2

        elif shift == 'M':

            if remaining_m > 0:
                score += 2

        elif shift == 'A':

            if remaining_a > 0:
                score += 2

        elif shift == 'E':

            if remaining_e > 0:
                score += 2

        return -score

    return sorted(
        domain[nurse_id][day],
        key=value_score
    )


# ====================================================================================================
# CHANGED: stronger forward checking using remaining staffing requirements
# ====================================================================================================

def forward_check(assignment, domain, day):

    possible_m = 0
    possible_a = 0
    possible_e = 0
    possible_b = 0

    for nurse_id in range(N):

        if assignment[nurse_id][day] == 'XX':

            has_value = False

            for shift in domain[nurse_id][day]:

                if is_consistent(
                    assignment,
                    domain,
                    nurse_id,
                    day,
                    shift
                ):

                    has_value = True

                    if shift in {'M', 'B'}:
                        possible_m += 1

                    if shift in {'A', 'B'}:
                        possible_a += 1

                    if shift == 'E':
                        possible_e += 1

                    if shift == 'B':
                        possible_b += 1

            if not has_value:
                return False

    remaining_m = m - morning_count[day]
    remaining_a = a - afternoon_count[day]
    remaining_e = e - evening_count[day]

    if remaining_m < 0 or remaining_a < 0 or remaining_e < 0:
        return False

    # Not enough possible nurses to satisfy remaining requirements
    if remaining_m > possible_m:
        return False

    if remaining_a > possible_a:
        return False

    if remaining_e > possible_e:
        return False

    # ====================================================================================================
    # CHANGED: ensure a surgical B is still possible
    # ====================================================================================================

    if days[day] == 'S':

        current_B = False

        for nurse_id in range(Ns):

            if assignment[nurse_id][day] == 'B':
                current_B = True
                break

        if not current_B and possible_b == 0:
            return False

    return True


# ====================================================================================================
# CHANGED: assign a shift and update all maintained counters
# ====================================================================================================

def assign_shift(assignment, nurse_id, day, shift):

    assignment[nurse_id][day] = shift

    if shift == 'M':

        morning_count[day] += 1
        shifts_worked[nurse_id] += 1

    elif shift == 'A':

        afternoon_count[day] += 1
        shifts_worked[nurse_id] += 1

    elif shift == 'E':

        evening_count[day] += 1
        shifts_worked[nurse_id] += 1

    elif shift == 'B':

        morning_count[day] += 1
        afternoon_count[day] += 1
        shifts_worked[nurse_id] += 2


# ====================================================================================================
# CHANGED: undo a shift and restore all maintained counters
# ====================================================================================================

def unassign_shift(assignment, nurse_id, day, shift):

    assignment[nurse_id][day] = 'XX'

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
        shifts_worked[nurse_id] -= 2


# Backtracking search algorithm
def backtrack(assignment, domain, day):

    if day == D:
        return assignment

    # Check whether all nurses for the current day are assigned
    all_assigned = True

    for nurse_id in range(N):

        if assignment[nurse_id][day] == 'XX':

            all_assigned = False
            break

    if all_assigned:

        if not check_day_constraints(assignment, day):
            return None

        return backtrack(
            assignment,
            domain,
            day + 1
        )

    # Select an unassigned nurse for the current day
    nurse_id, _ = select_unassigned_variable(
        assignment,
        domain,
        day
    )

    if nurse_id == -1:
        return None

    # Order domain values
    ordered_shifts = order_domain_values(
        assignment,
        domain,
        nurse_id,
        day
    )

    for shift in ordered_shifts:

        if is_consistent(
            assignment,
            domain,
            nurse_id,
            day,
            shift
        ):

            assign_shift(
                assignment,
                nurse_id,
                day,
                shift
            )

            # Forward checking
            if forward_check(
                assignment,
                domain,
                day
            ):

                result = backtrack(
                    assignment,
                    domain,
                    day
                )

                if result is not None:
                    return result

            # Undo assignment
            unassign_shift(
                assignment,
                nurse_id,
                day,
                shift
            )

    return None


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


# Final main function
def solve_part_a():

    result = backtrack(
        Assignment,
        Domain,
        0
    )

    if result is not None:

        print("Solution found:")

        for row in result:
            print(row)

        write_output(
            result,
            output_file
        )

    else:

        print("No solution exists.")

        write_output(
            None,
            output_file
        )


solve_part_a()