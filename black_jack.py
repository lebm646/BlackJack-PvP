class Player:
    # to create a player, input name. You can add numbers of chips if wish to. Default number is 500
    def __init__(self, name, chips = 500):
        self.name = name
        self.chips = chips
        self.game_played = 0
        self.game_won = 0
    def play(self):
        self.game_played += 1
    def win(self, bet):
        self.game_won += 1
        self.chips += bet
        print('{name} has {chips} remaining chips'.format(name = self.name, chips = self.chips))
    def lose(self, bet):
        self.chips -= bet
        print('{name} has {chips} remaining chips'.format(name = self.name, chips = self.chips))

