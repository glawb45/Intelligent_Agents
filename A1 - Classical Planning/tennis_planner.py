""" 
Tennis Point Construction Planning Domain
"""

import heapq

# ============================================================
# STEP 1: Copy your implementations from Challenge 1 & 2 below
# (or implement them here if you haven't done the earlier challenges)
# ============================================================

def is_applicable(state, action):
    """
    Check if action's preconditions are satisfied.
    Copy your implementation from Challenge 1!
    """
    pre = action['preconditions']
    return pre.issubset(state)


def apply_action(state, action):
    """
    Apply action to get new state.
    Copy your implementation from Challenge 1!
    """
    return action['add_list'].union(state.difference(action['delete_list']))


# ============================================================
# STEP 2: Implement the new functions for forward search
# ============================================================

def goal_satisfied(state, goal):
    """
    Check if the goal is satisfied in the current state.
    
    Args:
        state: Current state (set of fluents)
        goal: Set of fluents that must ALL be true
    
    Returns:
        bool: True if all goal fluents are in state
    
    Example:
        state = {"On(A,B)", "OnTable(B)", "Clear(A)"}
        goal = {"On(A,B)"}
        goal_satisfied(state, goal)  # Returns True
    """
    return goal.issubset(state)


def get_applicable_actions(state, actions):
    """
    Get all actions that can be applied in the current state.
    
    Args:
        state: Current state (set of fluents)
        actions: List of all action dictionaries
    
    Returns:
        list: Actions whose preconditions are satisfied
    
    Example:
        # If state has ArmEmpty, Clear(A), OnTable(A), Clear(B), OnTable(B)
        # Then Pick-up(A) and Pick-up(B) are applicable
    """
    app_actions = []

    for action in actions:
        if is_applicable(state, action):
            app_actions.append(action)

    return app_actions

# ============================================================
# STEP 2: Implement the goal-count heuristic
# ============================================================

def goal_count_heuristic(state, goal):
    """
    Estimate distance to goal by counting unsatisfied goal facts.
    
    Args:
        state: Current state (set of fluents)
        goal: Goal condition (set of fluents)
    
    Returns:
        int: Number of goal facts NOT in the current state
    
    Example:
        state = {"On(A,B)", "OnTable(B)"}
        goal = {"On(A,B)", "On(B,C)", "OnTable(C)"}
        # On(A,B) is satisfied, but On(B,C) and OnTable(C) are not
        # Heuristic value = 2
    """

    return len(goal - state)


# ============================================================
# STEP 3: Copy forward_search from Challenge 2 (for comparison)
# ============================================================

def forward_search(initial_state, goal, actions):
    """
    BFS forward search - copy from Challenge 2 for comparison!
    """
    
    explored = 0
    q = []

    visited = {frozenset(initial_state)}
    q.append((initial_state, []))

    while len(q) != 0:
        state, plan = q.pop(0)
        explored += 1

        if goal_satisfied(state, goal):
            return plan, explored

        app_actions = get_applicable_actions(state, actions)

        for action in app_actions:
            new_state = apply_action(state, action)
            v_new_state = frozenset(new_state)
            if v_new_state not in visited:
                visited.add(v_new_state)
                q.append((new_state, plan + [action['name']]))

    return None, explored


# ============================================================
# STEP 4: Implement the heuristic search algorithm
# ============================================================

def heuristic_search(initial_state, goal, actions):
    """
    Find a plan using A*-like search with goal-count heuristic.
    
    Args:
        initial_state: Starting state (set of fluents)
        goal: Goal condition (set of fluents)
        actions: List of all possible action dictionaries
    
    Returns:
        tuple: (plan, explored_count)
    
    Algorithm:
        1. Initialize priority queue with (f, counter, g, state, plan)
           where f = g + h, g = 0, h = heuristic(initial_state)
        2. Initialize visited set
        3. While queue not empty:
           a. Pop state with lowest f value
           b. Skip if already visited (we might add duplicates)
           c. Mark as visited, increment explored
           d. If goal satisfied: return plan
           e. For each applicable action:
              - Compute successor state
              - If not visited: compute f = g+1 + h(successor), add to queue
        4. Return None if no plan found
    
    Note: We use a counter as tie-breaker since sets aren't comparable.
    """
    explored = 0
    counter = 0  # Tie-breaker for priority queue
    
    h_initial = goal_count_heuristic(initial_state, goal)
  
    pq = []
    heapq.heappush(pq, (h_initial, counter, 0, initial_state, []))
    counter += 1
    
    visited = set()


    while len(pq) != 0:
        itemset = heapq.heappop(pq)
        f = itemset[0]
        _ = itemset[1]
        g = itemset[2]
        state = itemset[3]
        plan = itemset[4]

        new_state = frozenset(state)

        if new_state not in visited:
            visited.add(new_state)
            explored += 1

            if goal_satisfied(state, goal):
                return (plan, explored)

            for action in get_applicable_actions(state, actions):
                v_new_state = apply_action(state, action)
                if frozenset(v_new_state) not in visited:
                    h = goal_count_heuristic(v_new_state, goal)
                    new_f = (g + 1) + h
                    heapq.heappush(pq, (new_f, counter, g+1, v_new_state, plan + [action['name']]))
                    counter += 1

    return None, explored  # No plan found


# ============================================================
# Tennis Implementation
# ============================================================

def create_tennis_actions():
    actions = []

    # Court positions
    pos = ['BaslineLeft', 'BaselineCenter', 'BaselineRight']
    sides = ['Left', 'Right']

    # Action 1: Cross court

    for from_pos in pos:
        for target in sides:
            # Critical thinking for tennis
            # A) Tire out opponent if on opposite side
            opp_side = "Right" if target == "Left" else "Right"

            add_effects = {
                "HasBall(Opponent)",
                f"At(Opponent, Baseline{target})",
                f"CourtOpen({opp_side})"
                "DeepShot"
            }

            # Opponent off-balance
            actions.append({
                "name": f"Crosscourt({from_pos}, {target})",
                "preconditions": {
                    f"At(Player, {from_pos})",
                    "HasBall(Player)"
                },
                "add_list": add_effects,
                "delete_list": {
                    "HasBall(Player)",
                    "ShortBall"
                }
            })

            # Off-balance when opponent runs far
            opp_opposite = "Right" if target == "Left" else "Left"
            actions.append({
                "name": f"WideAngle({from_pos}, {target})",
                "preconditions": {
                    f"At(Player, {from_pos})",
                    "HasBall(Player)",
                    f"At(Opponent, Baseline{opp_opposite})"
                },
                "add_list": add_effects | {"OpponentOffBalance"},
                "delete_list": {
                    "HasBall(Player)",
                    "ShortBall"
                }
            })

    # Action 2: Down the line

    for from_pos in pos:
        for target in sides:
            actions.append({
                "name": f"DownTheLine({from_pos}, {target})",
                "preconditions": {
                    f"At(Player, {from_pos})",
                    "HasBall(Player)",
                    f"CourtOpen({target})"
                },
                "add_list": {"PointWon"},
                "delete_list": {
                    "HasBall(Player)",
                    f"CourtOpen({target})"
                }

            })

    # Action 3: Approach Net

    actions.append({
        "name": "ApproachNet()",
        "preconditions": {
            'HasBall(Opponent)',
            'DeepShot'
        },
        "add_list": {
            "AtNet(Player)",
            "At(Player, NetCenter)"
        },
        "delete_list": {
            "At(Player, BaselineCenter)",
            "At(Player, BaselineLeft)",
            "At(Player, BaselineRight)",
        }
    })

    # Action 4: Volley

    for target in sides:
        actions.append({
            "name": f"Volley({target})",
            "preconditions": {
                'AtNet(Player)',
                'HasBall(Player)',
                f'CourtOpen({target})'
            },
            "add_list": {
                "PointWon"
            },
            "delete_list": {
                'HasBall(Player)',
                f'CourtOpen({target})'
            }
    })
        
    # Action 5: Drop Shot (conditional based on opponent position)
    
    for from_pos in pos:
        actions.append({
            "name": f"DropShot({from_pos})",
            "preconditions": {
                f"At(Player, {from_pos})",
                'HasBall(Player)',
                "OpponentOffBalance" # Only works if opponent already off balance
            },
            "add_list": {
                "ShortBall",
                "PointWon"
            },
            "delete_list": {
                'HasBall(Player)',
                "DeepShot"
            }
        })

    # Action 6: Lob

    for from_pos in pos:
        actions.append({
            "name": f"Lob({from_pos})",
            "preconditions": {
                f"At(Player, {from_pos})",
                'HasBall(Player)',
                "AtNet(Opponent)"
            },
            "add_list": {
                "HasBall(Opponent)",
                "At(Opponent, BaselineCenter)",
                "CourtOpen(Left)",
                "CourtOpen(Right)",
                "DeepShot"
            },
            "delete_list": {
                'HasBall(Player)',
                "AtNet(Opponent)",
                "At(Opponent, NetCenter)" # remove opponent from net position
            }
        })

    # Action 7: Receive Return

    actions.append({
        "name": "ReceiveReturn()",
        "preconditions": {"HasBall(Opponent)"},
        "add_list": {"HasBall(Player)"},
        "delete_list": {"HasBall(Opponent)"}
    })

    return actions
    

# ============================================================
# Problem Instances
# ============================================================

def DTL_win():
    """
    Problem 1: "Basic Rally to Winner"
    Objective: Move opponent side to side to create open, finish with 
               down-the-line winner
    """

    initial_state = {
        "At(Player BaselineCenter)",
        "At(Opponent, BaselineLeft)",
        "HasBall(Player)"
    }

    goal = {
        "PointWon"
    }

    return initial_state, goal

def Approach_Volley():
    """
    Problem 2: "Approach and Volley"
    Objective: Hit deep, approach net, receive, finish with volley
    """

    initial_state = {
        "At(Player BaselineCenter)",
        "At(Opponent, BaselineCenter)",
        "HasBall(Player)"
    }

    goal = {
        "PointWon",
        "AtNet(Player)"
    }

    return initial_state, goal

def Lob_Player():
    """
    Problem 3: "Lob over Net Player"
    Objective: Opponent at net blocking w/ both sides - lob over them
    """

    initial_state = {
        "At(Player, BaselineCenter)",
        "At(Opponent, BaselineCenter)",
        "HasBall(Player)",
        "AtNet(Opponent)"
    }

    goal = {
        "PointWon",
        "At(Opponent, BaselineCenter)" # opponent pushed back from net to baseline
    }

    return initial_state, goal

def Off_Balance_Dropshot():
    """
    Problem 4: "Run opponent wide, then dropshot"
    Objective: Make Opponent run to create off-balance, then drop shot
    """

    initial_state = {
        "At(Player, BaselineCenter)",
        "At(Opponent, BaselineLeft)",
        "HasBall(Player)"
    }

    goal = {
        "PointWon",
        "ShortBall"
    }

    return initial_state, goal

# ============================================================
# Run planner
# ============================================================

def main():
    actions = create_tennis_actions()
    print(f"Domain initialized with {len(actions)} ground actions")
    print()

    # Test problems
    problems = [("Problem 1: Rally to Down-the-line Winner", DTL_win()),
                ("Problem 2: Approach and Volley", Approach_Volley()),
                ("Problem 3: Lob over Net Player", Lob_Player()),
                ("Problem 4: Run Wide, Drop Shot", Off_Balance_Dropshot())
    ]

    for prob, (initial_state, goal) in problems:
        print(prob)
        print()

        print("Initial State:")
        for fluent in sorted(initial_state):
            print(f" - {fluent}")
            print()

        print("Goal:")
        for fluent in sorted(goal):
            print(f" - {fluent}")
            print()

        # Run BFS
        print("BFS Running...")
        bfs_plan, bfs_explored = forward_search(initial_state, goal, actions)

        if bfs_plan:
            print(f"BFS found plan with {len(bfs_plan)} steps (explored {bfs_explored} states)")
            print(" Plan:")

            for i, action_name in enumerate(bfs_plan, 1):
                print(f"    {i}. {action_name}")
        else:
            print("BFS found NO PLAN (explored {bfs_explored} states)")
        print()

        # Run A* search
        print("A* Running...")
        astar_plan, astar_explored = forward_search(initial_state, goal, actions)

        if bfs_plan:
            print(f"A* found plan with {len(astar_plan)} steps (explored {astar_explored} states)")
            print(" Plan:")

            for i, action_name in enumerate(bfs_plan, 1):
                print(f"    {i}. {action_name}")
        else:
            print("A* found NO PLAN (explored {astar_explored} states)")
        print()

        # Compare efficiency
        if bfs_plan and astar_plan:
            eff = (1 - astar_explored / bfs_explored) * 100
            print(f"A* Efficiency: Explored {eff:.1f}% fewer states than BFS")
        
        print()

if __name__ == "__main__":
    main()
