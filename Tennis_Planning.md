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