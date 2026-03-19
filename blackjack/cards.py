import pydealer

RANKS = [str(i) for i in range(1, 12)]
SUIT  = "Numbered"

def build_deck():
    # cards go from 1 to 11, no suits, only numbers
    deck = pydealer.Deck(build=False)
    for rank in RANKS:
        deck.add(pydealer.Stack(cards=[pydealer.Card(rank, SUIT)]))
    deck.shuffle()
    return deck

def card_value(card):
    return int(card.value)

def replenish_deck(deck):
    # called when the deck runs low, adds a new set of 1-11 and reshuffles
    for rank in RANKS:
        deck.add(pydealer.Stack(cards=[pydealer.Card(rank, SUIT)]))
    deck.shuffle()