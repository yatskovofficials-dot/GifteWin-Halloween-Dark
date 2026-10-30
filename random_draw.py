import random
from typing import List, Dict, Any


def draw_winners(
    participants: List[Dict[str, Any]],
    winners_count: int,
    base_weight: int = 100
) -> List[int]:
    """
    Weighted random draw.
    Each participant has weight = base_weight + luck_balls.
    More luck_balls = higher chance.
    """
    if not participants:
        return []

    winners_count = min(winners_count, len(participants))
    if winners_count <= 0:
        return []

    # Create weighted pool
    pool = []
    weights = []
    for p in participants:
        luck = p.get("luck_at_join") or p.get("luck_balls") or 0
        weight = base_weight + max(0, luck)
        pool.append(p["user_id"])
        weights.append(weight)

    rng = random.SystemRandom()
    winners = []
    remaining_pool = pool[:]
    remaining_weights = weights[:]

    for _ in range(winners_count):
        if not remaining_pool:
            break
        chosen = rng.choices(remaining_pool, weights=remaining_weights, k=1)[0]
        winners.append(chosen)

        # Remove winner from pool
        idx = remaining_pool.index(chosen)
        remaining_pool.pop(idx)
        remaining_weights.pop(idx)

    return winners
