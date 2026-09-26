from datetime import datetime, timezone
import random
import secrets
from typing import List, Optional, Dict, Any
from .player import Player
from .dealer import Dealer

class GameSession:
    def __init__(self, session_id: str, creator_name: str, max_players: int = 5):
        self.session_id = session_id
        self.players: List[Player] = []
        self.dealer = Dealer()
        self.deck = self.initialize_deck()
        self.current_turn = 0
        self.status = "waiting"  # waiting, betting, in_progress, finished
        self.max_players = max_players
        self.creator = creator_name
        self.host_token = secrets.token_urlsafe(24)
        self.created_at = datetime.now(timezone.utc)
        self.current_player_index = 0
        self.winner = None
        self.messages: List[str] = []

    def initialize_deck(self) -> List[str]:
        """Initialize a standard deck of 52 cards with suits."""
        values = ['A', 'K', 'Q', 'J'] + [str(i) for i in range(2, 11)]
        suits = ['H', 'D', 'C', 'S']  # Hearts, Diamonds, Clubs, Spades
        deck = []
        for suit in suits:
            for value in values:
                deck.append(f"{value}{suit}")
        return deck

    def add_player(self, player_name: str, chips: int = 100) -> Optional[Player]:
        """Add a player to the session if there's space and name is available."""
        if len(self.players) >= self.max_players:
            return None
        
        if any(p.name.lower() == player_name.lower() for p in self.players):
            return None
            
        player = Player(player_name, chips)
        self.players.append(player)
        return player

    def remove_player(self, player_name: str) -> bool:
        """Remove a player from the session."""
        for i, player in enumerate(self.players):
            if player.name.lower() == player_name.lower():
                self.players.pop(i)
                if self.current_player_index >= len(self.players):
                    self.current_player_index = 0
                return True
        return False

    def begin_betting(self) -> bool:
        """Prepare a new round and wait for funded players to place bets."""
        if not self.players or not any(player.chips > 0 for player in self.players):
            return False

        self.status = "betting"
        self.current_player_index = 0
        self.winner = None
        self.messages = []
        self.dealer = Dealer()
        for player in self.players:
            player.cards = []
            player.total = 0
            player.busted = False
            player.blackjack = False
            player.bet = 0
        return True

    def place_bet(self, player_token: str, amount: int) -> bool:
        """Place a player's bet and deal once every funded player is ready."""
        if self.status != "betting":
            return False

        player = self.get_player_by_token(player_token)
        if player is None or not player.place_bet(amount):
            return False

        funded_players = [player for player in self.players if player.chips > 0 or player.bet > 0]
        if funded_players and all(player.bet > 0 for player in funded_players):
            self.start_game()
        return True

    def start_game(self) -> bool:
        """Deal a round after all participating players have placed a bet."""
        if self.status != "betting" or not any(player.bet > 0 for player in self.players):
            return False

        self.status = "in_progress"
        self.current_player_index = 0
        self.deal_initial_cards()
        if self.dealer.blackjack:
            self.determine_winners()
        else:
            self._skip_completed_players()
        return True

    def deal_initial_cards(self) -> None:
        """Deal initial cards to all players and the dealer."""
        self.deck = self.initialize_deck()
        random.shuffle(self.deck)
        
        # Deal two cards to participating players and the dealer.
        for _ in range(2):
            for player in self.players:
                if player.bet > 0:
                    player.hit(self.deck.pop())
            self.dealer.hit(self.deck.pop())

    def get_player_by_token(self, player_token: str) -> Optional[Player]:
        if not player_token:
            return None
        return next(
            (player for player in self.players if secrets.compare_digest(player.token, player_token)),
            None,
        )

    def get_current_player(self) -> Optional[Player]:
        """Get the player whose turn it is."""
        if not self.players or self.current_player_index >= len(self.players):
            return None
        return self.players[self.current_player_index]

    def next_turn(self) -> bool:
        """Move to the next player's turn. Returns True if game should continue."""
        self.current_player_index += 1

        return self._skip_completed_players()

    def _skip_completed_players(self) -> bool:
        """Advance past blackjack/busted players and run the dealer if none remain."""
        while self.current_player_index < len(self.players):
            player = self.players[self.current_player_index]
            if player.bet > 0 and player.total < 21 and not player.busted:
                return True
            self.current_player_index += 1

        if self.current_player_index >= len(self.players):
            self.current_player_index = 0
            self.dealer_turn()
            self.determine_winners()
            return False

        return True

    def dealer_turn(self) -> None:
        """Handle dealer's turn according to blackjack rules."""
        while self.dealer.total < 17:
            self.dealer.hit(self.deck.pop())

    def determine_winners(self) -> None:
        """Determine the winners of the game and update chips."""
        dealer_total = self.dealer.total
        dealer_busted = self.dealer.busted
        dealer_blackjack = self.dealer.blackjack
        winners = []
        pushes = []
        dealer_wins = []
        
        # Clear previous messages to avoid duplicates
        self.messages = []
        
        # Add dealer's hand to messages
        self.add_game_message(f"Dealer's hand: {', '.join(self.dealer.cards)} (Total: {dealer_total})")
        
        for player in self.players:
            # Add player's hand to messages
            self.add_game_message(f"{player.name}'s hand: {', '.join(player.cards)} (Total: {player.total})")
            
            # Skip if player has no bet
            if player.bet <= 0:
                continue
                
            if player.busted:
                # Player busted, they lose their bet
                player.lose_bet()
                dealer_wins.append(player.name)
                self.add_game_message(f"{player.name} busted and lost their bet!")
            elif player.blackjack:
                if dealer_blackjack:
                    # Both have blackjack, push
                    player.chips += player.bet
                    player.bet = 0
                    pushes.append(player.name)
                    self.add_game_message(f"Both have blackjack! {player.name} pushes.")
                else:
                    # Player has blackjack, dealer doesn't - 3:2 payout
                    winnings = player.win_bet(1.5)  # 3:2 payout
                    winners.append(player.name)
                    self.add_game_message(f"Blackjack! {player.name} wins {winnings} chips!")
            elif dealer_blackjack:
                # Dealer has blackjack, player doesn't
                player.lose_bet()
                dealer_wins.append(player.name)
                self.add_game_message(f"Dealer has blackjack! {player.name} loses their bet!")
            elif dealer_busted:
                # Dealer busted, all remaining players win 1:1
                winnings = player.win_bet(1)
                winners.append(player.name)
                self.add_game_message(f"Dealer busted! {player.name} wins {winnings} chips!")
            elif player.total > dealer_total:
                # Player beats dealer - 1:1 payout
                winnings = player.win_bet(1)
                winners.append(player.name)
                self.add_game_message(f"{player.name} wins {winnings} chips!")
            elif player.total == dealer_total:
                # Push - return bet
                player.chips += player.bet
                player.bet = 0
                pushes.append(player.name)
                self.add_game_message(f"{player.name} pushes and gets their bet back")
            else:
                # Player loses to dealer
                player.lose_bet()
                dealer_wins.append(player.name)
                self.add_game_message(f"{player.name} loses their bet!")
        
        # Reset bets for the next round
        for player in self.players:
            player.bet = 0

        result_parts = []
        if winners:
            label = "Winner" if len(winners) == 1 else "Winners"
            result_parts.append(f"{label}: {', '.join(winners)}!")
        if dealer_wins:
            result_parts.append(f"Dealer beats {', '.join(dealer_wins)}.")
        if pushes:
            result_parts.append(f"Push: {', '.join(pushes)}.")
        self.winner = " ".join(result_parts) or "Round complete."

        self.status = "finished"

    def add_game_message(self, message: str) -> None:
        """Add a message to the game log, avoiding duplicates."""
        # Clean the message for comparison (remove timestamp if present)
        clean_message = message.split('] ')[-1] if '] ' in message else message
        
        # Skip if the same message was just added
        if self.messages and any(clean_message in msg for msg in self.messages):
            return
            
        # Add timestamp and message
        timestamped = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}"
        self.messages.append(timestamped)
        
        # Keep only the last 10 messages
        if len(self.messages) > 10:
            self.messages = self.messages[-10:]

    def get_game_state(self) -> Dict[str, Any]:
        """Return the current game state."""
        dealer_cards = self.dealer.cards
        dealer_total = self.dealer.total
        if self.status != "finished" and dealer_cards:
            dealer_cards = ["XX", *dealer_cards[1:2]]
            dealer_total = None

        return {
            "session_id": self.session_id,
            "status": self.status,
            "max_players": self.max_players,
            "messages": self.messages,
            "players": [{
                "name": p.name,
                "cards": p.cards,
                "total": p.total,
                "chips": p.chips,
                "bet": p.bet,
                "can_bet": self.status == "betting" and p.chips > 0 and p.bet == 0,
                "busted": p.busted,
                "blackjack": p.blackjack,
                "is_current": (i == self.current_player_index and self.status == "in_progress")
            } for i, p in enumerate(self.players)],
            "dealer": {
                "cards": dealer_cards,
                "total": dealer_total,
                "busted": self.dealer.busted if self.status == "finished" else False,
                "blackjack": self.dealer.blackjack if self.status == "finished" else False,
            },
            "current_player": self.players[self.current_player_index].name if self.players and self.status == "in_progress" else None,
            "winner": self.winner
        }
