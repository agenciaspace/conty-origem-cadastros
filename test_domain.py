import unittest
from datetime import timedelta
from core import Store, Problem, instant
from domain import dispatch

class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.store = Store(); self.now = instant('2026-10-09T15:00:00Z')
        self.call('/links', id='a', source='campaign', reference='launch')
        self.call('/links', id='b', source='referral', reference='alice')
    def tearDown(self): self.store.close()
    def call(self, path, **data): return self.store.transact(lambda s: dispatch(s, 'POST', path, data, self.now))
    def opened(self, touch_id='a'): return self.call('/opens', installation_id='i1', touch_id=touch_id)
    def register(self): return self.call('/registrations', id='u1', installation_id='i1')
    def test_two_links_last_touch_wins_and_audit_explains_both(self):
        self.opened(); self.now += timedelta(hours=1); self.opened('b')
        result = self.register()['attribution']
        self.assertEqual(result['source'], 'referral')
        self.assertEqual([r['reason'] for r in result['touches']], ['superseded_by_later_touch', 'winner'])
    def test_equal_time_uses_smallest_id_not_arrival_order(self):
        self.opened('b'); self.opened('a')
        result = self.register()['attribution']
        self.assertEqual(result['winning_touch_id'], 'a')
        self.assertEqual(result['touches'][1]['reason'], 'timestamp_tie_id_tiebreak')
    def test_repeat_open_does_not_refresh_timestamp_or_window(self):
        original = self.opened(); self.now += timedelta(days=2)
        repeated = self.opened()
        self.assertEqual(original, repeated)
        self.assertEqual(len(repeated['touches']), 1)
    def test_window_anchored_to_first_app_open_not_latest_link(self):
        self.opened(None); self.now += timedelta(days=6); self.opened('b')
        self.now += timedelta(days=2)
        result = self.register()['attribution']
        self.assertEqual(result['source'], 'organic')
        self.assertEqual(result['reason'], 'window_expired')
        self.assertEqual(result['touches'][0]['reason'], 'outside_first_open_window')
    def test_exact_window_boundary_valid(self):
        self.opened(); self.now += timedelta(days=7)
        self.assertEqual(self.register()['attribution']['source'], 'campaign')
    def test_missing_origin_is_explicit(self):
        self.opened(None)
        self.assertEqual(self.register()['attribution']['reason'], 'no_eligible_touch')
    def test_late_link_cannot_change_registration_and_is_auditable(self):
        self.opened(); self.register(); self.now += timedelta(seconds=1); self.opened('b')
        result = self.store.transact(lambda s: dispatch(s, 'GET', '/registrations/u1', {}, self.now))
        self.assertEqual(result['attribution']['source'], 'campaign')
        self.assertEqual(result['audit']['touches'][1]['reason'], 'after_registration')
        self.assertEqual(self.register()['attribution']['source'], 'campaign')
    def test_link_after_registration_at_same_clock_instant_is_ignored(self):
        self.opened('b'); self.register(); self.opened('a')
        result = self.store.transact(lambda s: dispatch(s, 'GET', '/registrations/u1', {}, self.now))
        self.assertEqual(result['audit']['winning_touch_id'], 'b')
        self.assertEqual(result['audit']['touches'][0]['reason'], 'after_registration')
    def test_unknown_link_rejected(self):
        with self.assertRaises(Problem): self.opened('unknown')
    def test_same_link_on_two_installations_is_not_globally_deduplicated(self):
        self.opened()
        result = self.call('/opens', installation_id='i2', touch_id='a')
        self.assertEqual(len(result['touches']), 1)

if __name__ == '__main__': unittest.main()
