from flask import Flask, request, jsonify, render_template
from .gameSession import GameSession
import secrets
import string
from datetime import datetime, timedelta, timezone
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
    current_time = datetime.now(timezone.utc)
    expired_sessions = [
        session_id for session_id, session in active_sessions.items()
        if current_time - session.created_at > timedelta(hours=24)
    ]
    for session_id in expired_sessions:
        del active_sessions[session_id]

# Generate a random session ID
def generate_session_id():
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


def get_json_body():
    return request.get_json(silent=True) or {}


def get_player_token():
    return request.headers.get('X-Player-Token', '')


def is_host(session):
    supplied_token = request.headers.get('X-Host-Token', '')
    return bool(supplied_token) and secrets.compare_digest(session.host_token, supplied_token)


def valid_name(value):
    return isinstance(value, str) and 1 <= len(value.strip()) <= 30

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
    data = get_json_body()
    creator_name = data.get('creator_name', '')
    max_players = data.get('max_players', 5)

    if not valid_name(creator_name):
        return jsonify({'error': 'Creator name must be between 1 and 30 characters'}), 400
    if isinstance(max_players, bool) or not isinstance(max_players, int) or not 1 <= max_players <= 7:
        return jsonify({'error': 'Max players must be a whole number between 1 and 7'}), 400

    creator_name = creator_name.strip()
    
    session_id = generate_session_id()
    while session_id in active_sessions:
        session_id = generate_session_id()
    
    session = GameSession(session_id, creator_name, max_players)
    creator = session.add_player(creator_name)
    active_sessions[session_id] = session
    
    return jsonify({
        'session_id': session_id,
        'player_token': creator.token,
        'host_token': session.host_token,
        'message': f'Session created with ID: {session_id}'
    }), 201

@app.route('/api/sessions/<session_id>/join', methods=['POST'])
def join_session(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    data = get_json_body()
    player_name = data.get('player_name', '')
    
    if not valid_name(player_name):
        return jsonify({'error': 'Player name must be between 1 and 30 characters'}), 400

    player_name = player_name.strip()
    
    if session.status != 'waiting':
        return jsonify({'error': 'Game has already started'}), 400
    
    player = session.add_player(player_name)
    if not player:
        return jsonify({'error': 'Could not add player (name might be taken or session is full)'}), 400
    
    return jsonify({
        'message': f'Player {player_name} joined session {session_id}',
        'player_token': player.token,
        'session_status': session.status,
        'player_count': len(session.players)
    })

@app.route('/api/sessions/<session_id>/start', methods=['POST'])
def start_session(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    if not is_host(session):
        return jsonify({'error': 'Only the host can start the game'}), 403

    if session.status != 'waiting':
        return jsonify({'error': 'Game has already started or finished'}), 400
    
    if not session.begin_betting():
        return jsonify({'error': 'No funded players are available'}), 400
    
    return jsonify({
        'message': 'Betting is open!',
        'game_state': session.get_game_state()
    })


@app.route('/api/sessions/<session_id>/bet', methods=['POST'])
def place_bet(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404

    session = active_sessions[session_id]
    data = get_json_body()
    amount = data.get('amount')
    player_token = get_player_token()
    player = session.get_player_by_token(player_token)

    if player is None:
        return jsonify({'error': 'Invalid player credentials'}), 403
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        return jsonify({'error': 'Bet must be a positive whole number'}), 400
    if not session.place_bet(player_token, amount):
        return jsonify({'error': 'Bet is invalid, unaffordable, or already placed'}), 400

    return jsonify({
        'message': f'{player.name} bet {amount} chips',
        'game_state': session.get_game_state(),
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
    if session.status != 'in_progress':
        return jsonify({'error': 'The round is not in progress'}), 400

    player = session.get_player_by_token(get_player_token())
    if player is None:
        return jsonify({'error': 'Invalid player credentials'}), 403

    current_player = session.get_current_player()
    if current_player is not player:
        return jsonify({'error': 'Not your turn'}), 400
    
    # Player hits
    current_player.hit(session.deck.pop())
    
    message = f"{player.name} hits and has {current_player.total}"
    
    # Check if player has blackjack or busted
    if current_player.blackjack:
        message = f"{player.name} has Blackjack with {current_player.total}!"
        session.next_turn()
        return jsonify({
            'message': message,
            'game_state': session.get_game_state()
        })
    elif current_player.busted:
        message = f"{player.name} busted with {current_player.total}!"
        session.next_turn()
        return jsonify({
            'message': message,
            'game_state': session.get_game_state()
        })
    elif current_player.total == 21:
        message = f"{player.name} has 21!"
        session.next_turn()
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
    if session.status != 'in_progress':
        return jsonify({'error': 'The round is not in progress'}), 400

    player = session.get_player_by_token(get_player_token())
    if player is None:
        return jsonify({'error': 'Invalid player credentials'}), 403

    current_player = session.get_current_player()
    if current_player is not player:
        return jsonify({'error': 'Not your turn'}), 400
    
    # Move to next player or dealer's turn
    should_continue = session.next_turn()
    
    # Get the updated game state
    game_state = session.get_game_state()
    
    if not should_continue:
        # Game is over, show results
        return jsonify({
            'message': f"{player.name} stands. Dealer's turn.",
            'game_state': game_state
        })
    else:
        # Game continues with next player
        next_player = session.get_current_player()
        return jsonify({
            'message': f"{player.name} stands. {next_player.name}'s turn.",
            'game_state': game_state
        })

@app.route('/api/sessions/<session_id>/reset', methods=['POST'])
def reset_session(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    if not is_host(session):
        return jsonify({'error': 'Only the host can start a new round'}), 403
    if session.status != 'finished':
        return jsonify({'error': 'The current round is not finished'}), 400
    if not session.begin_betting():
        return jsonify({'error': 'No funded players are available'}), 400
    
    return jsonify({
        'message': 'Betting is open for the next round!',
        'game_state': session.get_game_state()
    })

if __name__ == '__main__':
    app.run(debug=True)
