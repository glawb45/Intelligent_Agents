# Tennis Point Planning Domain

## Part 1: Domain Selection & Description

### Real-world Scenario
This domain models a **tennis point planning strategy** for an amateur-professional tennis player. Players use many different tactics to attempt to win points, of which of those shot types and court states I define further below.

### Entities in Domain

1. **Players**
    - Player (my perspective)
    - Opponent

2. **Court Positions**:
    - BaselineLeft
    - BaselineCenter
    - BaselineRight
    - NetLeft
    - NetCenter
    - NetRight

3. **Shot Types**:
    - Crosscourt
    - DownTheLine
    - DropShot
    - Lob
    - Volley

4. **Court State**:
    - Ball possession
    - Player positions
    - Court openings (which side of court is vulnerable)

### Objective

**Tennis player attempts to win point using different tactics:**
    - Move opponent out of position
    - Create open court space
    - Execute shot opponent cannot return
    - Force error from opponent

Ex. A player can have a long crosscourt rally with the opponent, and eventually hit a down-the-line shot to offset the play and hit a winner.

### Why is planning needed?

Reflex agents are unable to detect complex changes in states and conditional dependencies.

1. **Conditional shots**: Opponents are thinking 2 shots ahead. How can you move them out of position and utilize the open court?

2. **Position constraints**: A player must be, for example, at the net in order to hit a net point.

3. **State transitions**: Each shot changes the state to enable or disable future actions. Planning is needed to find the right sequence.

---

## Part 2: STRIPS Formalization

### Predicates/Fluents

```
At(entity, position)           - Entity is at a court position
                                 Examples: At(Player, BaselineCenter), At(Opponent, NetLeft)

HasBall(entity)                - Entity currently has ball control
                                 Examples: HasBall(Player), HasBall(Opponent)

CourtOpen(side)                - A side of the court is open/vulnerable
                                 Values: CourtOpen(Left), CourtOpen(Right)

OpponentOffBalance             - Opponent is out of position or struggling

AtNet(entity)                  - Entity is positioned at the net
                                 Examples: AtNet(Player), AtNet(Opponent)

DeepShot                       - Last shot was hit deep (gives time to approach)

ShortBall                      - Ball is short/near the net

PointWon                       - The point has been won (GOAL)
```

### Action Schemas

#### Action 1: Crosscourt(from_pos, target)

Hit a diagonal groundstroke to move opponent to opposite side.

**Parameters**
- from_pos: Where player is hitting from
- target: Which side to target

**Preconditions**

```
{At(Player, from_pos), HasBall(Player), NOT AtNet(PLayer)}
```

**Add Effects**

```
{HasBall(Opponent),
At(Opponent, Baseline{target}),
CourtOpen({opp_side})
DeepShot}
```

**Delete Effects**

```
{HasBall(Player),
ShortBall}
```

#### Action 2: DownTheLine(from_pos, target)

Hit a down-the-line winner.

**Parameters**
- from_pos
- target

**Preconditions**

```
{At(Player, from_pos),
HasBall(Player),
CourtOpen(target)}
```

**Add Effects**

```
{PointWon}
```

**Delete Effects**

```
{HasBall(Player),
CourtOpen(target)}
```

#### Action 3: ApproachNet()

Approach the net and hit a winning shot.

**Parameters**
- None

**Preconditions**

```
{HasBall(Opponent),
DeepShot}
```

**Add Effects**

```
{AtNet(Player),
At(Player, NetCenter)}
```

**Delete Effects**

```
{At(Player, BaselineCenter),
At(Player, BaselineLeft),
At(Player, BaselineRight)}
```

#### Action 4: Volley(target)

Hit a volley winner (assume from net).

**Parameters**
- target

**Preconditions**

```
{AtNet(Player),
HasBall(Player),
CourtOpen({target})}
```

**Add Effects**

```
{PointWon}
```

**Delete Effects**

```
{HasBall(Player),
CourtOpen({target})}
```

#### Action 5: DropShot(from_pos)

Hit a drop shot winner from anywhere on the court.

**Parameters**
- from_pos

**Preconditions**

```
{At(Player, {from_pos}),
HasBall(Player),
OpponentOffBalance}
```

**Add Effects**

```
{ShortBall,
PointWon}
```

**Delete Effects**

```
{HasBall(Player),
DeepShot}
```

#### Action 6: Lob(from_pos)

Lob the opposing player, assuming they are at the net and are pushed back to the baseline and lose the point.

**Parameters**
- from_pos

**Preconditions**

```
{At(Player, {from_pos}),
HasBall(Player),
AtNet(Opponent)}
```

**Add Effects**

```
{HasBall(Opponent),
At(Opponent, BaselineCenter),
ourtOpen(Left),
CourtOpen(Right),
DeepShot}
```

**Delete Effects**

```
{HasBall(Player),
AtNet(Opponent),
At(Opponent, NetCenter)}
```

#### Action 7: ReceiveReturn()

Lob the opposing player, assuming they are at the net and are pushed back to the baseline and lose the point.

**Parameters**
- None

**Preconditions**

```
{HasBall(Opponent)}
```

**Add Effects**

```
{HasBall(Player)}
```

**Delete Effects**

```
{HasBall(Opponent)}
```

### Problem Instances

#### P1: Move Opponent, Hit DTL Winner

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

**Expected Plan** (one solution):
1. Crosscourt(BaselineCenter, Right): Move opponent to right side
2. DownTheLine(BaselineCenter, Left) - Hit backhand winner down the line (assuming right handed player)

**Reasoning**: First shot creates open court, second shot puts point away.

#### P2: Approach and Volley

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

**Expected Plan** (one solution):
1. Crosscourt(BaselineCenter, Right): Move opponent to right side
2. ApproachNet(): Move to net while opponent retrieves
3. Volley - Put volley away

**Reasoning**: First shot gives time to approach, volley finish at net

---

# Part 3: Python Implementation

