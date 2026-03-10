import pydealer

RANKS = [str(i) for i in range(1, 12)]
SUIT  = "Numbered"


def build_deck():
    deck = pydealer.Deck(build=False)
    for rank in RANKS:
        deck.add(pydealer.Stack(cards=[pydealer.Card(rank, SUIT)]))
    deck.shuffle()
    return deck


def card_value(card):
    return int(card.value)


def replenish_deck(deck):
    for rank in RANKS:
        deck.add(pydealer.Stack(cards=[pydealer.Card(rank, SUIT)]))
    deck.shuffle()