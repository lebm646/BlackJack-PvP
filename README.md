# Multiplayer Blackjack

A feature-rich multiplayer Blackjack game built with Flask (Python) for the backend and modern JavaScript for the frontend. Play with friends and experience realistic Blackjack gameplay with chip betting, multiple rounds, and a dealer.

## 🚀 Features

- **Multiplayer Support**: Play with friends in the same game session
- **Chip Betting System**: Start with 100 chips and choose a validated bet each round
- **Private Player Identity**: Player actions use private per-session credentials
- **Host Controls**: Only the table creator can start games and new rounds
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
   - The host opens betting, then each funded player chooses a positive whole-chip bet
   - The cards are dealt automatically after the last player places a bet

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
- **Session Identity**: Private player and host tokens are kept in session storage for tab refreshes
- **Responsive Design**: CSS Grid and Flexbox

Active games use shared Upstash Redis when configured. Successful player actions renew a 24-hour idle expiry; polling alone does not keep abandoned games alive. Local development without Redis uses memory.

## Vercel storage setup

Connect your Upstash Redis database to this Vercel project and enable the Production environment. Keep the generated credentials private. The app accepts either pair of environment variables:

- `KV_REST_API_URL` and `KV_REST_API_TOKEN` (Vercel integration defaults)
- `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`

Redeploy after connecting the database so the new deployment receives the variables. Use the read/write token, not a read-only token. No additional Python runtime dependency is needed: the app uses Upstash's HTTPS REST API.

Vercel deployments never fall back to memory: missing credentials or storage outages return a temporary 503 error without signing players out. Updates use atomic compare-and-set; conflicting actions return 409 and should be retried after refreshing the game state. Production and preview use separate key prefixes; `BLACKJACK_REDIS_PREFIX` can override the default when sharing a database between multiple projects.

Games created before the Redis migration cannot be recovered; create a new game after deployment.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Storage tests run Redis Lua scripts against fakeredis and simulate separate function instances. They never connect to the production database.

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
