import random

class BlackjackEngine:
    def __init__(self):
        self.deck = self.create_deck()
        self.player_hand = []
        self.dealer_hand = []
    
    def create_deck(self):
        suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [(rank, suit) for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck
    
    def card_value(self, rank):
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11
        else:
            return int(rank)
    
    def hand_value(self, hand):
        total = sum(self.card_value(card[0]) for card in hand)
        aces = sum(1 for card in hand if card[0] == 'A')
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total
    
    def draw_card(self):
        if not self.deck:
            self.deck = self.create_deck()
        return self.deck.pop()
    
    def start_game(self):
        self.player_hand = [self.draw_card(), self.draw_card()]
        self.dealer_hand = [self.draw_card(), self.draw_card()]
    
    def player_hit(self):
        self.player_hand.append(self.draw_card())
    
    def dealer_play(self):
        while self.hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.draw_card())
    
    def get_result(self):
        player_value = self.hand_value(self.player_hand)
        dealer_value = self.hand_value(self.dealer_hand)
        
        if player_value > 21:
            return "Bust! Dealer wins."
        elif dealer_value > 21:
            return "Dealer bust! You win!"
        elif player_value > dealer_value:
            return "You win!"
        elif dealer_value > player_value:
            return "Dealer wins."
        else:
            return "Push!"

if __name__ == "__main__":
    game = BlackjackEngine()
    game.start_game()
    print(f"Your hand: {game.player_hand}, Value: {game.hand_value(game.player_hand)}")
    print(f"Dealer shows: {game.dealer_hand[0]}")