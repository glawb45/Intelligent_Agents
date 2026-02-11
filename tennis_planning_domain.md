# Tennis Point Construction Planning Domain

## Part 1: Domain Selection & Description

### Real-World Scenario

This domain models **tennis point construction strategy** - the art of planning a sequence of shots to win a point in tennis. Professional tennis players don't just hit random shots; they construct points strategically by moving their opponent around the court, creating openings, and then executing winning shots.

### Entities/Objects in the Domain

1. **Players**: 
   - Player (you)
   - Opponent

2. **Court Positions**:
   - BaselineLeft (back left of court)
   - BaselineCenter (back center of court)
   - BaselineRight (back right of court)
   - NetLeft (front left, near net)
   - NetCenter (front center, near net)
   - NetRight (front right, near net)

3. **Shot Types**:
   - Groundstroke (baseline rally shot)
   - GroundstrokeCrosscourt (diagonal shot)
   - GroundstrokeDownLine (straight shot along sideline)
   - DropShot (short shot that barely clears net)
   - Lob (high arcing shot)
   - Volley (shot hit before ball bounces)
   - Smash (overhead winner)

4. **Court State**:
   - Ball possession
   - Player positions
   - Court openings (which side is vulnerable)

### What the Agent is Trying to Accomplish

The tennis player (agent) is trying to **win the point** by:
- Moving the opponent out of position
- Creating open court space
- Executing a shot the opponent cannot return
- Forcing an error from the opponent

A successful plan might involve: hitting crosscourt to move opponent wide → approaching the net → hitting a volley to the open court.

### Why Planning is Needed

**Why can't a simple reflex agent do it?**

A reflex agent that just "hits the ball back" or always "tries to hit a winner" would fail because:

1. **Sequential dependencies**: You can't effectively hit a down-the-line winner if your opponent is already positioned there. You need to first move them away (setup shot), THEN hit to the open court (finishing shot).

2. **Position constraints**: You can't hit a volley unless you're at the net. You can't approach the net unless you've hit a deep shot that gives you time.

3. **Court geometry**: The effectiveness of shots depends on both player positions. A crosscourt shot only creates an opening if the opponent is on the opposite side.

4. **State transitions**: Each shot changes the state (positions, ball location, court openings) in ways that enable or disable future actions. Planning is needed to find the right sequence.

Real-world parallel: Watch any Federer or Nadal point - they're thinking 2-3 shots ahead, setting up patterns that create winning opportunities. A beginner who just "hits it back" will lose to someone who constructs points strategically.

---

## Part 2: STRIPS Formalization

### Predicates/Fluents

These predicates describe the state of the tennis point:

```
At(entity, position)           - Entity is at a court position
                                 Examples: At(Player, BaselineCenter), At(Opponent, NetLeft)

HasBall(entity)                - Entity currently has ball control
                                 Examples: HasBall(Player), HasBall(Opponent)

CourtOpen(side)                - A side of the court is open/vulnerable
                                 Values: CourtOpen(Left), CourtOpen(Right)

OpponentOffBalance             - Opponent is out of position or struggling

OpponentTired                  - Opponent is tired (from running)

AtNet(entity)                  - Entity is positioned at the net
                                 Examples: AtNet(Player), AtNet(Opponent)

DeepShot                       - Last shot was hit deep (gives time to approach)

ShortBall                      - Ball is short/near the net

PointWon                       - The point has been won (GOAL)
```

### Action Schemas

#### Action 1: HitCrosscourt(from_position, target_side)

Hits a diagonal groundstroke to move opponent to opposite side.

**Parameters**: 
- from_position: Where player is hitting from (BaselineLeft/Center/Right)
- target_side: Which side to target (Left or Right)

**Preconditions**:
```
{At(Player, from_position), HasBall(Player), NOT AtNet(Player)}
```

**Add Effects**:
```
{HasBall(Opponent), 
 At(Opponent, Baseline[target_side]), 
 CourtOpen([opposite of target_side]),
 DeepShot}
```

**Delete Effects**:
```
{HasBall(Player), 
 ShortBall}
```

**Example**: 
- HitCrosscourt(BaselineCenter, Right) 
- Moves opponent to BaselineRight, opens up the left side

---

#### Action 2: HitDownTheLine(from_position, target_side)

Hits a straight shot along the sideline to the open court.

**Parameters**: 
- from_position: Where player is hitting from
- target_side: Which sideline (Left or Right)

**Preconditions**:
```
{At(Player, from_position), 
 HasBall(Player), 
 CourtOpen(target_side),
 NOT AtNet(Player)}
```

**Add Effects**:
```
{PointWon}  // If court is open, down-the-line often wins
```

**Delete Effects**:
```
{HasBall(Player),
 CourtOpen(target_side)}
```

**Example**: 
- After moving opponent right, HitDownTheLine(BaselineCenter, Left) wins the point

---

#### Action 3: ApproachNet()

Moves player to the net after hitting a deep shot.

**Preconditions**:
```
{HasBall(Opponent),  // Opponent must have ball (we just hit it)
 DeepShot,           // Our last shot was deep (gives us time)
 NOT AtNet(Player)}  // We're not already at net
```

**Add Effects**:
```
{AtNet(Player),
 At(Player, NetCenter)}
```

**Delete Effects**:
```
{At(Player, BaselineCenter),  // Moving from baseline
 At(Player, BaselineLeft),
 At(Player, BaselineRight)}
```

**Example**: 
- After hitting deep crosscourt, approach the net to finish point

---

#### Action 4: HitVolley(target_side)

Hits a volley (before ball bounces) when at the net.

**Parameters**: 
- target_side: Where to aim the volley (Left or Right)

**Preconditions**:
```
{AtNet(Player),
 HasBall(Player),
 CourtOpen(target_side)}
```

**Add Effects**:
```
{PointWon}  // Volleys to open court usually win
```

**Delete Effects**:
```
{HasBall(Player),
 CourtOpen(target_side)}
```

**Example**: 
- At net with left court open → HitVolley(Left) wins point

---

#### Action 5: HitDropShot(from_position)

Hits a soft shot that barely clears the net, catching opponent off guard.

**Parameters**: 
- from_position: Where player is hitting from

**Preconditions**:
```
{At(Player, from_position),
 HasBall(Player),
 NOT AtNet(Opponent),        // Opponent is back
 At(Opponent, BaselineLeft) OR At(Opponent, BaselineCenter) OR At(Opponent, BaselineRight)}
```

**Add Effects**:
```
{ShortBall,
 OpponentOffBalance,
 PointWon}  // If opponent is far back, drop shot often wins
```

**Delete Effects**:
```
{HasBall(Player),
 DeepShot}
```

**Example**: 
- When opponent is deep at baseline, surprise them with a drop shot

---

#### Action 6: HitLob(from_position)

Hits a high arcing shot over opponent's head (counter to net player).

**Parameters**: 
- from_position: Where player is hitting from

**Preconditions**:
```
{At(Player, from_position),
 HasBall(Player),
 AtNet(Opponent)}  // Opponent is at net, vulnerable to lob
```

**Add Effects**:
```
{HasBall(Opponent),
 OpponentOffBalance,
 At(Opponent, BaselineCenter),  // Lob pushes them back
 CourtOpen(Left),
 CourtOpen(Right)}
```

**Delete Effects**:
```
{HasBall(Player),
 AtNet(Opponent)}
```

**Example**: 
- When opponent approaches net, lob over their head to push them back

---

### Example Problem Instance 1: "The Classic Setup"

**Initial State**:
```python
{
    "At(Player, BaselineCenter)",
    "At(Opponent, BaselineCenter)", 
    "HasBall(Player)"
}
```

**Goal State**:
```python
{
    "PointWon"
}
```

**Expected Plan** (one possible solution):
1. HitCrosscourt(BaselineCenter, Right) - Move opponent to right side
2. HitDownTheLine(BaselineCenter, Left) - Hit winner to open left court

**Why this works**: First shot creates court opening, second shot exploits it.

---

### Example Problem Instance 2: "Approach and Volley"

**Initial State**:
```python
{
    "At(Player, BaselineCenter)",
    "At(Opponent, BaselineRight)",
    "HasBall(Player)",
    "CourtOpen(Left)"
}
```

**Goal State**:
```python
{
    "PointWon"
}
```

**Expected Plan** (one possible solution):
1. HitCrosscourt(BaselineCenter, Right) - Hit deep to opponent (adds DeepShot)
2. ApproachNet() - Move to net while opponent retrieves
3. HitVolley(Left) - Put away volley to open court

**Why this works**: Deep shot gives time to approach, volley finishes at net.

---

### Example Problem Instance 3: "Defensive Lob Recovery"

**Initial State**:
```python
{
    "At(Player, BaselineLeft)",
    "At(Opponent, NetCenter)",
    "HasBall(Player)",
    "AtNet(Opponent)"
}
```

**Goal State**:
```python
{
    "PointWon"
}
```

**Expected Plan** (one possible solution):
1. HitLob(BaselineLeft) - Lob over opponent, push them back
2. HitDownTheLine(BaselineLeft, Left) - Hit winner to now-open court

**Why this works**: Lob neutralizes opponent's net position, creates opening for winner.

---

### Summary of Domain Characteristics

- **Number of distinct actions**: 6 (HitCrosscourt, HitDownTheLine, ApproachNet, HitVolley, HitDropShot, HitLob)
- **State space size**: Large - combinations of positions, ball possession, court openings
- **Realistic complexity**: Models actual tennis strategy and point construction
- **Planning requirement**: Clear dependencies between actions (must create openings before exploiting them)
