from datetime import datetime, timezone
import random
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
        self.status = "waiting"  # waiting, in_progress, finished
        self.max_players = max_players
        self.creator = creator_name
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

    def add_player(self, player_name: str, chips: int = 100) -> bool:
        """Add a player to the session if there's space and name is available."""
        if len(self.players) >= self.max_players:
            return False
        
        if any(p.name.lower() == player_name.lower() for p in self.players):
            return False
            
        self.players.append(Player(player_name, chips))
        return True

    def remove_player(self, player_name: str) -> bool:
        """Remove a player from the session."""
        for i, player in enumerate(self.players):
            if player.name.lower() == player_name.lower():
                self.players.pop(i)
                if self.current_player_index >= len(self.players):
                    self.current_player_index = 0
                return True
        return False

    def start_game(self) -> bool:
        """Start the game if there are enough players."""
        if len(self.players) < 1:
            return False
            
        self.status = "in_progress"
        self.current_player_index = 0
        self.deck = self.initialize_deck()
        random.shuffle(self.deck)
        
        # Reset player hands but keep their chips
        for player in self.players:
            player.cards = []
            player.total = 0
            player.busted = False
            player.blackjack = False
            player.bet = 10  # Default bet for each round
            player.chips -= player.bet  # Deduct bet from chips
        
        # Reset dealer
        self.dealer = Dealer()
        
        # Deal initial cards
        self.deal_initial_cards()
        return True

    def deal_initial_cards(self) -> None:
        """Deal initial cards to all players and the dealer."""
        self.deck = self.initialize_deck()
        random.shuffle(self.deck)
        
        # Deal two cards to each player
        for _ in range(2):
            for player in self.players:
                player.hit(self.deck.pop())
            self.dealer.hit(self.deck.pop())

    def get_current_player(self) -> Optional[Player]:
        """Get the player whose turn it is."""
        if not self.players or self.current_player_index >= len(self.players):
            return None
        return self.players[self.current_player_index]

    def next_turn(self) -> bool:
        """Move to the next player's turn. Returns True if game should continue."""
        self.current_player_index += 1
        
        if self.current_player_index >= len(self.players):
            self.current_player_index = 0
            self.dealer_turn()
            self.determine_winners()
            self.status = "finished"
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
                self.add_game_message(f"{player.name} busted and lost their bet!")
            elif dealer_busted:
                # Dealer busted, all remaining players win 1:1
                winnings = player.win_bet(1)  # 1:1 payout
                self.add_game_message(f"Dealer busted! {player.name} wins {winnings} chips!")
            elif player.blackjack:
                if dealer_blackjack:
                    # Both have blackjack, push
                    player.chips += player.bet
                    player.bet = 0
                    self.add_game_message(f"Both have blackjack! {player.name} pushes.")
                else:
                    # Player has blackjack, dealer doesn't - 3:2 payout
                    winnings = player.win_bet(1.5)  # 3:2 payout
                    self.add_game_message(f"Blackjack! {player.name} wins {winnings} chips!")
            elif dealer_blackjack:
                # Dealer has blackjack, player doesn't
                player.lose_bet()
                self.add_game_message(f"Dealer has blackjack! {player.name} loses their bet!")
            elif player.total > dealer_total:
                # Player beats dealer - 1:1 payout
                winnings = player.win_bet(1)
                self.add_game_message(f"{player.name} wins {winnings} chips!")
            elif player.total == dealer_total:
                # Push - return bet
                player.chips += player.bet
                player.bet = 0
                self.add_game_message(f"{player.name} pushes and gets their bet back")
            else:
                # Player loses to dealer
                player.lose_bet()
                self.add_game_message(f"{player.name} loses their bet!")
        
        # Reset bets for the next round
        for player in self.players:
            player.bet = 0
            
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
        return {
            "session_id": self.session_id,
            "status": self.status,
            "messages": self.messages,
            "players": [{
                "name": p.name,
                "cards": p.cards,
                "total": p.total,
                "chips": p.chips,
                "busted": p.busted,
                "blackjack": p.blackjack,
                "is_current": (i == self.current_player_index and self.status == "in_progress")
            } for i, p in enumerate(self.players)],
            "dealer": {
                "cards": self.dealer.cards,
                "total": self.dealer.total,
                "busted": self.dealer.busted,
                "blackjack": self.dealer.blackjack
            },
            "current_player": self.players[self.current_player_index].name if self.players and self.status == "in_progress" else None,
            "winner": self.winner
        }