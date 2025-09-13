from flask import Flask, request, jsonify, render_template
from .gameSession import GameSession
import random
import string
from datetime import datetime, timedelta
import os

# Get the base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# Initialize Flask app
app = Flask(__name__, 
            template_folder=TEMPLATE_DIR,
            static_folder=STATIC_DIR)

# In-memory storage for active game sessions
active_sessions = {}

# Clean up old sessions that are older than 24 hours
def cleanup_old_sessions():
    current_time = datetime.utcnow()
    expired_sessions = [
        session_id for session_id, session in active_sessions.items()
        if current_time - session.created_at > timedelta(hours=24)
    ]
    for session_id in expired_sessions:
        del active_sessions[session_id]

# Generate a random session ID
def generate_session_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    cleanup_old_sessions()
    return jsonify({
        'sessions': [
            {
                'session_id': session_id,
                'creator': session.creator,
                'player_count': len(session.players),
                'max_players': session.max_players,
                'status': session.status,
                'created_at': session.created_at.isoformat()
            }
            for session_id, session in active_sessions.items()
        ]
    })

@app.route('/api/sessions', methods=['POST'])
def create_session():
    data = request.json
    creator_name = data.get('creator_name')
    max_players = int(data.get('max_players', 5))
    
    if not creator_name:
        return jsonify({'error': 'Creator name is required'}), 400
    
    session_id = generate_session_id()
    while session_id in active_sessions:
        session_id = generate_session_id()
    
    session = GameSession(session_id, creator_name, max_players)
    session.add_player(creator_name)
    active_sessions[session_id] = session
    
    return jsonify({
        'session_id': session_id,
        'message': f'Session created with ID: {session_id}'
    }), 201

@app.route('/api/sessions/<session_id>/join', methods=['POST'])
def join_session(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    data = request.json
    player_name = data.get('player_name')
    
    if not player_name:
        return jsonify({'error': 'Player name is required'}), 400
    
    if session.status != 'waiting':
        return jsonify({'error': 'Game has already started'}), 400
    
    if not session.add_player(player_name):
        return jsonify({'error': 'Could not add player (name might be taken or session is full)'}), 400
    
    return jsonify({
        'message': f'Player {player_name} joined session {session_id}',
        'session_status': session.status,
        'player_count': len(session.players)
    })

@app.route('/api/sessions/<session_id>/start', methods=['POST'])
def start_session(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    
    if session.status != 'waiting':
        return jsonify({'error': 'Game has already started or finished'}), 400
    
    if not session.start_game():
        return jsonify({'error': 'Not enough players to start the game'}), 400
    
    return jsonify({
        'message': 'Game started!',
        'game_state': session.get_game_state()
    })

@app.route('/api/sessions/<session_id>/status', methods=['GET'])
def get_session_status(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify(active_sessions[session_id].get_game_state())

@app.route('/api/sessions/<session_id>/hit', methods=['POST'])
def hit(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    data = request.json
    player_name = data.get('player_name')
    
    if not player_name:
        return jsonify({'error': 'Player name is required'}), 400
    
    current_player = session.get_current_player()
    if not current_player or current_player.name.lower() != player_name.lower():
        return jsonify({'error': 'Not your turn'}), 400
    
    # Player hits
    current_player.hit(session.deck.pop())
    
    message = f"{player_name} hits and has {current_player.total}"
    
    # Check if player has blackjack or busted
    if current_player.blackjack:
        message = f"{player_name} has Blackjack with {current_player.total}!"
        # Move to next player
        if not session.next_turn():
            # Game is over, dealer's turn
            session.determine_winners()
        return jsonify({
            'message': message,
            'game_state': session.get_game_state()
        })
    elif current_player.busted:
        message = f"{player_name} busted with {current_player.total}!"
        # Move to next player
        if not session.next_turn():
            # Game is over, dealer's turn
            session.determine_winners()
        return jsonify({
            'message': message,
            'game_state': session.get_game_state()
        })
    
    return jsonify({
        'message': message,
        'game_state': session.get_game_state()
    })

@app.route('/api/sessions/<session_id>/stand', methods=['POST'])
def stand(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    data = request.json
    player_name = data.get('player_name')
    
    if not player_name:
        return jsonify({'error': 'Player name is required'}), 400
    
    current_player = session.get_current_player()
    if not current_player or current_player.name.lower() != player_name.lower():
        return jsonify({'error': 'Not your turn'}), 400
    
    # Move to next player or dealer's turn
    should_continue = session.next_turn()
    
    # If game is over, determine winners
    if not should_continue:
        session.determine_winners()
    
    # Get the updated game state
    game_state = session.get_game_state()
    
    if not should_continue:
        # Game is over, show results
        return jsonify({
            'message': f"{player_name} stands. Dealer's turn.",
            'game_state': game_state
        })
    else:
        # Game continues with next player
        next_player = session.get_current_player()
        return jsonify({
            'message': f"{player_name} stands. {next_player.name}'s turn.",
            'game_state': game_state
        })

@app.route('/api/sessions/<session_id>/reset', methods=['POST'])
def reset_session(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    
    # Store player chips before resetting
    player_chips = {player.name: player.chips for player in session.players}
    
    # Reset the session
    session.__init__(session_id, session.creator, session.max_players)
    
    # Re-add all players with their chips
    for player_name, chips in player_chips.items():
        session.add_player(player_name, chips)
    
    # Start a new game
    session.start_game()
    
    return jsonify({
        'message': 'New round started!',
        'game_state': session.get_game_state()
    })

if __name__ == '__main__':
    app.run(debug=True)
