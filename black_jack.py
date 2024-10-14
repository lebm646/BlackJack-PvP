class Player:
    # to create a player, input name. 
    # You can add numbers of chips if wish to. 
    # Default number is 100
    def __init__(self, name, chips = 100, cards =[]):
        self.name = name
        self.chips = chips
        self.game_played = 0
        self.game_won = 0
        self.cards = cards

    def play(self):
        self.game_played += 1

    def win(self, bet):
        self.game_won += 1
        self.chips += bet
        # print('{name} has {chips} remaining chips'
        #       .format(name = self.name, chips = self.chips))

    def lose(self, bet):
        self.chips -= bet
        # print('{name} has {chips} remaining chips'
        #       .format(name = self.name, chips = self.chips))
    def hit(self):
        while True:
            hit = input('{player}, do you want to hit? yes/no: '.format(player = self.name)).strip().lower()
            if hit == 'no':
                break
            elif hit =='yes':
                card = draw()
                self.cards.append(card)
                player_points = calculate(self.cards)
                print('You get {card}. Your points are {point}'.format(card = card, point= player_points))
                # player bust
                if player_points > 21:
                    print('You are busted!')
                    break
                elif player_points == 21:
                    breakc
                continue
            else:
                print('Invalid input! Please try again!')
                continue

import random
deck = ['A','K','Q','J',10,9,8,7,6,5,4,3,2] * 4

# draw 1 card function
def draw():
    card = deck.pop(0)
    return card
# calculate points function
def calculate(cards):
    total = 0
    aces = 0
    for card in cards:
        if card in ['K','Q','J']: 
            total += 10
        elif card == 'A':
            aces += 1
        else:
            total += card
    for ace in range(aces):
        if total + 11 <= 21:
            total += 11
        else:
            total += 1
    return total
    

#input names for players
player_1_name = input('welcome to Black Jack Terminal! Please enter your name: ')
player_1 = Player(player_1_name)
player_2_name = input("Enter the second player's name: ")
player_2 = Player(player_2_name)
# looping through games
while True:
    # bet input
    bet = input('Hello {name1} and {name2}! Input your desired bet here: '
          .format(name1 = player_1_name, name2 = player_2_name))
    try:
        bet_type= int(bet)
    except ValueError:
        print("Invalid input! Please enter a valid number for the bet.")
        continue
    if int(bet) > player_1.chips or int(bet) > player_2.chips or int(bet) <=0:
        print('Invalid bet! Please try again!')
        continue
    else: print('The agreed bet for this game is {}'.format(bet))

    # draw cards:
    random.shuffle(deck)
    player_1.cards = [draw(), draw()]
    player_2.cards = [draw(), draw()]
    calculate(player_1.cards)
    calculate(player_2.cards)
    print('{player_1} gets {card_1} and {card_2}. Point is {point}'
          .format(player_1= player_1_name, card_1 = player_1.cards[0], card_2 = player_1.cards[1], point = calculate(player_1.cards)))
    print('{player_2} gets {card_3} and {card_4}. Point is {point}'
          .format(player_2= player_2_name, card_3 = player_2.cards[0], card_4 = player_2.cards[1], point = calculate(player_2.cards)))
    # Hitting cards
    player_1.hit()
    if calculate(player_1.cards) <=21:
        player_2.hit()

    # calculate the winner
    if calculate(player_1.cards) > 21:
        player_1.lose(int(bet))
        player_2.win(int(bet))
        print('{player_1} lost! {player_1} has {chips} chips'.format(player_1 = player_1_name, chips = player_1.chips))
        print('{player_2} won! {player_2} has {chips} chips'.format(player_2 = player_2_name, chips = player_2.chips))
    elif calculate(player_2.cards) >21 :  
        player_1.win(int(bet))
        player_2.lose(int(bet))
        print('{player_1} won! {player_1} has {chips} chips'.format(player_1 = player_1_name, chips = player_1.chips))
        print('{player_2} lost! {player_2} has {chips} chips'.format(player_2 = player_2_name, chips = player_2.chips))
    elif calculate(player_1.cards) > calculate(player_2.cards):
        player_1.win(int(bet))
        player_2.lose(int(bet))
        print('{player_1} won! {player_1} has {chips} chips'.format(player_1 = player_1_name, chips = player_1.chips))
        print('{player_2} lost! {player_2} has {chips} chips'.format(player_2 = player_2_name, chips = player_2.chips))
    elif calculate(player_1.cards) < calculate(player_2.cards):
        player_1.lose(int(bet))
        player_2.win(int(bet))
        print('{player_1} lost! {player_1} has {chips} chips'.format(player_1 = player_1_name, chips = player_1.chips))
        print('{player_2} won! {player_2} has {chips} chips'.format(player_2 = player_2_name, chips = player_2.chips))
    else:
        print("It's a tie! No chips are exchanged.")
        print('{player_1} has {chips} chips'.format(player_1 = player_1_name, chips = player_1.chips))
        print('{player_2} has {chips} chips'.format(player_2 = player_2_name, chips = player_2.chips))



    # play again
    while True:
        play_again = input("Do you want to play again? (yes/no): ").strip().lower()
        if play_again != 'yes' and play_again != 'no':
            print('Invalid input! Please try again!')
            continue
        if play_again == 'no':
            print("Thanks for playing! Goodbye.")
            break
        deck = ['A', 'K', 'Q', 'J', 10, 9, 8, 7, 6, 5, 4, 3, 2] * 4
        print("Starting a new game...")
        break  # Exit the inner loop to start a new game

    if play_again == 'no':
        break  # Break the outer loop to stop the game