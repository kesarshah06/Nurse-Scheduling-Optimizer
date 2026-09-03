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

# ..........................precomputing boolean lookup tables to avoid repeated string indexing in the hot path.......................................................

is_surgical = [days[j] == 'S' for j in range(D)]                                          # is_surgical[day] replaces days[day] == 'S' checks everywhere

on_leave = [[leaves[i * D + j] == 'L' for j in range(D)] for i in range(N)]               # on_leave[nurse][day] replaces leaves[nurse*D+day] == 'L' checks everywhere

is_surgical_nurse = [i < Ns for i in range(N)]                                            # is_surgical_nurse[nurse] replaces nurse_id >= Ns checks everywhere

sole_surg_nurses = {}                                                                     # sole_surg_nurses[day] maps surgical days with exactly 1 available surgical nurse to that nurse_id
for j in range(D):
    if is_surgical[j]:
        avail = [i for i in range(Ns) if leaves[i * D + j] != 'L']
        if len(avail) == 1:
            sole_surg_nurses[j] = avail[0]

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

#..............................................initialize the shifts worked count for each nurse.................................................................................
shifts_worked = [0 for _ in range(N)]

b_count = [0 for _ in range(D)]

# ....................................consecutive_work[nurse] = number of consecutive working days up to but not including the current assignment.......................................................

consecutive_work = [0 for _ in range(N)]

# ....................................stack to restore consecutive_work in O(1) on remove_shift.......................................................

prev_consecutive = [[] for _ in range(N)]

#...............................................add_shift: update counters when a shift is assigned.......................................................................................
def add_shift(nurse_id, day, shift):

    Assignment[nurse_id][day] = shift

    # ....................................save current consecutive_work before modifying, so remove_shift can restore it in O(1).......................................................
    prev_consecutive[nurse_id].append(consecutive_work[nurse_id])

    if shift == 'M':                                                                      #increment the morning count for the day, increment the shifts worked for the nurse, and increment the consecutive work count for the nurse
        morning_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1

    elif shift == 'A':                                                                    #increment the afternoon count for the day, increment the shifts worked for the nurse, and increment the consecutive work count for the nurse
        afternoon_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1

    elif shift == 'E':                                                                    #increment the evening count for the day, increment the shifts worked for the nurse, and increment the consecutive work count for the nurse
        evening_count[day] += 1
        shifts_worked[nurse_id] += 1
        consecutive_work[nurse_id] += 1

    elif shift == 'B':                                                                    #increment the morning and afternoon counts for the day, increment the b_count for the day, increment the shifts worked for the nurse by 2, and increment the consecutive work count for the nurse
        morning_count[day] += 1
        afternoon_count[day] += 1
        b_count[day] += 1
        shifts_worked[nurse_id] += 2
        consecutive_work[nurse_id] += 1

    elif shift == 'R':                                                                   #if the shift is 'R', reset the consecutive work count for the nurse to 0
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

    consecutive_work[nurse_id] = prev_consecutive[nurse_id].pop()                         #restore the previous consecutive work count for the nurse from the stack, so that remove_shift can restore it in O(1)

#.......................................function to check if an assignment is consistent or not................................................................
def is_consistent(assignment, domain, nurse_id, day, shift):

    if shift not in domain[nurse_id][day]:                                                #if the shift is not in the domain of the nurse for the current day, return False
        return False

    if shift != 'R': 
        if shifts_worked[nurse_id] >= max_shifts:                                         # H7: every nurse works at most K shifts in total. If the nurse has already worked max_shifts, return False
            return False
        if shift == 'B' and shifts_worked[nurse_id] + 2 > max_shifts:                     # H7: every nurse works at most K shifts in total. If the nurse has already worked max_shifts - 1, return False
            return False
        if consecutive_work[nurse_id] >= 5:                                               # H5: every nurse works at most 5 consecutive days. If the nurse has already worked 5 consecutive days, return False
            return False

    prev_shift = assignment[nurse_id][day - 1] if day > 0 else 'XX'

    if shift in {'M', 'B'}:
        if morning_count[day] >= m:                                                       # H4: there are exactly m morning shifts, a afternoon shifts, and e evening shifts each day. If the morning count for the day is already m, return False
            return False
        if prev_shift in {'M', 'B', 'E'}:                                                 # H2/H6: no consecutive morning shifts
            return False

    if shift in {'A', 'B'}:                         
        if afternoon_count[day] >= a:
            return False

    if shift == 'E':
        if evening_count[day] >= e:
            return False

    if prev_shift == 'B' and shift in {'M', 'A'}:                                        # H3: no consecutive shifts of the same type, and no morning shift after a night shift.
        return False

    return True


#..................................................function to check if the daily constraints are satisfied.........................................................................
def check_day_constraints(assignment, day):                                           

    if morning_count[day] != m:                                                          # H4
        return False

    if afternoon_count[day] != a:
        return False

    if evening_count[day] != e:
        return False

    if is_surgical[day] and b_count[day] < 1:                                           # every surgical day has atleast one surgical nurse
        return False

    return True


#..............................................Selecting unassigned variable using MRV........................................................................
def select_unassigned_variable(assignment, domain, day):

    best_nurse_id = -1                                                                    # initializing best_nurse_id to -1, best_domain_size to infinity, best_day to -1
    best_domain_size = float('inf')                                                       # best_nurse will have the smallest domain size among all unassigned nurses for the current day.
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

            if domain_size == 0:                                                          # if some unassigned nurse has no valid value for current situation then this assignment immedietly fails
                return nurse_id, day, []

            if can_m:
                possible_m += 1

            if can_a:
                possible_a += 1

            if can_e:
                possible_e += 1

            if domain_size < best_domain_size:                                            # choosing smallest domain

                best_domain_size = domain_size
                best_nurse_id = nurse_id
                best_day = day
                best_consistent_shifts = consistent_shifts

            elif domain_size == best_domain_size:                                        # if domain sizes are equal, choose the nurse with the least shifts worked so far, and if still equal, choose the surgical nurse if the day is surgical and no surgical nurse has been assigned yet
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
def backtrack(assignment, domain, day):

    if day == D:                                                                          #if all days have been assigned, return the assignment as a solution
        return assignment

    # ....................................fast shortcut: if daily active shift quotas are fulfilled, batch assign 'R' to all remaining nurses and advance to day + 1.......................................................
    if (
        morning_count[day] == m
        and afternoon_count[day] == a
        and evening_count[day] == e
        and (not is_surgical[day] or b_count[day] >= 1)
    ):
        unassigned = [                                                                    # find all the unassigned nurses
            i for i in range(N) if assignment[i][day] == 'XX'
        ]

        if not unassigned:
            if not check_day_constraints(assignment, day):                               #if all nurses have been assigned for the current day, check if the daily constraints are satisfied. If not,
                return None
            return backtrack(assignment, domain, day + 1)                                #If any nurse's assignment is inconsistent, set valid to False and break the loop

        valid = True
        for nid in unassigned:                                                          # else if there are unassigned nurses, assign 'R' to all of them and check if the assignment is consistent for each nurse. 
            if not is_consistent(assignment, domain, nid, day, 'R'):
                valid = False
                break

        if not valid:
            return None

        for nid in unassigned:                                                         # for all unassigned nurses, assign 'R' to them 
            add_shift(nid, day, 'R')

        result = backtrack(assignment, domain, day + 1)

        if result is not None:                                                         # if after assigning R to all remaining n the assignment works then we found the sol
            return result

        for nid in unassigned:                                                         # else remove the whole assignment and backtrack
            remove_shift(nid, day, 'R')

        return None

    target_shift = None
    if is_surgical[day] and b_count[day] == 0:                                        # if surgical day and no surgical nurse has been assigned, then the next shift will be B
        target_shift = 'B'
    elif morning_count[day] < m:                                                      # else choose the first shift available 
        target_shift = 'M'
    elif afternoon_count[day] < a:
        target_shift = 'A'
    elif evening_count[day] < e:
        target_shift = 'E'

    if target_shift is not None:                      
        rem_req = (D - day) * (m + a + e) - (morning_count[day] + afternoon_count[day] + evening_count[day])   
        rem_avail = sum(max_shifts - shifts_worked[i] for i in range(N))               # rem_avail represents the total number of shifts that can still be assigned to all nurses, and rem_req represents the total number of shifts that still need to be assigned for the remaining days.

        for j in range(day, D):                                                        # the loop iterates over the remaining days and checks if there is a surgical day with no surgical nurse assigned. 
            if is_surgical[j] and b_count[j] == 0 and j in sole_surg_nurses:           # If so, it checks if the sole surgical nurse for that day has enough shifts left to work. 
                sole_nurse = sole_surg_nurses[j]
                if shifts_worked[sole_nurse] + 2 > max_shifts:                         # If not, it returns None, indicating that the assignment is not feasible.
                    return None

        rem_surg_days = sum(1 for j in range(day, D) if is_surgical[j] and b_count[j] == 0)
        avail_surg_budget = sum(2 * ((max_shifts - shifts_worked[i]) // 2) for i in range(Ns))
        if avail_surg_budget < 2 * rem_surg_days:
            return None

        if target_shift == 'B':                                                       # if the target shift is 'B', the candidates are all surgical nurses who are unassigned for the current day and for whom assigning 'B' is consistent with the current assignment.
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

        if target_shift == 'B':
            candidates.sort(key=lambda i: (shifts_worked[i], i))
        elif rem_surg_days > 0 and Ns <= 5:
            candidates.sort(key=lambda i: (is_surgical_nurse[i], shifts_worked[i], i))
        else:
            candidates.sort(key=lambda i: (shifts_worked[i], i))

        for cand in candidates:
            add_shift(cand, day, target_shift)
            result = backtrack(assignment, domain, day)
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

        return backtrack(assignment, domain, day + 1)                                     #if the daily constraints are satisfied, move on to the next day and continue the backtracking search

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
        ordered_shifts = order_domain_values(                                           #order the shifts in the domain of the selected nurse for the current day using the least constraining value heuristic, so that the shift with the least impact on other nurses' choices is tried first
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
                day
            )
            if result is not None:
                return result
            remove_shift(
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


#..................................................function to check problem feasibility upfront................................................................ me
def is_problem_feasible():
    if m > N or a > N or e > N or (m + a + e) > N:                                        # if any of the daily shift requirements exceed the total number of nurses, return False
        return False

    if D * (m + a + e) > N * max_shifts:                                                  # if the total number of shifts required over all days exceeds the total number of shifts that can be worked by all nurses, return False
        return False

    for j in range(D):                                                          
        avail_nurses = sum(1 for i in range(N) if leaves[i * D + j] != 'L')
        min_needed = (m + a + e - 1) if is_surgical[j] else (m + a + e)
        if avail_nurses < min_needed:                                                     # if the number of available nurses for any day is less than the minimum number of shifts required for that day,
            return False

        if is_surgical[j]:                                                                # if the day is surgical, check if there is at least one surgical nurse available for that day. If not, return False
            avail_surg = sum(1 for i in range(Ns) if leaves[i * D + j] != 'L')
            if avail_surg < 1:
                return False

    return True


#..................................................main function to solve part a.........................................................................
def solve_part_a():
    global backtrack_calls
    backtrack_calls = 0

    if not is_problem_feasible():
        print("No solution exists.")
        write_output(
            None,
            output_file
        )
        return

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