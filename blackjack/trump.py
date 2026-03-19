import random
import pydealer
from cards import card_value, replenish_deck, build_deck

TRUMP_POOL = [
    "max24", "max27", "max17",
    "reset_deck", "exchange",
    "friendship", "force_draw",
    "draw2", "draw4", "draw6", "perfect_draw"
]


# helper functions used by multiple trump cards

def _user_hand(game, user):
    return game.player_hand if user == "player" else game.enemy_hand

def _user_total(game, user):
    return game.player_total if user == "player" else game.enemy_total

def _set_total(game, user, value):
    if user == "player":
        game.player_total = value
    else:
        game.enemy_total = value

def _opponent(user):
    return "enemy" if user == "player" else "player"

def _draw_card_for(game, target):
    # deals one card from the deck straight into a hand, updates total
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

def _find_and_remove(deck, rank):
    # searches the deck for a specific rank and pulls it out if found
    for card in list(deck.cards):
        if card.value == rank:
            deck.cards.remove(card)
            return card
    return None

def _make_card(rank):
    # creates a card directly when it can't be found in the deck
    return pydealer.Card(rank, "Numbered")


# trump implementations, each takes (game, user) and returns a result string

def apply_max24(game, user):
    game.current_max = 24
    return f"{user.upper()} set the bust limit to 24"

def apply_max27(game, user):
    game.current_max = 27
    return f"{user.upper()} set the bust limit to 27"

def apply_max17(game, user):
    game.current_max = 17
    return f"{user.upper()} set the bust limit to 17"

def apply_reset_deck(game, user):
    # wipes the user's hand, rebuilds the deck, redeals 2 cards
    print(f"BEFORE reset: hand={[c.value for c in _user_hand(game, user)]}, total={_user_total(game, user)}")
    if user == "player":
        game.player_hand  = []
        game.player_total = 0
    else:
        game.enemy_hand  = []
        game.enemy_total = 0
    game.deck = build_deck()
    for _ in range(2):
        card = game.deck.deal(1).cards[0]
        if user == "player":
            game.player_hand.append(card)
            game.player_total += card_value(card)
        else:
            game.enemy_hand.append(card)
            game.enemy_total += card_value(card)
    print(f"AFTER reset: hand={[c.value for c in _user_hand(game, user)]}, total={_user_total(game, user)}")
    return f"{user.upper()} reset the deck — hand redrawn"

def apply_exchange(game, user):
    # swaps the most recently drawn card between both hands and recalculates totals
    if not game.player_hand or not game.enemy_hand:
        return "SWAP LAST failed — a hand is empty"
    p_card = game.player_hand[-1]
    e_card = game.enemy_hand[-1]
    game.player_hand[-1] = e_card
    game.enemy_hand[-1]  = p_card
    game.player_total = sum(card_value(c) for c in game.player_hand)
    game.enemy_total  = sum(card_value(c) for c in game.enemy_hand)
    return f"{user.upper()} swapped last cards — player gave {p_card.value}, got {e_card.value}"

def apply_friendship(game, user):
    # gives 2 random abilities to both players
    gains = [random.choice(TRUMP_POOL) for _ in range(2)]
    game.player_inventory.extend(gains)
    game.enemy_inventory.extend(gains)
    return f"{user.upper()} used FRIENDSHIP — both players gained 2 abilities"

def apply_force_draw(game, user):
    # forces the opponent to take a card immediately
    opp  = _opponent(user)
    card = _draw_card_for(game, opp)
    return f"{user.upper()} forced {opp.upper()} to draw {card.value}"

def _apply_draw_specific(game, user, rank):
    # checks both hands, if the card is already held by anyone, do nothing
    all_held = [c.value for c in game.player_hand + game.enemy_hand]
    if rank in all_held:
        return f"{user.upper()} tried DRAW {rank} — already in play"
    card = _find_and_remove(game.deck, rank)
    if not card:
        # not in deck either (shouldn't happen given above check, but just in case)
        return f"{user.upper()} tried DRAW {rank} — card unavailable"
    _user_hand(game, user).append(card)
    _set_total(game, user, _user_total(game, user) + card_value(card))
    return f"{user.upper()} used DRAW {rank}"

def apply_draw2(game, user):
    return _apply_draw_specific(game, user, "2")

def apply_draw4(game, user):
    return _apply_draw_specific(game, user, "4")

def apply_draw6(game, user):
    return _apply_draw_specific(game, user, "6")

def apply_perfect_draw(game, user):
    # calculates exactly what card is needed to hit current_max and draws it
    # if that card isn't in the deck, it gets generated directly
    total  = _user_total(game, user)
    needed = game.current_max - total
    print(f"PERFECT DRAW: total={total}, max={game.current_max}, needed={needed}")
    if 1 <= needed <= 11:
        card = _find_and_remove(game.deck, str(needed))
        print(f"Card found in deck: {card}")
        if not card:
            card = _make_card(str(needed))
        _user_hand(game, user).append(card)
        _set_total(game, user, total + card_value(card))
        print(f"AFTER perfect draw: total={_user_total(game, user)}")
        return f"{user.upper()} used PERFECT DRAW — drew {card.value} to reach {game.current_max}"
    return f"{user.upper()} used PERFECT DRAW — already at or over max"


# maps trump card names to their functions so use_trump can look them up

TRUMP_FUNCS = {
    "max24":         apply_max24,
    "max27":         apply_max27,
    "max17":         apply_max17,
    "reset_deck":    apply_reset_deck,
    "exchange":     apply_exchange,
    "friendship":    apply_friendship,
    "force_draw":    apply_force_draw,
    "draw2":         apply_draw2,
    "draw4":         apply_draw4,
    "draw6":         apply_draw6,
    "perfect_draw":  apply_perfect_draw,
}

def use_trump(game, trump_name, user):
    # removes the trump card from inventory then runs it
    inventory = game.player_inventory if user == "player" else game.enemy_inventory
    if trump_name not in inventory:
        return f"{trump_name} not in {user} inventory"
    inventory.remove(trump_name)
    func = TRUMP_FUNCS.get(trump_name)
    if func:
        return func(game, user)
    return f"Unknown trump card: {trump_name}"


# enemy bot - decides whether and what trump to play before hitting or standing

def enemy_should_use_trump(game):
    inv = game.enemy_inventory
    if not inv:
        return None
    e = game.enemy_total
    p = game.player_total
    m = game.current_max

    if e >= m - 2:
        # close to busting - try to raise the limit or offload a bad card
        for trump_name in ["max27", "max24", "exchange"]:
            if trump_name in inv:
                return trump_name

    if p >= m - 3 and e < p:
        # player is about to win, punish them
        for trump_name in ["force_draw", "max17", "exchange"]:
            if trump_name in inv:
                return trump_name

    if e < m * 0.6:
        # total is low, try to boost it precisely
        for trump_name in ["perfect_draw"]:
            if trump_name in inv:
                return trump_name

    # small random chance to use something anyway
    if random.random() < 0.15:
        return random.choice(inv)

    return None

def run_enemy_trumps(game):
    trump_name = enemy_should_use_trump(game)
    if trump_name:
        return use_trump(game, trump_name, "enemy")
    return None