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



# ....................................changed the recursion limit as to account for large N*D instances.......................................................
sys.setrecursionlimit(max(10000, N * D + 100))

# ....................................precompute boolean lookup tables to avoid repeated string indexing in the hot path.......................................................
# is_surgical[day] replaces days[day] == 'S' checks everywhere
is_surgical = [days[j] == 'S' for j in range(D)]

# on_leave[nurse][day] replaces leaves[nurse*D+day] == 'L' checks everywhere
on_leave = [
    [leaves[i * D + j] == 'L' for j in range(D)]
    for i in range(N)
]

# is_surgical_nurse[nurse] replaces nurse_id >= Ns checks everywhere
is_surgical_nurse = [i < Ns for i in range(N)]

#..................................................initialize the domain and assignment matrices.................................................................................
Domain = []

for i in range(N):                                                                         #domain is a 3D vector of size N*D where each element is a set of possible shifts for that nurse on that day

    Domain.append([])

    if i < Ns:                                                                             #first Ns nurses are surgical nurses, the rest are general nurses

        for j in range(D):
            if days[j] == 'S':
                Domain[i].append({'M', 'A', 'E', 'R', 'B'})                                #for surgical nurses on surgical days, the possible shifts are M, A, E, R, B
            else:
                Domain[i].append({'M', 'A', 'E', 'R'})                                     #for surgical nurses on general days, the possible shifts are M, A, E, R

    else:

        for j in range(D):
            Domain[i].append({'M', 'A', 'E', 'R'})                                         #for general nurses on any day, the possible shifts are M, A, E, R

#...............................................leave days only have R in their Domain.......................................................
for i in range(N):

    for j in range(D):

        if leaves[i * D + j] == 'L':
            Domain[i][j] = {'R'}



#..................................................initialize the assignment matrix.................................................................................    
Assignment = [['XX' for j in range(D)] for i in range(N)]

#..................................................initialize the daily shift counts.................................................................................
morning_count = [0 for _ in range(D)]
afternoon_count = [0 for _ in range(D)]
evening_count = [0 for _ in range(D)]

#..................................................initialize the shifts worked count for each nurse.................................................................................
shifts_worked = [0 for _ in range(N)]

b_count = [0 for _ in range(D)]

# ....................................cache: consecutive_work[nurse] = number of consecutive working days up to but not including the current assignment.......................................................
# Tracks how many consecutive working days each nurse currently has, used for H5 check in O(1).
consecutive_work = [0 for _ in range(N)]

# ....................................stack to restore consecutive_work in O(1) on remove_shift.......................................................
# prev_consecutive[nurse] stores the consecutive_work value before each add_shift, so remove_shift can pop it back instantly.
prev_consecutive = [[] for _ in range(N)]

#...............................................add_shift: update counters when a shift is assigned.......................................................................................
def add_shift(nurse_id, day, shift):

    Assignment[nurse_id][day] = shift

    # ....................................save current consecutive_work before modifying, so remove_shift can restore it in O(1).......................................................
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

#...............................................remove_shift: update counters when a shift is unassigned.......................................................................................
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

    # ....................................restore consecutive_work in O(1) using the saved stack instead of an O(D) backward scan.......................................................
    consecutive_work[nurse_id] = prev_consecutive[nurse_id].pop()

#.......................................function to check if an assignment is consistent or not................................................................
def is_consistent(assignment, domain, nurse_id, day, shift):

    if shift not in domain[nurse_id][day]:                                                 #H1 : if the shift is not in the domain of the nurse for that day, return False
        return False

    
    if (
        morning_count[day] == m
        and afternoon_count[day] == a
        and evening_count[day] == e
        and shift != 'R'
    ):
        return False

    if shift in {'M', 'B'} and day > 0:                                                    #H2 : no consecutive morning shifts
        if assignment[nurse_id][day - 1] in {'M', 'B'}:
            return False

    if shift in {'M', 'B'} and day > 0:                                                    #H3 : no morning shift after evening shift
        if assignment[nurse_id][day - 1] == 'E':
            return False

    if shift in {'M', 'B'}:                                                                #H4 : for exact m morning shifts
        if morning_count[day] + 1 > m:
            return False

    if shift in {'A', 'B'}:                                                                #H4 : for exact a afternoon shifts
        if afternoon_count[day] + 1 > a:
            return False

    if shift == 'E':                                                                       #H4 : for exact e evening shifts
        if evening_count[day] + 1 > e:
            return False

    # ....................................H5 check using cached consecutive_work counter (O(1) instead of O(D)).......................................................
    if shift != 'R' and consecutive_work[nurse_id] >= 5:                                   #H5 : no more than 5 consecutive working days
        return False

    if day > 0 and assignment[nurse_id][day - 1] == 'B':                                    #H6 : no M/A shift after a B shift

        if shift == 'M' or shift == 'A':
            return False

    if shift == 'B':                                                                       #H7 : every nurse works at most max_shifts shifts in total

        if shifts_worked[nurse_id] + 2 > max_shifts:
            return False

    elif shift in {'M', 'A', 'E'}:

        if shifts_worked[nurse_id] + 1 > max_shifts:
            return False

    # ....................................use precomputed boolean tables instead of string indexing and arithmetic.......................................................
    if on_leave[nurse_id][day] and shift != 'R':                                           #H8 : if the nurse is on leave, they can only be assigned R
        return False

    if shift == 'B' and (not is_surgical_nurse[nurse_id] or not is_surgical[day]):        #H9 : only surgical nurses can work B shifts on surgical days
        return False

    return True                                                                            #all constraints are satisfied, return True


#..................................................function to check if the daily constraints are satisfied.........................................................................
def check_day_constraints(assignment, day):

    if morning_count[day] != m:                                                            #Check if the number of shifts assigned for the day matches the required counts
        return False

    if afternoon_count[day] != a:
        return False

    if evening_count[day] != e:
        return False

    if is_surgical[day]:                                                                   #Check if there is at least one surgical nurse assigned to a B shift on surgical days

        if b_count[day] < 1:
            return False

    return True                                                                           #all daily constraints are satisfied, return True


# ....................................merged MRV + forward_check into one pass to avoid iterating over all nurses twice per backtrack node.......................................................
# Returns (best_nurse_id, best_day, is_feasible, consistent_shifts_for_best_nurse).
# is_feasible=False means forward check already failed, so we can prune immediately.
# consistent_shifts_for_best_nurse is passed directly to order_domain_values, avoiding a third redundant is_consistent scan.
def select_and_check(assignment, domain, day):

    best_nurse_id = -1                                                                     #current intialization of best nurse id, best domain size and best day to be assigned
    best_domain_size = float('inf')
    best_consistent_shifts = []

    unassigned_nurses = 0

    possible_m = 0
    possible_a = 0
    possible_e = 0

    # ....................................track surgical nurses who could still do B, for H7 check.......................................................
    possible_b = False

    surgical_day = is_surgical[day]                                                        # ....................................cache the surgical day boolean once per call.......................................................

    for nurse_id in range(N):

        if assignment[nurse_id][day] == 'XX':                                              #if the nurse is unassigned for the day, calculate the domain size for that nurse on that day

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

                    if shift == 'M' or shift == 'B':                                       #if the shift is M or B, then the nurse can work a morning shift, so set can_m to True
                        can_m = True

                    if shift == 'A' or shift == 'B':                                       #if the shift is A or B, then the nurse can work an afternoon shift, so set can_a to True
                        can_a = True

                    if shift == 'E':                                                       #if the shift is E, then the nurse can work an evening shift, so set can_e to True
                        can_e = True

                    # ....................................check B feasibility inline to avoid a separate pass for H7.......................................................
                    if shift == 'B' and surgical_day and b_count[day] == 0:
                        possible_b = True

            domain_size = len(consistent_shifts)

            if domain_size == 0:                                                           #if the nurse has no valid shifts in their domain for the current day, then return False immediately
                return nurse_id, day, False, []

            if can_m:
                possible_m += 1

            if can_a:
                possible_a += 1

            if can_e:
                possible_e += 1

            if domain_size < best_domain_size:                                            #if the domain size is less than the best domain size, update the best nurse id, best domain size and best day to be assigned

                best_domain_size = domain_size
                best_nurse_id = nurse_id
                best_consistent_shifts = consistent_shifts

    # ....................................forward check using counts accumulated in the same loop above.......................................................
    remaining_m = m - morning_count[day]                                                  #calculate the remaining number of morning, afternoon, and evening shifts that need to be assigned for the current day based on the required counts and the current counts
    remaining_a = a - afternoon_count[day]
    remaining_e = e - evening_count[day]

    if possible_m < remaining_m:                                                          #if the number of unassigned nurses who can work a morning shift is less than the remaining number of morning shifts that need to be assigned, then return False, as this means that it is not possible to assign enough morning shifts for the current day
        return best_nurse_id, day, False, []

    if possible_a < remaining_a:
        return best_nurse_id, day, False, []

    if possible_e < remaining_e:
        return best_nurse_id, day, False, []

    # ....................................H7: use the possible_b flag computed inline above instead of a separate loop.......................................................
    if surgical_day and b_count[day] == 0 and not possible_b:
        return best_nurse_id, day, False, []

    if remaining_m + remaining_a + remaining_e > 2 * unassigned_nurses:                   #if the total number of remaining shifts that need to be assigned for the current day is greater than twice the number of unassigned nurses for that day, then return False, as this means that it is not possible to assign enough shifts for the current day
        return best_nurse_id, day, False, []

    return best_nurse_id, day, True, best_consistent_shifts                               #return the best nurse id and best day to be assigned


#..............................................Selecting unassigned variable using MRV........................................................................................
def select_unassigned_variable(assignment, domain, day):

    best_nurse_id = -1                                                                     #current intialization of best nurse id, best domain size and best day to be assigned
    best_domain_size = float('inf')
    best_day = -1

    for nurse_id in range(N):

        if assignment[nurse_id][day] == 'XX':                                              #if the nurse is unassigned for the day, calculate the domain size for that nurse on that day

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

            if domain_size == 0:
                return nurse_id, day

            if domain_size < best_domain_size:                                            #if the domain size is less than the best domain size, update the best nurse id, best domain size and best day to be assigned

                best_domain_size = domain_size
                best_nurse_id = nurse_id
                best_day = day

    return best_nurse_id, best_day                                                        #return the best nurse id and best day to be assigned


#..................................................Ordering domain values.........................................................................................
def order_domain_values(assignment, domain, nurse_id, day, consistent_shifts):

    # ....................................consistent_shifts passed in directly from select_and_check; no redundant is_consistent scan needed.......................................................

    # ....................................if only one or zero consistent shifts, skip LCV scoring entirely.......................................................
    if len(consistent_shifts) <= 1:
        return consistent_shifts

    value_scores = {}                                                                     #dictionary to store the scores for each shift based on the number of remaining choices for other nurses

    # ....................................precompute which nurses are unassigned on this day once.......................................................
    unassigned_others = [
        other_id for other_id in range(N)
        if other_id != nurse_id and assignment[other_id][day] == 'XX'
    ]

    # ....................................if no other nurses left to assign today, all shifts are equally good; skip LCV scoring.......................................................
    if not unassigned_others:
        return consistent_shifts

    for shift in consistent_shifts:                                                       #for each consistent shift, check the remaining choices for other nurses

        add_shift(                                                                        #incrementally assign the shift to the nurse for the day to check the remaining choices for other nurses
            nurse_id,
            day,
            shift
        )

        total_remaining_choices = 0                                                       #variable to store the total remaining choices for other nurses on the same day after assigning the shift to the selected nurse
        valid = True

        for other_nurse_id in unassigned_others:                                          # ....................................iterate only over pre-computed unassigned nurses.......................................................

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

    ordered_shifts = sorted(                                                               #sort the shifts in the domain of the selected nurse for the current day based on their scores in descending order, so that the shift with the least impact on other nurses' choices is tried first
        consistent_shifts,
        key=lambda shift: value_scores.get(shift, -1),
        reverse=True
    )

    return ordered_shifts

#..........................................................forward_check.........................................................
def forward_check(assignment, domain, day):

    unassigned_nurses = 0

    possible_m = 0
    possible_a = 0
    possible_e = 0

    # ....................................track surgical nurses who could still do B, for H7 check.......................................................
    possible_b = False

    is_surgical_day = is_surgical[day]                                                     # ....................................use precomputed boolean instead of string indexing.......................................................

    for other_nurse_id in range(N):

        if assignment[other_nurse_id][day] == 'XX':

            unassigned_nurses += 1                                                         #count the number of unassigned nurses on the current day

            has_value = False
            can_m = False
            can_a = False
            can_e = False

            for shift in domain[other_nurse_id][day]:                                      #for each shift in the domain of the unassigned nurse for the current day, check if the assignment is consistent, if so, update the possible shifts for that nurse

                if is_consistent(
                    assignment,
                    domain,
                    other_nurse_id,
                    day,
                    shift
                ):

                    has_value = True

                    if shift == 'M' or shift == 'B':                                       #if the shift is M or B, then the nurse can work a morning shift, so set can_m to True
                        can_m = True

                    if shift == 'A' or shift == 'B':                                       #if the shift is A or B, then the nurse can work an afternoon shift, so set can_a to True
                        can_a = True

                    if shift == 'E':                                                       #if the shift is E, then the nurse can work an evening shift, so set can_e to True
                        can_e = True

                    # ....................................check B feasibility inline to avoid a separate pass for H7.......................................................
                    if shift == 'B' and is_surgical_day and b_count[day] == 0:
                        possible_b = True

            if not has_value:                                                              #if the nurse has no valid shifts in their domain for the current day, then return False, as this means that the assignment is not consistent and cannot be completed                 
                return False

            if can_m:
                possible_m += 1

            if can_a:
                possible_a += 1

            if can_e:
                possible_e += 1

    remaining_m = m - morning_count[day]                                                  #calculate the remaining number of morning, afternoon, and evening shifts that need to be assigned for the current day based on the required counts and the current counts
    remaining_a = a - afternoon_count[day]
    remaining_e = e - evening_count[day]

    if possible_m < remaining_m:                                                          #if the number of unassigned nurses who can work a morning shift is less than the remaining number of morning shifts that need to be assigned, then return False, as this means that it is not possible to assign enough morning shifts for the current day
        return False

    if possible_a < remaining_a:
        return False

    if possible_e < remaining_e:
        return False

    # ....................................H7: use the possible_b flag computed inline above instead of a separate loop.......................................................
    if is_surgical_day and b_count[day] == 0 and not possible_b:
        return False

    if remaining_m + remaining_a + remaining_e > 2 * unassigned_nurses:                   #if the total number of remaining shifts that need to be assigned for the current day is greater than twice the number of unassigned nurses for that day, then return False, as this means that it is not possible to assign enough shifts for the current day
        return False

    return True


# .................................................Backtracking search algorithm.................................................
def backtrack(assignment, domain, day):

    if day == D:                                                                          #if all days have been assigned, return the assignment as a solution
        return assignment

    all_assigned = True

    for nurse_id in range(N):

        if assignment[nurse_id][day] == 'XX':                                             #if there is at least one nurse who is unassigned for the current day, set all_assigned to False and break the loop
            all_assigned = False
            break

    if all_assigned:

        if not check_day_constraints(assignment, day):                                    #if all nurses have been assigned for the current day, check if the daily constraints are satisfied. If not, return None, as this means that the assignment is not consistent and cannot be completed
            return None

        return backtrack(assignment, domain, day + 1)                                     #if the daily constraints are satisfied, move on to the next day and continue the backtracking search

    # ....................................merged MRV + forward_check into one single pass over nurses, halving the O(N*S) scans per node.......................................................
    nurse_id, _, feasible, consistent_shifts = select_and_check(
        assignment,
        domain,
        day
    )

    if nurse_id == -1 or not feasible:                                                    #if no valid nurse was found or the day is already infeasible, return None
        return None

    ordered_shifts = order_domain_values(                                                  #order the shifts in the domain of the selected nurse for the current day using the least constraining value heuristic, so that the shift with the least impact on other nurses' choices is tried first
        assignment,
        domain,
        nurse_id,
        day,
        consistent_shifts                                                                  # ....................................pass pre-computed consistent shifts directly, avoiding a third is_consistent scan.......................................................
    )

    for shift in ordered_shifts:                                                           #for each shift in the ordered list of shifts for the selected nurse for the current day, check if the assignment is consistent. If so, assign the shift to the nurse for the current day and continue the backtracking search. If not, unassign the shift and try the next shift in the ordered list

        # ....................................consistency already guaranteed by select_and_check pre-filter; skip redundant check.......................................................
        add_shift(                                                                        #incrementally assign the shift to the nurse for the current day to check if the assignment is consistent and can be completed
            nurse_id,
            day,
            shift
        )

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

        remove_shift(                                                                     #decrementally unassign the shift from the nurse for the current day to restore the assignment state for the next iteration      
            nurse_id,
            day,
            shift
        )

    return None

#..................................................function to write the output to a JSON file.........................................................................
def write_output(solution, output_file):

    import json

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


#..................................................main function to solve part a.........................................................................
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

#..................................................call the main function to solve part a.........................................................................
solve_part_a()