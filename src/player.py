import random

def draw():
    """Draw a random card from a standard deck."""
    values = ['A', 'K', 'Q', 'J'] + [str(i) for i in range(2, 11)]
    suits = ['H', 'D', 'C', 'S']  # Hearts, Diamonds, Clubs, Spades
    return f"{random.choice(values)}{random.choice(suits)}"

def calculate(cards):
    """Calculate the total value of a hand of cards."""
    value = 0
    aces = 0
    
    for card in cards:
        # Extract the value part (remove suit)
        val = card[:-1] if len(card) > 1 else card
        
        if val in ['K', 'Q', 'J']:
            value += 10
        elif val == 'A':
            value += 11
            aces += 1
        else:
            value += int(val)
    
    # Handle aces
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    
    return value

class Player:
    def __init__(self, name, chips = 100):
        self.name = name
        self.cards = []
        self.total = 0
        self.busted = False
        self.blackjack = False
        self.chips = chips
        self.bet = 0
    
    def place_bet(self, amount):
        """Place a bet, deducting the amount from chips."""
        if amount > self.chips:
            return False
        
        self.bet = amount
        self.chips -= amount
        return True
    
    def win_bet(self, multiplier=2):
        """Add winnings to chips based on the bet and multiplier."""
        if self.bet <= 0:
            return 0
            
        # Calculate total winnings (bet * multiplier) plus return the original bet
        winnings = (self.bet * multiplier) + self.bet
        self.chips += winnings
        self.bet = 0  # Reset the bet
        return winnings
        
    def lose_bet(self):
        """Lose the current bet (chips were already deducted)."""
        lost = self.bet
        self.bet = 0
        return lost


    def hit(self, card=None):
        if self.busted or self.blackjack:
            return None  # Prevent drawing if busted or blackjack
        
        if card is None:
            card = draw()
            
        self.cards.append(card)
        self.total = calculate(self.cards)
        
        if self.total > 21:
            self.busted = True
        if self.total == 21:
            self.blackjack = True

        return card