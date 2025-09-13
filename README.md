# Multiplayer Blackjack

A feature-rich multiplayer Blackjack game built with Flask (Python) for the backend and modern JavaScript for the frontend. Play with friends and experience realistic Blackjack gameplay with chip betting, multiple rounds, and a dealer.

## 🚀 Features

- **Multiplayer Support**: Play with friends in the same game session
- **Chip Betting System**: Start with 100 chips and bet each round
- **Real-time Updates**: See game state changes instantly
- **Blackjack Payouts**: 3:2 payout for Blackjack (1.5x your bet)
- **Dealer AI**: Automated dealer follows standard Blackjack rules (hits on 16, stands on 17)
- **Multiple Rounds**: Play multiple hands without restarting
- **Responsive Design**: Works on desktop and mobile devices

## 🎮 How to Play

1. **Create or Join a Game**
   - Create a new game or join an existing one using the game ID
   - Enter your name and join the game

2. **Place Your Bet**
   - Each player starts with 100 chips
   - Place your bet before the round starts (default is 10 chips)

3. **Gameplay**
   - Each player is dealt two cards
   - The dealer shows one card face up and one face down
   - On your turn, choose to:
     - **Hit**: Take another card
     - **Stand**: Keep your current hand
   - If you go over 21, you bust and lose your bet
   - Blackjack (Ace + 10-value card) pays 3:2

4. **Winning**
   - Beat the dealer's hand without going over 21
   - Get 21 with your first two cards (Blackjack) for a 3:2 payout
   - If you and the dealer tie, you get your bet back (push)

5. **Next Round**
   - After each round, click "New Round" to play again
   - Chips carry over between rounds

## 🛠️ Technical Details

- **Backend**: Python/Flask
- **Frontend**: Vanilla JavaScript with Fetch API
- **Real-time Updates**: Polling mechanism for game state
- **Responsive Design**: CSS Grid and Flexbox

## 🚀 Getting Started

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python run.py
   ```

3. Open your browser and go to `http://localhost:5000`

## 🎯 Future Improvements

- Add user accounts and persistent statistics
- Implement chat functionality
- Add sound effects and animations
- Support for custom betting amounts
- Mobile app version
