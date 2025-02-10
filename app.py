from flask import Flask, request, jsonify, render_template
import random

app = Flask(__name__)

# Card deck and game logic
deck = ['A', 'K', 'Q', 'J', 10, 9, 8, 7, 6, 5, 4, 3, 2] * 4

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
        if amount > self.chips:
            return False
        
        self.bet = amount
        self.chips -= amount
        return True
    
    def win_bet(self, multiplier = 2):
        self.chips += self.bet * multiplier
        self.bet = 0

    def lose_bet(self):
        self.bet = 0


    def hit(self):
        if self.busted or self.blackjack:
            return None  # Prevent drawing if busted or blackjack
        
        card = draw()
        self.cards.append(card)
        self.total = calculate(self.cards)
        
        if self.total > 21:
            self.busted = True
        if self.total == 21:
            self.blackjack = True

        return card

def draw():
    random.shuffle(deck)
    return deck.pop()

def calculate(cards):
    total = 0
    aces = 0

    for card in cards:
        if card in ['K', 'Q', 'J']:
            total += 10
        elif card == 'A':
            aces += 1
        else:
            total += card
    
    for _ in range(aces):
        total += 11 if total + 11 <= 21 else 1
        
    return total

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
@app.route('/start', methods=['POST'])
def start_game():
    global player1, player2

    data = request.json
    bet = data.get('bet', 10)  # Default bet of 10 chips

    # Preserve chips if players already exist
    if 'player1' in globals() and player1:
        player1_chips = player1.chips
    else:
        player1_chips = 100  # Default if new game

    if 'player2' in globals() and player2:
        player2_chips = player2.chips
    else:
        player2_chips = 100  # Default if new game

    # Create players while keeping existing chip counts
    player1 = Player(data['player1'], chips=player1_chips)
    player2 = Player(data['player2'], chips=player2_chips)

    # Deduct bet from both players
    if not player1.place_bet(bet) or not player2.place_bet(bet):
        return jsonify({"error": "Not enough chips to place bet"}), 400

    # Deal two cards to each player
    player1.hit()
    player1.hit()
    player2.hit()
    player2.hit()

    result = check_winner()

    return jsonify({
        "message": "Game started!",
        "player1": {"name": player1.name, "cards": player1.cards, "total": player1.total, "chips": player1.chips},
        "player2": {"name": player2.name, "cards": player2.cards, "total": player2.total, "chips": player2.chips},
        "winner": result
    })


@app.route('/hit', methods=['POST'])
def hit():
    data = request.json

    # Ensure player is properly identified
    if data['player'] == "player1":
        player = player1
    elif data['player'] == "player2":
        player = player2
    else:
        return jsonify({"error": "Invalid player"})

    card = player.hit()

    if card is None:
        return jsonify({"error": "Cannot draw more cards", "busted": player.busted, "blackjack": player.blackjack, "chips": player.chips})
    
    if player.busted:
        player.lose_bet()

    result = check_winner()  # Check winner after each hit

    return jsonify({
        "player": data['player'],
        "card": card,
        "cards": player.cards,  # Send updated card list
        "total": player.total,
        "busted": player.busted,
        "blackjack": player.blackjack,
        "chips": player.chips,
        "winner": result  # Send winner message if applicable
    })

def check_winner():
    """Checks if either player has won and returns the result"""
    if player1.blackjack and player2.blackjack:
        player1.win_bet(1)
        player2.win_bet(1)
        return "Both players got Blackjack! It's a tie!"
        
    elif player1.blackjack or player2.busted:
        player1.win_bet()
        return f"{player1.name} wins!"
    
    elif player2.blackjack or player1.busted:
        player2.win_bet()
        return f"{player2.name} wins!"
    
    return None  # No winner yet

@app.route('/reset', methods=['POST'])
@app.route('/reset', methods=['POST'])
def reset_game():
    global player1, player2, deck

    # Keep existing chip amounts before resetting the game
    player1_chips = player1.chips if player1 else 100
    player2_chips = player2.chips if player2 else 100

    # Reset the deck
    deck = ['A', 'K', 'Q', 'J', 10, 9, 8, 7, 6, 5, 4, 3, 2] * 4

    # Recreate players with their previous chip amounts
    player1 = Player(player1.name, chips=player1_chips)
    player2 = Player(player2.name, chips=player2_chips)

    return jsonify({
        "message": "Game has been reset!",
        "player1_chips": player1.chips,
        "player2_chips": player2.chips
    })


if __name__ == '__main__':
    app.run(debug=True)
