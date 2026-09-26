import io
import json
import os
import unittest
from unittest.mock import patch

import fakeredis

from src.app import app
from src.gameSession import GameSession
from src.session_store import (RedisSessionStore, MemorySessionStore,
                               StoreUnavailable, configured_store, encode, TTL)


class TestSharedSessions(unittest.TestCase):
    def setUp(self):
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        self.original = app.config['SESSION_STORE']
        self.http = patch('src.session_store.urlopen', side_effect=self.transport)
        self.http.start()
        self.addCleanup(self.http.stop)
        self.addCleanup(lambda: app.config.update(SESSION_STORE=self.original))
        self.a = RedisSessionStore('https://redis.example', 'test-token', 'test')
        self.b = RedisSessionStore('https://redis.example', 'test-token', 'test')

    def transport(self, request, timeout):
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-token')
        args = json.loads(request.data)
        return io.BytesIO(json.dumps({'result': self.redis.execute_command(*args)}).encode())

    def request(self, store, path, method='GET', **kwargs):
        # Swap in independent store objects to model unrelated Vercel invocations.
        app.config['SESSION_STORE'] = store
        with app.test_client() as client:
            return client.open(path, method=method, **kwargs)

    def test_separate_instances_share_full_multiplayer_round(self):
        a = self.request(self.a, '/api/sessions', 'POST', json={'creator_name': 'Alice'})
        self.assertEqual(a.status_code, 201)
        owner = a.get_json()
        base = '/api/sessions/' + owner['session_id']
        joined = self.request(self.b, base + '/join', 'POST', json={'player_name': 'Bob'})
        self.assertEqual(joined.status_code, 200)
        bob = joined.get_json()['player_token']
        state = self.request(self.a, base + '/status').get_json()
        self.assertEqual([p['name'] for p in state['players']], ['Alice', 'Bob'])
        self.assertNotIn(owner['player_token'], json.dumps(state))
        host = {'X-Host-Token': owner['host_token']}
        self.assertEqual(self.request(self.b, base + '/start', 'POST', headers=host).status_code, 200)
        self.assertEqual(self.a.list_waiting(), [])
        self.assertEqual(self.request(self.a, base + '/bet', 'POST', json={'amount': 10},
                                     headers={'X-Player-Token': owner['player_token']}).status_code, 200)
        with patch('src.gameSession.random.shuffle', lambda deck: None):
            result = self.request(self.b, base + '/bet', 'POST', json={'amount': 20},
                                  headers={'X-Player-Token': bob})
        self.assertEqual(result.status_code, 200)
        state = result.get_json()['game_state']
        self.assertEqual(state['dealer']['cards'][0], 'XX')
        self.assertIsNone(state['dealer']['total'])
        for token, store in ((owner['player_token'], self.a), (bob, self.b)):
            result = self.request(store, base + '/stand', 'POST', headers={'X-Player-Token': token})
            self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()['game_state']['status'], 'finished')
        reset = self.request(self.a, base + '/reset', 'POST', headers=host)
        self.assertEqual(reset.status_code, 200)
        self.assertEqual(reset.get_json()['game_state']['status'], 'betting')
        self.assertIsNotNone(self.b.load(owner['session_id'])[0].get_player_by_token(bob))

    def test_stale_update_cannot_overwrite_join(self):
        session = GameSession('ABC', 'Alice')
        session.add_player('Alice')
        self.assertTrue(self.a.save(session))
        first, expected1 = self.a.load('ABC')
        second, expected2 = self.b.load('ABC')
        first.add_player('Bob')
        second.add_player('Carol')
        self.assertTrue(self.a.save(first, expected1))
        self.assertFalse(self.b.save(second, expected2))
        self.assertEqual([p.name for p in self.b.load('ABC')[0].players], ['Alice', 'Bob'])

    def test_expiry_and_idle_refresh(self):
        session = GameSession('ABC', 'Alice')
        session.add_player('Alice')
        self.a.save(session)
        self.assertGreater(self.redis.ttl(self.a.key('ABC')), TTL - 5)
        self.redis.expire(self.a.key('ABC'), 60)
        loaded, expected = self.b.load('ABC')
        self.assertLessEqual(self.redis.ttl(self.a.key('ABC')), 60)
        loaded.add_player('Bob')
        self.assertTrue(self.b.save(loaded, expected))
        self.assertGreater(self.redis.ttl(self.a.key('ABC')), TTL - 5)
        stale, expected = self.a.load('ABC')
        self.redis.delete(self.a.key('ABC'))
        self.assertFalse(self.a.save(stale, expected))
        self.assertEqual(self.b.load('ABC'), (None, None))
        self.assertEqual(self.b.list_waiting(), [])

    def test_private_state_round_trips_without_leaking_in_public_state(self):
        session = GameSession('ABC', 'Alice')
        session.add_player('Alice')
        session.begin_betting()
        with patch('src.gameSession.random.shuffle', lambda deck: None):
            session.place_bet(session.players[0].token, 10)
        self.a.save(session)
        restored, _ = self.b.load('ABC')
        self.assertEqual(encode(restored), encode(session))
        public = json.dumps(restored.get_game_state())
        self.assertNotIn(session.host_token, public)
        self.assertNotIn(session.players[0].token, public)
        self.assertNotIn(session.dealer.cards[0], public)

    def test_storage_outage_returns_503_and_preserves_session(self):
        session = GameSession('ABC', 'Alice')
        self.a.save(session)
        with patch('src.session_store.urlopen', side_effect=TimeoutError('secret-token')):
            response = self.request(self.b, '/api/sessions/ABC/status')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret-token', response.get_data(as_text=True))
        self.assertEqual(self.request(self.b, '/api/sessions/ABC/status').status_code, 200)

    def test_route_conflict_returns_409(self):
        session = GameSession('ABC', 'Alice')
        self.a.save(session)
        with patch.object(self.b, 'save', return_value=False):
            result = self.request(self.b, '/api/sessions/ABC/join', 'POST', json={'player_name': 'Bob'})
        self.assertEqual(result.status_code, 409)
        self.assertEqual(self.a.load('ABC')[0].players, [])

    def test_configuration_and_missing_vercel_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(configured_store({}), MemorySessionStore)
        with patch.dict(os.environ, {'VERCEL': '1'}, clear=True):
            with self.assertRaises(StoreUnavailable):
                configured_store({}).load('ABC')
        for url_name in ('KV_REST_API_URL', 'UPSTASH_REDIS_REST_URL'):
            token_name = url_name.replace('_URL', '_TOKEN')
            with patch.dict(os.environ, {url_name: 'https://redis.example', token_name: 'test',
                                       'VERCEL_ENV': 'production'}, clear=True):
                store = configured_store({})
                self.assertIsInstance(store, RedisSessionStore)
                self.assertEqual(store.prefix, 'blackjack:production')
