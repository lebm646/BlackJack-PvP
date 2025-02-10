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
        self.bj = False
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
        if self.busted or self.bj:
            return None  # Prevent drawing if busted or blackjack
        
        card = draw()
        self.cards.append(card)
        self.total = calculate(self.cards)
        
        if self.total > 21:
            self.busted = True
        if self.total == 21:
            self.bj = True

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
def start_game():
    global player1, player2
    data = request.json
    player1 = Player(data['player1'])
    player2 = Player(data['player2'])

    bet = data.get('bet', 10)

    if not player1.place_bet(bet) or not player2.place_bet(bet):
        return jsonify({"error": "Not enough chips to place bet"}), 400
    
    # Give each player two initial cards
    player1.hit()
    player1.hit()
    player2.hit()
    player2.hit()

    result = check_winner()

    return jsonify({
        "message": "Game started!",
        "player1": {"name": player1.name, "cards": player1.cards, "total": player1.total, "chips": player1.chips},
        "player2": {"name": player2.name, "cards": player2.cards, "total": player2.total, "chips": player2.chips},
        "winner": result  # Return winner if any
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
        return jsonify({"error": "Cannot draw more cards", "busted": player.busted, "blackjack": player.bj, "chips": player.chips})
    
    if player.busted:
        player.lose_bet()

    result = check_winner()  # Check winner after each hit

    return jsonify({
        "player": data['player'],
        "card": card,
        "cards": player.cards,  # Send updated card list
        "total": player.total,
        "busted": player.busted,
        "blackjack": player.bj,
        "chips": player.chips,
        "winner": result  # Send winner message if applicable
    })

def check_winner():
    """Checks if either player has won and returns the result"""
    if player1.bj and player2.bj:
        player1.win_bet(1)
        player2.win_bet(1)
        return "Both players got Blackjack! It's a tie!"
        
    elif player1.bj or player2.busted:
        player1.win_bet()
        return f"{player1.name} wins!"
    
    elif player2.bj or player1.busted:
        player2.win_bet()
        return f"{player2.name} wins!"
    
    return None  # No winner yet

@app.route('/reset', methods=['POST'])
def reset_game():
    global player1, player2, deck
    deck = ['A', 'K', 'Q', 'J', 10, 9, 8, 7, 6, 5, 4, 3, 2] * 4  # Reset deck

    player1_chips = player1.chips
    player2_chips = player2.chips

    player1 = Player(player1.name, chips=player1_chips)
    player2 = Player(player2.name, chips=player2_chips)

    return jsonify({"message": "Game has been reset!",  "player1_chips": player1.chips, "player2_chips": player2.chips})

if __name__ == '__main__':
    app.run(debug=True)
