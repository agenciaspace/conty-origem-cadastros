"""First-install-open anchored attribution without relying on HTTP referrers."""
from datetime import timedelta
from urllib.parse import urlencode
from core import Problem, require, text, instant, iso

WINDOW = timedelta(days=7)

def audit(installation, registered_at):
    first = instant(installation['first_open_at'])
    expires = first + WINDOW
    eligible, rows = [], []
    for touch in installation['touches'].values():
        opened = instant(touch['opened_at'])
        if touch.get('after_registration') or opened > registered_at:
            reason = 'after_registration'
        elif opened < first or opened > expires or registered_at > expires:
            reason = 'outside_first_open_window'
        else:
            reason = 'eligible'
            eligible.append(touch)
        rows.append({**touch, 'reason': reason})
    # Last touch wins; equal timestamps resolve to the smallest stable link ID.
    eligible.sort(key=lambda t: (-instant(t['opened_at']).timestamp(), t['id']))
    winner = eligible[0] if eligible else None
    for row in rows:
        if row['reason'] == 'eligible':
            row['reason'] = 'winner' if row['id'] == winner['id'] else (
                'timestamp_tie_id_tiebreak' if row['opened_at'] == winner['opened_at'] else 'superseded_by_later_touch')
    return {'source': winner['source'] if winner else 'organic', 'reference': winner['reference'] if winner else None,
            'winning_touch_id': winner['id'] if winner else None,
            'reason': 'last_touch_then_smallest_id' if winner else ('window_expired' if registered_at > expires else 'no_eligible_touch'),
            'first_open_at': iso(first), 'expires_at': iso(expires), 'window_days': 7,
            'touches': sorted(rows, key=lambda r: (r['opened_at'], r['id']))}

def dispatch(state, method, path, data, now):
    links, installs, registrations = (state.setdefault(k, {}) for k in ('links', 'installations', 'registrations'))
    if method == 'POST' and path == '/links':
        ident, source, reference = text(data, 'id'), text(data, 'source'), text(data, 'reference')
        require(source in ('campaign', 'referral', 'community'), 'invalid source')
        link = {'id': ident, 'source': source, 'reference': reference}
        require(ident not in links or links[ident] == link, 'link identity conflict', 409)
        links[ident] = link
        return {**link, 'example_url': 'https://app.example/open?' + urlencode({'touch_id': ident})}
    if method == 'POST' and path == '/opens':
        ident = text(data, 'installation_id')
        link_id = data.get('touch_id')
        require(link_id is None or isinstance(link_id, str) and link_id in links, 'unknown touch_id')
        installation = installs.setdefault(ident, {'id': ident, 'first_open_at': iso(now), 'touches': {}})
        if link_id is not None and link_id not in installation['touches']:
            installation['touches'][link_id] = {**links[link_id], 'opened_at': iso(now),
                'after_registration': any(r['installation_id'] == ident for r in registrations.values())}
        return installation
    if method == 'POST' and path == '/registrations':
        ident, installation_id = text(data, 'id'), text(data, 'installation_id')
        require(installation_id in installs, 'first app open must be recorded', 409)
        if ident in registrations:
            require(registrations[ident]['installation_id'] == installation_id, 'registration identity conflict', 409)
            return registrations[ident]
        require(not any(r['installation_id'] == installation_id for r in registrations.values()), 'installation already registered', 409)
        installation = installs[installation_id]
        require(now >= instant(installation['first_open_at']), 'registration precedes first open')
        result = {'id': ident, 'installation_id': installation_id, 'registered_at': iso(now), 'attribution': audit(installation, now)}
        registrations[ident] = result
        return result
    parts = path.strip('/').split('/')
    if method == 'GET' and len(parts) == 2 and parts[0] == 'registrations':
        result = registrations.get(parts[1])
        require(result is not None, 'registration not found', 404)
        # Frozen attribution plus a live audit that also explains later, ignored opens.
        return {**result, 'audit': audit(installs[result['installation_id']], instant(result['registered_at']))}
    raise Problem('route not found', 404)
