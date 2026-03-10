print("LOADING game_logic.py")
import random
from cards import build_deck, card_value, replenish_deck

# ── Game state ─────────────────────────────────────────────────────────────

class GameState:
    def __init__(self):
        self.deck                = build_deck()
        self.player_hand         = []
        self.enemy_hand          = []
        self.player_total        = 0
        self.enemy_total         = 0
        self.current_max         = 21
        self.state               = "player_turn"  # player_turn | enemy_turn | round_over | game_over
        self.round_result        = None           # "player_win" | "enemy_win" | "draw"
        self.consecutive_losses  = 0
        self.round_number        = 1
        self.player_inventory    = []
        self.enemy_inventory     = []
        self.inventory_index     = 0

    def reset_round(self):
        self.player_hand  = []
        self.enemy_hand   = []
        self.player_total = 0
        self.enemy_total  = 0
        self.current_max  = 21
        self.round_result = None
        self.state        = "player_turn"
        self.inventory_index = 0
        self.round_number += 1
        if len(self.deck) < 4:
            replenish_deck(self.deck)


# ── Drawing ────────────────────────────────────────────────────────────────

def draw_card(game, target):
    if len(game.deck) == 0:
        replenish_deck(game.deck)
    card = game.deck.deal(1).cards[0]
    if target == "player":
        game.player_hand.append(card)
        game.player_total += card_value(card)
    else:
        game.enemy_hand.append(card)
        game.enemy_total += card_value(card)
    return card


def deal_opening_hands(game):
    for _ in range(2):
        draw_card(game, "player")
        draw_card(game, "enemy")


# ── Player actions ─────────────────────────────────────────────────────────

def player_hit(game):
    return draw_card(game, "player")


def player_stand(game):
    game.state = "enemy_turn"


# ── Enemy AI ───────────────────────────────────────────────────────────────

def enemy_should_stand(game):
    ratio = game.enemy_total / game.current_max
    if ratio >= 1.0:
        return True
    if ratio < 0.5:
        return False
    stand_probability = (ratio - 0.5) * 2
    return random.random() < stand_probability


def run_enemy_turn(game):
    import trump
    trump.run_enemy_abilities(game)
    while True:
        if enemy_should_stand(game):
            break
        draw_card(game, "enemy")
        if game.enemy_total > game.current_max:
            break
    resolve_round(game)


# ── Round resolution ───────────────────────────────────────────────────────

def resolve_round(game):
    p = game.player_total
    e = game.enemy_total
    m = game.current_max

    player_busted = p > m
    enemy_busted  = e > m

    if player_busted and enemy_busted:
        if p == e:
            result = "draw"
        elif p > e:
            result = "enemy_win"
        else:
            result = "player_win"
    elif player_busted:
        result = "enemy_win"
    elif enemy_busted:
        result = "player_win"
    else:
        if p > e:
            result = "player_win"
        elif e > p:
            result = "enemy_win"
        else:
            result = "draw"

    game.round_result = result
    game.state        = "round_over"
    _update_match_state(game, result)


def _update_match_state(game, result):
    if result == "enemy_win":
        game.consecutive_losses += 1
    else:
        game.consecutive_losses = 0
    if game.consecutive_losses >= 2:
        game.state = "game_over"


# ── Ability distribution ───────────────────────────────────────────────────

ABILITY_POOL = [
    "max24", "max27", "max17",
    "reset_deck", "swap_last",
    "friendship", "force_draw",
    "draw_specific", "perfect_draw"
]

def distribute_abilities(game):
    count = 1 if game.round_result == "draw" else random.randint(1, 2)
    player_gains = [random.choice(ABILITY_POOL) for _ in range(count)]
    enemy_gains  = [random.choice(ABILITY_POOL) for _ in range(count)]
    game.player_inventory.extend(player_gains)
    game.enemy_inventory.extend(enemy_gains)
    return player_gains, enemy_gains