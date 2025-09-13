from .player import Player

class Dealer(Player):
    def __init__(self):
        super().__init__("Dealer", chips=0)
        
    def play_turn(self):
        """Dealer's turn logic"""
        while self.total < 17:
            self.hit()
        return self.cards