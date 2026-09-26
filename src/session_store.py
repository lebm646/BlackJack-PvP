"""Shared, JSON-only session storage with atomic compare-and-set updates."""
import json
import os
import threading
import time
from urllib.request import Request, urlopen

from .gameSession import GameSession

TTL = 24 * 60 * 60


class StoreUnavailable(Exception):
    pass


def encode(session):
    data = vars(session).copy()
    data['created_at'] = session.created_at.isoformat()
    data['players'] = [vars(player).copy() for player in session.players]
    data['dealer'] = vars(session.dealer).copy()
    return json.dumps(data, sort_keys=True, separators=(',', ':'))


def decode(raw):
    from datetime import datetime
    from .player import Player

    data = json.loads(raw)
    session = GameSession(data['session_id'], data['creator'], data['max_players'])
    for field in ('deck', 'status', 'host_token', 'current_player_index', 'winner', 'messages'):
        setattr(session, field, data[field])
    session.created_at = datetime.fromisoformat(data['created_at'])
    for saved in data['players']:
        player = Player(saved['name'], saved['chips'], saved['token'])
        for field in ('cards', 'total', 'busted', 'blackjack', 'bet'):
            setattr(player, field, saved[field])
        session.players.append(player)
    for field in ('cards', 'total', 'busted', 'blackjack', 'token', 'bet', 'chips'):
        setattr(session.dealer, field, data['dealer'][field])
    return session


class MemorySessionStore:
    """Local development only; the dictionary also supports existing test fixtures."""
    def __init__(self, sessions=None):
        self.sessions = sessions if sessions is not None else {}
        self.expires = {}
        self.lock = threading.RLock()

    def load(self, session_id):
        with self.lock:
            if self.expires.get(session_id, float('inf')) <= time.time():
                self.sessions.pop(session_id, None)
                self.expires.pop(session_id, None)
            session = self.sessions.get(session_id)
            raw = encode(session) if session else None
            return (decode(raw), raw) if raw else (None, None)

    def save(self, session, expected=None):
        with self.lock:
            _, current = self.load(session.session_id)
            if current != expected:
                return False
            self.sessions[session.session_id] = decode(encode(session))
            self.expires[session.session_id] = time.time() + TTL
            return True

    def list_waiting(self):
        with self.lock:
            sessions = [self.load(sid)[0] for sid in list(self.sessions)]
            return [s for s in sessions if s and s.status == 'waiting'][:100]


class RedisSessionStore:
    # Check and write in one Redis operation. A concurrent request cannot overwrite
    # another player's join/bet/move, or resurrect an expired session.
    SAVE = """
    local current = redis.call('GET', KEYS[1])
    if ARGV[1] == '' then
        if current then return 0 end
    elseif current ~= ARGV[1] then return 0 end
    redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
    if ARGV[4] == 'waiting' then
        local now = redis.call('TIME')
        redis.call('ZADD', KEYS[2], tonumber(now[1]) + tonumber(ARGV[3]), KEYS[1])
    else
        redis.call('ZREM', KEYS[2], KEYS[1])
    end
    return 1
    """
    LIST = """
    local now = redis.call('TIME')
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now[1])
    local keys = redis.call('ZRANGE', KEYS[1], 0, 99)
    local result = {}
    for _, key in ipairs(keys) do
        local value = redis.call('GET', key)
        if value then table.insert(result, value)
        else redis.call('ZREM', KEYS[1], key) end
    end
    return result
    """

    def __init__(self, url, token, namespace='blackjack:production'):
        self.url = url.rstrip('/')
        self.token = token
        self.prefix = namespace
        self.index = namespace + ':waiting'

    def command(self, *args):
        request = Request(self.url, data=json.dumps(args).encode(), headers={
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json',
        }, method='POST')
        try:
            with urlopen(request, timeout=8) as response:
                payload = json.load(response)
            if 'error' in payload or 'result' not in payload:
                raise ValueError('Redis command failed')
            return payload['result']
        except Exception:
            # Never expose URLs, tokens, or the private stored game state in errors.
            raise StoreUnavailable('Shared session storage is unavailable') from None

    def key(self, session_id):
        return self.prefix + ':session:' + session_id

    def load(self, session_id):
        raw = self.command('GET', self.key(session_id))
        try:
            return (decode(raw), raw) if raw else (None, None)
        except (ValueError, KeyError, TypeError):
            raise StoreUnavailable('Stored session could not be read') from None

    def save(self, session, expected=None):
        return self.command('EVAL', self.SAVE, 2, self.key(session.session_id),
                            self.index, expected or '', encode(session), TTL,
                            session.status) == 1

    def list_waiting(self):
        raw_sessions = self.command('EVAL', self.LIST, 1, self.index)
        try:
            return [decode(raw) for raw in raw_sessions]
        except (ValueError, KeyError, TypeError):
            raise StoreUnavailable('Stored sessions could not be read') from None


class UnavailableSessionStore:
    def __getattr__(self, name):
        raise StoreUnavailable('Shared session storage is not configured')


def configured_store(local_sessions):
    for url_name, token_name in (
        ('UPSTASH_REDIS_REST_URL', 'UPSTASH_REDIS_REST_TOKEN'),
        ('KV_REST_API_URL', 'KV_REST_API_TOKEN'),
    ):
        url, token = os.getenv(url_name), os.getenv(token_name)
        if url and token and url.startswith('https://'):
            namespace = os.getenv('BLACKJACK_REDIS_PREFIX') or (
                'blackjack:' + os.getenv('VERCEL_ENV', 'development'))
            return RedisSessionStore(url, token, namespace)
    if os.getenv('VERCEL') or any(os.getenv(name) for name in (
        'UPSTASH_REDIS_REST_URL', 'UPSTASH_REDIS_REST_TOKEN',
        'KV_REST_API_URL', 'KV_REST_API_TOKEN',
    )):
        return UnavailableSessionStore()
    return MemorySessionStore(local_sessions)
