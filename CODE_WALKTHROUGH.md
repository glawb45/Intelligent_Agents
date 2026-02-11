# Code Walkthrough - Tennis Planner

## Quick Navigation

### For Your Video Explanation

When demonstrating the code in your video, here's what to highlight:

## 1. Domain Definition (`create_tennis_actions()`)

**Lines to focus on**: The action definitions

```python
# Example: HitCrosscourt action
actions.append({
    'name': f'HitCrosscourt({from_pos}, {target_side})',
    'preconditions': {
        f'At(Player, {from_pos})',
        'HasBall(Player)',
    },
    'add_list': {
        'HasBall(Opponent)',
        f'At(Opponent, Baseline{target_side})',
        f'CourtOpen({opposite_side})',
        'DeepShot'
    },
    'delete_list': {
        'HasBall(Player)',
        'ShortBall'
    }
})
```

**What to say**: 
"This shows how we represent actions in STRIPS. The crosscourt shot has preconditions (player must have ball and be at a position), add effects (opponent gets ball, court opens up), and delete effects (player loses ball)."

## 2. Core Planning Functions

### `is_applicable(state, action)`
**What it does**: Checks if an action can be executed in the current state
**Key line**: `return precond.issubset(state)`
**Explanation**: "We use set operations - an action is applicable if all preconditions are in the current state"

### `apply_action(state, action)`  
**What it does**: Executes an action to produce a new state
**Key line**: `return action['add_list'].union(state.difference(action['delete_list']))`
**Explanation**: "We remove the delete list from state, then add the add list - this is the core STRIPS state transition"

### `goal_satisfied(state, goal)`
**What it does**: Checks if we've reached the goal
**Key line**: `return goal.issubset(state)`
**Explanation**: "Goal is satisfied when all goal facts are true in the current state"

## 3. Search Algorithms

### Forward Search (BFS)
```python
def forward_search(initial_state, goal, actions):
    queue = []
    visited = {frozenset(initial_state)}
    queue.append((initial_state, []))
    
    while len(queue) != 0:
        state, plan = queue.pop(0)  # BFS: pop from front
        explored += 1
        
        if goal_satisfied(state, goal):
            return (plan, explored)
        
        for action in get_applicable_actions(state, actions):
            new_state = apply_action(state, action)
            if frozenset(new_state) not in visited:
                queue.append((new_state, plan + [action['name']]))
```

**Explanation**: "Classic breadth-first search. We explore states level by level using a queue. We track visited states to avoid cycles."

### A* Heuristic Search
```python
def heuristic_search(initial_state, goal, actions):
    h_initial = goal_count_heuristic(initial_state, goal)
    pq = []
    heapq.heappush(pq, (h_initial, counter, 0, initial_state, []))
    
    while len(pq) != 0:
        item = heapq.heappop(pq)  # Always get lowest f-score
        g = item[2]  # Cost so far
        state = item[3]
        plan = item[4]
        
        if goal_satisfied(state, goal):
            return (plan, explored)
        
        for action in get_applicable_actions(state, actions):
            new_state = apply_action(state, action)
            h = goal_count_heuristic(new_state, goal)
            new_f = (g + 1) + h  # f = g + h
            heapq.heappush(pq, (new_f, counter, g+1, new_state, updated_plan))
```

**Explanation**: "A* uses a priority queue ordered by f = g + h, where g is steps taken and h estimates remaining steps. The goal-count heuristic counts unsatisfied goals."

## 4. Example Problem Instance

```python
def problem_instance_2():
    """
    Problem 2: "Approach and Volley"
    Hit deep, approach net, receive, finish with volley.
    """
    initial_state = {
        "At(Player, BaselineCenter)",
        "At(Opponent, BaselineCenter)",
        "HasBall(Player)"
    }
    
    goal = {
        "PointWon",
        "AtNet(Player)"  # Must finish at net
    }
```

**Explanation**: "This shows a real tennis tactic - approach and volley. The goal requires both winning the point AND being at the net, forcing the planner to find the right sequence."

## 5. Results to Highlight

**Problem 3** has the best A* efficiency (65% fewer states):
```
✓ BFS found plan with 3 steps (explored 20 states)
✓ A* found plan with 3 steps (explored 7 states)
A* Efficiency: Explored 65.0% fewer states than BFS
```

**Why?** The goal-count heuristic guides A* directly toward the lob action which satisfies multiple goals at once.

## Video Script Suggestions

### Opening (30 seconds)
"I chose tennis point construction because it's a perfect planning domain - you can't just hit winners immediately, you need to set them up, just like in real tennis."

### Domain Explanation (1 minute)
Show tennis_planning_domain.md
"Here's my STRIPS formalization. I have predicates for positions, ball possession, and court state. Actions include crosscourt shots, approaching the net, volleys, lobs, and drop shots."

### Code Demo (2 minutes)
Show tennis_planner.py running
"The planner finds optimal shot sequences. Watch how Problem 2 shows approach-and-volley: crosscourt, approach net, receive return, then volley winner. That's exactly how pros play."

### Results (1 minute)
"A* consistently beats BFS. In Problem 3, it explored 65% fewer states because the heuristic guided it directly to the lob action. This shows the power of informed search."

## Common Questions

**Q: Why is tennis better than blocks world?**
A: "Tennis has real strategy - actions depend on positions, you need setup shots before winners, and it models actual professional play."

**Q: How does the heuristic work?**
A: "Goal-count just counts unsatisfied goals. Simple but effective - it always underestimates (admissible) so A* finds optimal plans."

**Q: What if opponent has the ball?**
A: "The ReceiveReturn action models getting the ball back. Every rally involves this back-and-forth."

---

Good luck with your video! The domain is solid and the code works great.
