// Game state
let currentGame = {
    id: null,
    playerName: '',
    isCreator: false,
    currentPlayer: null,
    players: [],
    dealer: {
        cards: [],
        total: 0
    },
    status: 'waiting' // waiting, in_progress, finished
};

// DOM Elements
const lobbySection = document.getElementById('lobby');
const gameSection = document.getElementById('game');
const playerNameInput = document.getElementById('playerName');
const gameIdInput = document.getElementById('gameId');
const createGameBtn = document.getElementById('createGame');
const joinGameBtn = document.getElementById('joinGame');
const startGameBtn = document.getElementById('startGame');
const hitBtn = document.getElementById('hitBtn');
const standBtn = document.getElementById('standBtn');
const newRoundBtn = document.getElementById('newRoundBtn');
const gameMessage = document.getElementById('gameMessage');
const playersArea = document.getElementById('playersArea');
const dealerCards = document.getElementById('dealerCards');
const dealerTotal = document.getElementById('dealerTotal');
const gameStatus = document.getElementById('gameStatus');
const playerCount = document.getElementById('playerCount');
const maxPlayers = document.getElementById('maxPlayers');
const currentGameId = document.getElementById('currentGameId');

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    createGameBtn.addEventListener('click', createGame);
    joinGameBtn.addEventListener('click', joinGame);
    startGameBtn.addEventListener('click', startGame);
    hitBtn.addEventListener('click', hit);
    standBtn.addEventListener('click', stand);
    newRoundBtn.addEventListener('click', startNewRound);
    
    // Check for game ID in URL
    const urlParams = new URLSearchParams(window.location.search);
    const gameId = urlParams.get('game');
    if (gameId) {
        gameIdInput.value = gameId;
    }
    
    // Poll for game updates
    setInterval(pollGameState, 2000);
});

// API Functions
async function createGame() {
    const playerName = playerNameInput.value.trim();
    if (!playerName) {
        showMessage('Please enter your name');
        return;
    }
    
    try {
        const response = await fetch('/api/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ creator_name: playerName })
        });
        
        const data = await response.json();
        
        if (response.status === 201) {
            currentGame.id = data.session_id;
            currentGame.playerName = playerName;
            currentGame.isCreator = true;
            currentGameId.textContent = data.session_id;
            
            // Update URL with game ID
            window.history.pushState({}, '', `?game=${data.session_id}`);
            
            // Show game section
            showGameSection();
            
            // Start polling for game updates
            pollGameState();
        } else {
            showMessage(data.error || 'Failed to create game');
        }
    } catch (error) {
        console.error('Error creating game:', error);
        showMessage('Failed to connect to server');
    }
}

async function joinGame() {
    const playerName = playerNameInput.value.trim();
    const gameId = gameIdInput.value.trim();
    
    if (!playerName) {
        showMessage('Please enter your name');
        return;
    }
    
    if (!gameId) {
        showMessage('Please enter a game ID');
        return;
    }
    
    try {
        const response = await fetch(`/api/sessions/${gameId}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_name: playerName })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentGame.id = gameId;
            currentGame.playerName = playerName;
            currentGameId.textContent = gameId;
            
            // Update URL with game ID
            window.history.pushState({}, '', `?game=${gameId}`);
            
            // Show game section
            showGameSection();
            
            // Start polling for game updates
            pollGameState();
        } else {
            showMessage(data.error || 'Failed to join game');
        }
    } catch (error) {
        console.error('Error joining game:', error);
        showMessage('Failed to connect to server');
    }
}

async function startGame() {
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const data = await response.json();
            showMessage(data.error || 'Failed to start game');
        }
    } catch (error) {
        console.error('Error starting game:', error);
        showMessage('Failed to start game');
    }
}

async function hit() {
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/hit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_name: currentGame.playerName })
        });
        
        if (response.ok) {
            const data = await response.json();
            updateGameUI(data.game_state);
            
            // Show message from server if available
            if (data.message) {
                showMessage(data.message, 3000);
            }
            
            // Check if the game is over
            if (data.game_state.status === 'finished') {
                showMessage('Round over!', 3000);
            }
        } else {
            const data = await response.json();
            showMessage(data.error || 'Failed to hit', 3000);
        }
    } catch (error) {
        console.error('Error hitting:', error);
        showMessage('Failed to connect to server', 3000);
    }
}

async function stand() {
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/stand`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_name: currentGame.playerName })
        });
        
        if (response.ok) {
            const data = await response.json();
            updateGameUI(data.game_state);
            
            // Show appropriate message
            if (data.message) {
                showMessage(data.message, 3000);
            }
        } else {
            const data = await response.json();
            showMessage(data.error || 'Failed to stand', 3000);
        }
    } catch (error) {
        console.error('Error standing:', error);
        showMessage('Failed to connect to server', 3000);
    }
}

async function startNewRound() {
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            const data = await response.json();
            showMessage(data.message || 'New round started!');
            // The polling mechanism will automatically update the UI with the new game state
        } else {
            const data = await response.json();
            showMessage(data.error || 'Failed to start new round', 5000);
        }
    } catch (error) {
        console.error('Error starting new round:', error);
        showMessage('Failed to connect to server', 5000);
    }
}

// UI Elements
const newRoundContainer = document.querySelector('.new-round-container');

// UI Update Functions
function showGameSection() {
    lobbySection.classList.add('hidden');
    gameSection.classList.remove('hidden');
}

function showMessage(message, duration = 3000) {
    // Create a new message element
    const messageEl = document.createElement('div');
    messageEl.className = 'floating-message show';
    messageEl.textContent = message;
    
    // Add to the body
    document.body.appendChild(messageEl);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            messageEl.classList.remove('show');
            // Remove from DOM after animation
            setTimeout(() => {
                if (messageEl.parentNode) {
                    messageEl.parentNode.removeChild(messageEl);
                }
            }, 300);
        }, duration);
    }
    
    return messageEl;
}

function updateGameUI(gameState) {
    // Update game status
    gameStatus.textContent = gameState.status;
    playerCount.textContent = gameState.players.length;
    
    // Update dealer
    updateDealerUI(gameState.dealer);
    
    // Update players
    updatePlayersUI(gameState.players);
    
    // Update game controls based on current player
    updateGameControls(gameState);
    
    // Show/hide start game button for creator
    if (currentGame.isCreator && gameState.status === 'waiting') {
        startGameBtn.classList.remove('hidden');
    } else {
        startGameBtn.classList.add('hidden');
    }
    
    // Show/hide game controls
    if (gameState.status === 'in_progress') {
        const currentPlayer = gameState.players.find(p => p.is_current);
        if (currentPlayer && currentPlayer.name === currentGame.playerName) {
            document.getElementById('gameControls').classList.remove('hidden');
        } else {
            document.getElementById('gameControls').classList.add('hidden');
        }
    } else {
        document.getElementById('gameControls').classList.add('hidden');
    }
    
    // Show new round button if game is finished
    if (gameState.status === 'finished') {
        newRoundContainer.classList.remove('hidden');
        newRoundBtn.classList.remove('hidden');
        // Only show the last message if it's not already showing
        if (gameState.messages && gameState.messages.length > 0) {
            const lastMessage = gameState.messages[gameState.messages.length - 1];
            // Only show if it's a game result message (not a chip update)
            if (lastMessage.includes('wins') || lastMessage.includes('bust') || lastMessage.includes('Blackjack')) {
                showMessage(lastMessage, 5000);
            }
        }
    } else {
        newRoundContainer.classList.add('hidden');
        newRoundBtn.classList.add('hidden');
    }
    
    // Update game messages if available
    if (gameState.messages && gameState.messages.length > 0) {
        const messagesDiv = document.createElement('div');
        messagesDiv.className = 'game-messages';
        
        // Only take the most recent 5 messages to avoid clutter
        const recentMessages = [...new Set(gameState.messages)].slice(-5);
        
        recentMessages.forEach(msg => {
            // Skip duplicate messages about the same player's turn
            if (msg.includes('turn') && messagesDiv.textContent.includes(msg.split("'s turn")[0])) {
                return;
            }
            
            const msgEl = document.createElement('div');
            msgEl.className = 'game-message';
            // Remove timestamp if present
            const cleanMsg = msg.replace(/^\[\d{2}:\d{2}:\d{2}\]\s*/, '');
            msgEl.textContent = cleanMsg;
            messagesDiv.prepend(msgEl);
        });
        
        const existingMessages = document.querySelector('.game-messages');
        const gameSection = document.querySelector('.game-section');
        
        if (existingMessages) {
            existingMessages.replaceWith(messagesDiv);
        } else if (gameSection) {
            gameSection.appendChild(messagesDiv);
        }
    }
}

function updateDealerUI(dealer) {
    dealerCards.innerHTML = '';
    
    // Show all dealer cards if game is finished, otherwise hide the first card
    const showAllCards = currentGame.status === 'finished';
    
    dealer.cards.forEach((card, index) => {
        if (index === 0 && !showAllCards) {
            // Show card back for first card if game is in progress
            const cardElement = createCardElement('🂠');
            dealerCards.appendChild(cardElement);
        } else {
            const cardElement = createCardElement(formatCard(card));
            dealerCards.appendChild(cardElement);
        }
    });
    
    // Update dealer total
    if (showAllCards) {
        dealerTotal.innerHTML = `Total: <span>${dealer.total}</span>`;
    } else if (dealer.cards.length > 0) {
        // Only show the value of the visible card
        const visibleCard = dealer.cards[0];
        const cardValue = getCardValue(visibleCard);
        dealerTotal.innerHTML = `Total: <span>${cardValue} + ?</span>`;
    } else {
        dealerTotal.innerHTML = 'Total: <span>0</span>';
    }
}

function updatePlayersUI(players) {
    playersArea.innerHTML = '';
    
    players.forEach(player => {
        const playerElement = document.createElement('div');
        playerElement.className = `player-area ${player.is_current ? 'current-turn' : ''}`;
        
        const playerName = document.createElement('div');
        playerName.className = 'player-name';
        playerName.textContent = player.name;
        
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'cards';
        
        player.cards.forEach(card => {
            const cardElement = createCardElement(formatCard(card));
            cardsContainer.appendChild(cardElement);
        });
        
        const totalElement = document.createElement('div');
        totalElement.className = 'total';
        totalElement.innerHTML = `Total: <span>${player.total}</span>`;
        
        const chipsElement = document.createElement('div');
        chipsElement.className = 'chips';
        chipsElement.textContent = `Chips: ${player.chips}`;
        
        playerElement.appendChild(playerName);
        playerElement.appendChild(cardsContainer);
        playerElement.appendChild(totalElement);
        playerElement.appendChild(chipsElement);
        
        playersArea.appendChild(playerElement);
    });
}

function updateGameControls(gameState) {
    const currentPlayer = gameState.players.find(p => p.name === currentGame.playerName);
    const isCurrentTurn = gameState.players.some(p => p.is_current && p.name === currentGame.playerName);
    
    if (currentPlayer) {
        // Disable buttons if it's not the player's turn, or if they've busted or have blackjack
        const shouldDisable = !isCurrentTurn || currentPlayer.busted || currentPlayer.blackjack || gameState.status !== 'in_progress';
        
        hitBtn.disabled = shouldDisable;
        standBtn.disabled = shouldDisable;
        
        // Add/remove disabled class for styling
        if (shouldDisable) {
            hitBtn.classList.add('disabled');
            standBtn.classList.add('disabled');
        } else {
            hitBtn.classList.remove('disabled');
            standBtn.classList.remove('disabled');
        }
    } else {
        // Player not found in game
        hitBtn.disabled = true;
        standBtn.disabled = true;
        hitBtn.classList.add('disabled');
        standBtn.classList.add('disabled');
    }
}

// Helper Functions
function createCardElement(cardText) {
    const card = document.createElement('div');
    card.className = 'card';
    
    // Check if card is a heart or diamond (red)
    if (cardText.includes('♥') || cardText.includes('♦')) {
        card.classList.add('red');
    }
    
    card.textContent = cardText;
    return card;
}

function formatCard(card) {
    // Convert card string to emoji (e.g., 'AH' -> 'A♥')
    const suit = card.slice(-1);
    const value = card.slice(0, -1);
    
    let suitSymbol = '';
    switch(suit) {
        case 'H': suitSymbol = '♥'; break;
        case 'D': suitSymbol = '♦'; break;
        case 'C': suitSymbol = '♣'; break;
        case 'S': suitSymbol = '♠'; break;
        default: suitSymbol = suit;
    }
    
    return value + suitSymbol;
}

function getCardValue(card) {
    // Extract the value part (without suit)
    const value = card.slice(0, -1);
    
    if (['K', 'Q', 'J'].includes(value)) {
        return 10;
    } else if (value === 'A') {
        return 11; // Simplified for dealer's visible card
    } else {
        return parseInt(value) || 0;
    }
}

// Polling Functions
async function pollGameState() {
    if (!currentGame.id) return;
    
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/status`);
        
        if (response.ok) {
            const gameState = await response.json();
            currentGame.status = gameState.status;
            updateGameUI(gameState);
        }
    } catch (error) {
        console.error('Error polling game state:', error);
    }
}

// Initialize available games list
async function updateAvailableGames() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        
        const availableGames = document.getElementById('availableGames');
        availableGames.innerHTML = '';
        
        if (data.sessions.length === 0) {
            availableGames.innerHTML = '<p>No games available. Create one!</p>';
            return;
        }
        
        data.sessions.forEach(session => {
            if (session.status === 'waiting') {
                const gameElement = document.createElement('div');
                gameElement.className = 'available-game';
                gameElement.innerHTML = `
                    <div>
                        <strong>${session.creator}'s Game</strong><br>
                        <small>Players: ${session.player_count}/${session.max_players}</small>
                    </div>
                    <button class="btn btn-small" data-id="${session.session_id}">Join</button>
                `;
                
                gameElement.querySelector('button').addEventListener('click', (e) => {
                    e.stopPropagation();
                    gameIdInput.value = session.session_id;
                    joinGame();
                });
                
                availableGames.appendChild(gameElement);
            }
        });
    } catch (error) {
        console.error('Error fetching available games:', error);
    }
}

// Update available games list periodically
setInterval(updateAvailableGames, 5000);
updateAvailableGames();
