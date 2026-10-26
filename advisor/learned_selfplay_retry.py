"""Coordinator-only request-refresh evidence; never repairs or selects actions."""
from copy import deepcopy

from advisor.learned_execution_alignment import content_hash

VERSION = 'public-request-refresh-resolution-v1'


def compact(event):
    from scripts.run_foundation_difficulty_calibration import compact_view
    row = deepcopy(event)
    for stage in ('before', 'after'):
        row[stage] = {s: compact_view(v) if 'state' in v else v for s, v in row[stage].items()}
    return row


def classify_refresh(rejected, accepted, previous_decisions):
    """Require a nonexecuting rejection, unchanged public state and actual commit.

    A changed request alone is insufficient. Missing proof remains unresolved.
    No native error cause is inferred from disabled/trapped confirmation.
    """
    q, n = rejected, accepted
    try:
        r, z = q['result'], n['result']
        assert r['action_rejected'] is True and z['action_rejected'] is False
        assert not r['terminated'] and not r['truncated'] and r['winner'] is None
        assert r['rewards'] == {'self': 0, 'opponent': 0}
        assert type(previous_decisions) is int and r['decisions'] == previous_decisions
        assert z['decisions'] == r['decisions'] + 1
        assert n['ordinal'] == q['ordinal'] + 1
        assert set(q['before']) == set(q['after']) == set(n['before']) == set(n['after'])
        confirmed = []
        for side in q['before']:
            b, a, v, end = q['before'][side], q['after'][side], n['before'][side], n['after'][side]
            assert b['side'] == a['side'] == v['side'] == end['side'] == side
            assert b['episode_id'] == a['episode_id'] == v['episode_id'] == end['episode_id']
            assert b['turn'] == a['turn'] == v['turn']
            assert a['revision'] == b['revision'] + 1 == r['revision']
            assert end['revision'] == a['revision'] + 1 == z['revision']
            assert a == v  # Includes exact refreshed owner request, mask and choices.
            for key in ('state_sha256', 'public_history_sha256'):
                assert b[key] and b[key] == a[key]
            assert b['own_request']['side'] == a['own_request']['side']
            owner = b['own_request']['side']['id']
            assert owner in ('p1', 'p2') and owner == a['own_request']['side']['id']
            action, next_action = q['actions'][side], n['actions'][side]
            assert b['action_mask'][action] and v['action_mask'][next_action]
            if a['action_mask'][action]:
                continue
            assert a['own_request'].get('update') is True
            old, new = b['own_request']['active'][0], a['own_request']['active'][0]
            choice = b['choices'][action].split()
            if choice[0] == 'move':
                slot = int(choice[1]) - 1
                om, nm = old['moves'][slot], new['moves'][slot]
                assert old.get('maybeDisabled') is True
                assert om.get('disabled') is False and nm.get('disabled') is True
                assert {k: x for k, x in om.items() if k not in ('disabled', 'disabledSource')} == {
                    k: x for k, x in nm.items() if k not in ('disabled', 'disabledSource')}
                confirmed.append({'side': side, 'owner': owner, 'kind': 'maybeDisabled_to_disabled',
                                  'move': om['id'], 'action': action})
            elif choice[0] == 'switch':
                assert old.get('maybeTrapped') is True and not old.get('trapped')
                assert new.get('trapped') is True and old['moves'] == new['moves']
                confirmed.append({'side': side, 'owner': owner, 'kind': 'maybeTrapped_to_trapped',
                                  'action': action})
            else:
                raise AssertionError('unsupported_refresh')
        assert confirmed
        return {'classification': 'RESOLVED_REQUEST_REFRESH', 'version': VERSION,
                'confirmed': confirmed, 'rejected_decision': q.get('decision_id'),
                'accepted_decision': n.get('decision_id'), 'native_decisions_before': r['decisions'],
                'native_decisions_after': z['decisions'], 'rejected_row_SHA256': content_hash(q),
                'accepted_row_SHA256': content_hash(n), 'native_error_cause': 'not_established'}
    except (AssertionError, KeyError, TypeError, IndexError, ValueError, AttributeError):
        return {'classification': 'UNRESOLVED', 'version': VERSION}


class ResolvedRequestRateGuard:
    """Keep raw counts; only proved next-commit refreshes leave unresolved counts.

    Pending rejects count immediately. No boundary deferral; six unresolved in
    any 512-attempt window still stop. The separate eight-retry guard runs first.
    """
    def __init__(self):
        self.attempts = self.rejections = self.resolved = 0
        self.windows = {}
        self.pending = self.last_episode = self.last_decisions = None
        self.last_revision = self.last_ordinal = None
        self.proofs = []

    def observe(self, event):
        row = compact(event)
        view = next(iter(row['before'].values()))
        episode, revision = view['episode_id'], view['revision']
        same = episode == self.last_episode
        if same and revision != self.last_revision + 1:
            raise ValueError('refresh_audit_missing_or_duplicate_native_revision')
        row.setdefault('ordinal', self.last_ordinal + 1 if same else 0)
        row.setdefault('decision_id', f'{episode}:{revision}:joint')
        if same and row['ordinal'] != self.last_ordinal + 1:
            raise ValueError('refresh_audit_missing_or_duplicate_native_ordinal')
        if self.pending is not None:
            q, previous, window = self.pending
            proof = classify_refresh(q, row, previous)
            if proof['classification'] == 'RESOLVED_REQUEST_REFRESH':
                self.windows[window]['unresolved'] -= 1
                self.windows[window]['resolved'] += 1
                self.resolved += 1
                self.proofs.append(proof)
        self.pending = None
        window = self.attempts // 512
        counts = self.windows.setdefault(window, {'attempts': 0, 'raw': 0, 'resolved': 0, 'unresolved': 0})
        counts['attempts'] += 1
        self.attempts += 1
        rejected = row['result']['action_rejected']
        if rejected:
            self.rejections += 1
            counts['raw'] += 1
            counts['unresolved'] += 1
            self.pending = (row, self.last_decisions if same else None, window)
        self.last_episode, self.last_revision, self.last_ordinal = episode, revision, row['ordinal']
        self.last_decisions = row['result']['decisions']
        if counts['attempts'] == 512 and counts['unresolved'] > .01 * 512:
            raise ValueError('unresolved_interval_retry_rate_above_one_percent')

    def statistics(self):
        return {'version': VERSION, 'raw_attempts': self.attempts, 'raw_rejections': self.rejections,
                'resolved_request_refreshes': self.resolved, 'unresolved_rejections': self.rejections - self.resolved,
                'windows': self.windows, 'proofs': self.proofs,
                'pending_is_unresolved': self.pending is not None}
