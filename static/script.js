// Game state
let currentGame = {
    id: null,
    playerName: '',
    playerToken: '',
    hostToken: '',
    isCreator: false,
    currentPlayer: null,
    players: [],
    dealer: {
        cards: [],
        total: 0
    },
    status: 'waiting' // waiting, betting, in_progress, finished
};
let lastAnnouncedWinner = null;
let dealerAnimationId = 0;
let dealerResultKey = null;
let inlineMessageTimer = null;
let pollingGame = false;
let pollingLobby = false;
let pollFailures = 0;
let nextPollAt = 0;
let actionPending = false;
let actionEpoch = 0;
let lastGameState = null;
let lastRenderedState = '';

function pollDelay() {
    return ['in_progress', 'betting'].includes(currentGame.status) ? 500 :
        currentGame.status === 'waiting' ? 1000 : 2500;
}

async function runAction(action, button) {
    if (actionPending) return;
    actionPending = true;
    actionEpoch += 1;
    const label = button.textContent;
    button.textContent = 'Working…';
    const buttons = [createGameBtn, joinGameBtn, startGameBtn, placeBetBtn, hitBtn, standBtn, newRoundBtn];
    buttons.forEach(control => { control.disabled = true; });
    try {
        await action();
    } finally {
        actionPending = false;
        actionEpoch += 1;
        button.textContent = label;
        buttons.forEach(control => { control.disabled = false; });
        if (lastGameState) updateGameControls(lastGameState);
        nextPollAt = 0;
        pollGameState();
    }
}

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
const bettingControls = document.getElementById('bettingControls');
const betAmountInput = document.getElementById('betAmount');
const placeBetBtn = document.getElementById('placeBetBtn');
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
    for (const [button, action] of [[createGameBtn, createGame], [joinGameBtn, joinGame],
        [startGameBtn, startGame], [hitBtn, hit], [standBtn, stand],
        [newRoundBtn, startNewRound], [placeBetBtn, placeBet]]) {
        button.addEventListener('click', () => runAction(action, button));
    }
    
    // Check for game ID in URL
    const urlParams = new URLSearchParams(window.location.search);
    const gameId = urlParams.get('game');
    if (gameId) {
        gameIdInput.value = gameId;
        restoreIdentity(gameId);
    }
    
    // Poll for game updates
    setInterval(pollGameState, 100);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            nextPollAt = 0;
            pollGameState();
            updateAvailableGames();
        }
    });
});

// API Functions
async function createGame() {
    const playerName = playerNameInput.value.trim();
    if (!playerName) {
        showInlineMessage('Please enter your name');
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
            currentGame.playerToken = data.player_token;
            currentGame.hostToken = data.host_token;
            currentGame.isCreator = true;
            currentGameId.textContent = data.session_id;
            
            // Update URL with game ID
            window.history.pushState({}, '', `?game=${data.session_id}`);
            saveIdentity();
            
            // Show game section
            showGameSection();
            
            // Start polling for game updates
            pollGameState();
        } else {
            showInlineMessage(data.error || 'Failed to create game');
        }
    } catch (error) {
        console.error('Error creating game:', error);
        showInlineMessage('Failed to connect to server');
    }
}

async function joinGame() {
    const playerName = playerNameInput.value.trim();
    const gameId = gameIdInput.value.trim();
    
    if (!playerName) {
        showInlineMessage('Please enter your name');
        return;
    }
    
    if (!gameId) {
        showInlineMessage('Please enter a game ID');
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
            currentGame.playerToken = data.player_token;
            currentGame.hostToken = '';
            currentGame.isCreator = false;
            currentGameId.textContent = gameId;
            
            // Update URL with game ID
            window.history.pushState({}, '', `?game=${gameId}`);
            saveIdentity();
            
            // Show game section
            showGameSection();
            
            // Start polling for game updates
            pollGameState();
        } else {
            showInlineMessage(data.error || 'Failed to join game');
        }
    } catch (error) {
        console.error('Error joining game:', error);
        showInlineMessage('Failed to connect to server');
    }
}

async function startGame() {
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/start`, {
            method: 'POST',
            headers: { 'X-Host-Token': currentGame.hostToken }
        });

        const data = await response.json();
        if (response.ok) {
            updateGameUI(data.game_state);
            showMessage(data.message);
        } else {
            showInlineMessage(data.error || 'Failed to start game');
        }
    } catch (error) {
        console.error('Error starting game:', error);
        showInlineMessage('Failed to start game');
    }
}

async function placeBet() {
    const amount = Number(betAmountInput.value);
    if (!Number.isInteger(amount) || amount <= 0) {
        showInlineMessage('Enter a positive whole-chip bet');
        return;
    }

    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/bet`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Player-Token': currentGame.playerToken
            },
            body: JSON.stringify({ amount })
        });
        const data = await response.json();
        if (response.ok) {
            updateGameUI(data.game_state);
            showMessage(data.message);
        } else {
            showInlineMessage(data.error || 'Failed to place bet');
        }
    } catch (error) {
        console.error('Error placing bet:', error);
        showInlineMessage('Failed to connect to server');
    }
}

async function hit() {
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/hit`, {
            method: 'POST',
            headers: { 'X-Player-Token': currentGame.playerToken }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateGameUI(data.game_state);
            
        } else {
            const data = await response.json();
            showInlineMessage(data.error || 'Failed to hit');
        }
    } catch (error) {
        console.error('Error hitting:', error);
        showInlineMessage('Failed to connect to server');
    }
}

async function stand() {
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/stand`, {
            method: 'POST',
            headers: { 'X-Player-Token': currentGame.playerToken }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateGameUI(data.game_state);
            
        } else {
            const data = await response.json();
            showInlineMessage(data.error || 'Failed to stand');
        }
    } catch (error) {
        console.error('Error standing:', error);
        showInlineMessage('Failed to connect to server');
    }
}

async function startNewRound() {
    try {
        const response = await fetch(`/api/sessions/${currentGame.id}/reset`, {
            method: 'POST',
            headers: { 'X-Host-Token': currentGame.hostToken }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateGameUI(data.game_state);
            showMessage(data.message || 'New round started!');
            // The polling mechanism will automatically update the UI with the new game state
        } else {
            const data = await response.json();
            showInlineMessage(data.error || 'Failed to start new round', 5000);
        }
    } catch (error) {
        console.error('Error starting new round:', error);
        showInlineMessage('Failed to connect to server', 5000);
    }
}

// UI Elements
const newRoundContainer = document.querySelector('.new-round-container');

// UI Update Functions
function showGameSection() {
    lobbySection.classList.add('hidden');
    gameSection.classList.remove('hidden');
}

function identityKey(gameId) {
    return `blackjack:${gameId}`;
}

function saveIdentity() {
    sessionStorage.setItem(identityKey(currentGame.id), JSON.stringify({
        playerName: currentGame.playerName,
        playerToken: currentGame.playerToken,
        hostToken: currentGame.hostToken
    }));
}

function restoreIdentity(gameId) {
    try {
        const saved = JSON.parse(sessionStorage.getItem(identityKey(gameId)) || 'null');
        if (!saved || !saved.playerToken) return;
        currentGame.id = gameId;
        currentGame.playerName = saved.playerName;
        currentGame.playerToken = saved.playerToken;
        currentGame.hostToken = saved.hostToken || '';
        currentGame.isCreator = Boolean(saved.hostToken);
        currentGameId.textContent = gameId;
        playerNameInput.value = saved.playerName;
        showGameSection();
        pollGameState();
    } catch (error) {
        console.error('Unable to restore game identity:', error);
    }
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

function showInlineMessage(message, duration = 3000) {
    gameMessage.textContent = message;
    gameMessage.classList.remove('hidden');
    clearTimeout(inlineMessageTimer);
    inlineMessageTimer = setTimeout(() => {
        gameMessage.classList.add('hidden');
    }, duration);
}

function updateGameUI(gameState) {
    const signature = JSON.stringify(gameState);
    if (signature === lastRenderedState) return;
    lastRenderedState = signature;
    lastGameState = gameState;
    // Update game status
    currentGame.status = gameState.status;
    gameStatus.textContent = gameState.status.replace('_', ' ');
    playerCount.textContent = gameState.players.length;
    maxPlayers.textContent = gameState.max_players;
    
    // Update dealer
    updateDealerUI(gameState.dealer, gameState.status, () => {
        announceWinner(gameState.winner);
    });
    
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

    const localPlayer = gameState.players.find(p => p.name === currentGame.playerName);
    const canPlaceBet = gameState.status === 'betting' && localPlayer && localPlayer.can_bet;
    bettingControls.classList.toggle('hidden', !canPlaceBet);
    if (canPlaceBet) {
        betAmountInput.max = localPlayer.chips;
        betAmountInput.value = Math.min(Number(betAmountInput.value) || 10, localPlayer.chips);
    }
    
    // Show new round button if game is finished
    if (gameState.status === 'finished' && currentGame.isCreator) {
        newRoundContainer.classList.remove('hidden');
        newRoundBtn.classList.remove('hidden');
    } else {
        lastAnnouncedWinner = null;
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
        const gameSection = document.getElementById('game');
        
        if (existingMessages) {
            existingMessages.replaceWith(messagesDiv);
        } else if (gameSection) {
            gameSection.appendChild(messagesDiv);
        }
    } else {
        document.querySelector('.game-messages')?.remove();
    }
}

function announceWinner(winner) {
    if (!winner || winner === lastAnnouncedWinner) return;
    lastAnnouncedWinner = winner;
    showMessage(winner, 5000);
}

function updateDealerUI(dealer, status, onRevealComplete) {
    if (status !== 'finished') {
        dealerAnimationId += 1;
        dealerResultKey = null;
        renderDealerCards(dealer.cards, Math.min(2, dealer.cards.length), false);
        return;
    }

    const resultKey = `${dealer.cards.join(',')}|${dealer.total}`;
    if (dealerResultKey === resultKey) return;

    dealerResultKey = resultKey;
    const animationId = ++dealerAnimationId;
    const initialCardCount = Math.min(2, dealer.cards.length);

    // Preserve the in-progress view briefly, reveal the hole card, then add
    // each dealer hit separately so every client can follow the turn.
    renderDealerCards(dealer.cards, initialCardCount, false);
    const revealSteps = [initialCardCount];
    for (let count = initialCardCount + 1; count <= dealer.cards.length; count += 1) {
        revealSteps.push(count);
    }

    revealSteps.forEach((visibleCount, index) => {
        setTimeout(() => {
            if (animationId !== dealerAnimationId) return;
            renderDealerCards(dealer.cards, visibleCount, true);
            if (index === revealSteps.length - 1) onRevealComplete();
        }, 200 + (index * 250));
    });
}

function renderDealerCards(cards, visibleCount, revealHoleCard) {
    dealerCards.innerHTML = '';
    const visibleCards = cards.slice(0, visibleCount);

    visibleCards.forEach((card, index) => {
        const cardText = index === 0 && !revealHoleCard ? '🂠' : formatCard(card);
        dealerCards.appendChild(createCardElement(cardText));
    });

    if (!revealHoleCard && cards.length > 0) {
        const visibleCard = cards.length > 1 ? cards[1] : cards[0];
        dealerTotal.innerHTML = `Total: <span>${getCardValue(visibleCard)} + ?</span>`;
    } else if (visibleCards.length > 0) {
        dealerTotal.innerHTML = `Total: <span>${calculateHandTotal(visibleCards)}</span>`;
    } else {
        dealerTotal.innerHTML = 'Total: <span>0</span>';
    }
}

function calculateHandTotal(cards) {
    let total = 0;
    let aces = 0;
    cards.forEach(card => {
        const value = card.slice(0, -1);
        if (value === 'A') {
            total += 11;
            aces += 1;
        } else if (['K', 'Q', 'J'].includes(value)) {
            total += 10;
        } else {
            total += Number(value);
        }
    });
    while (total > 21 && aces > 0) {
        total -= 10;
        aces -= 1;
    }
    return total;
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

        const betElement = document.createElement('div');
        betElement.className = 'player-bet';
        betElement.textContent = player.bet > 0 ? `Bet: ${player.bet}` : '';
        
        playerElement.appendChild(playerName);
        playerElement.appendChild(cardsContainer);
        playerElement.appendChild(totalElement);
        playerElement.appendChild(chipsElement);
        playerElement.appendChild(betElement);
        
        playersArea.appendChild(playerElement);
    });
}

function updateGameControls(gameState) {
    const currentPlayer = gameState.players.find(p => p.name === currentGame.playerName);
    const isCurrentTurn = gameState.players.some(p => p.is_current && p.name === currentGame.playerName);
    
    if (currentPlayer) {
        // Disable buttons if it's not the player's turn, or if they've busted or have blackjack
        const shouldDisable = actionPending || !isCurrentTurn || currentPlayer.busted || currentPlayer.blackjack || gameState.status !== 'in_progress';
        
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
    if (!currentGame.id || document.hidden || actionPending || pollingGame || Date.now() < nextPollAt) return;
    pollingGame = true;
    const requestedGame = currentGame.id;
    const requestedEpoch = actionEpoch;
    
    try {
        const response = await fetch(`/api/sessions/${requestedGame}/status`);
        if (requestedGame !== currentGame.id || requestedEpoch !== actionEpoch) return;
        
        if (response.ok) {
            const gameState = await response.json();
            if (requestedGame !== currentGame.id || requestedEpoch !== actionEpoch) return;
            pollFailures = 0;
            currentGame.status = gameState.status;
            nextPollAt = Date.now() + pollDelay();
            updateGameUI(gameState);
        } else if (response.status === 404) {
            // Stop polling a session that no longer exists. Without this, the
            // two-second timer keeps generating identical 404s indefinitely.
            currentGame.id = null;
            lobbySection.classList.remove('hidden');
            gameSection.classList.add('hidden');
            window.history.replaceState({}, '', window.location.pathname);
            showInlineMessage('This session no longer exists or has expired. Please create or join another game.', 5000);
        } else {
            throw new Error('Session status temporarily unavailable');
        }
    } catch (error) {
        if (requestedGame !== currentGame.id || requestedEpoch !== actionEpoch) return;
        console.error('Error polling game state:', error);
        pollFailures += 1;
        nextPollAt = Date.now() + Math.min(30000, 2000 * (2 ** Math.min(pollFailures, 4)));
        showInlineMessage('Connection interrupted. Reconnecting to your game…', 5000);
    } finally {
        pollingGame = false;
    }
}

// Initialize available games list
async function updateAvailableGames() {
    if (currentGame.id || document.hidden || pollingLobby) return;
    pollingLobby = true;
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `Unable to list sessions (${response.status})`);
        }
        
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
                const details = document.createElement('div');
                const title = document.createElement('strong');
                title.textContent = `${session.creator}'s Game`;
                const count = document.createElement('small');
                count.textContent = `Players: ${session.player_count}/${session.max_players}`;
                details.append(title, document.createElement('br'), count);

                const joinButton = document.createElement('button');
                joinButton.className = 'btn btn-small';
                joinButton.textContent = 'Join';
                joinButton.addEventListener('click', (e) => {
                    e.stopPropagation();
                    gameIdInput.value = session.session_id;
                    runAction(joinGame, joinGameBtn);
                });

                gameElement.append(details, joinButton);
                availableGames.appendChild(gameElement);
            }
        });
    } catch (error) {
        console.error('Error fetching available games:', error);
        document.getElementById('availableGames').textContent = 'Games are temporarily unavailable. Retrying shortly…';
    } finally {
        pollingLobby = false;
    }
}

// Update available games list periodically
setInterval(updateAvailableGames, 15000);
updateAvailableGames();
