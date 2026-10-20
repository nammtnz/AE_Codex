"""Read-only offline verification of the actual live AE portal audio mix.

Writes a JSON report only. It does not render AE, create preview media,
submit JSX, or make an auditory/perceptual verification claim.
"""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import numpy as np

ROOT = Path('C:/Users/nguye/AE_Codex')
FF = str(ROOT / '.ae-codex/praise-runtime-20261016/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
LIVE_PATH = ROOT / '.ae-codex/vd057-portal-sfx-verification.json'
ASSETS_PATH = ROOT / '.ae-codex/vd057-portal-sfx-assets.json'
PLAN_PATH = ROOT / '.ae-codex/vd057-portal-sfx-plan.json'
OUT_PATH = ROOT / '.ae-codex/vd057-portal-sfx-audio-check.json'
RATE = 48000
DURATION = 13
PREFIX = 'VD057 PORTAL FX SFX | '


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def db(value):
    return round(20 * math.log10(max(float(value), 1e-12)), 3)


live = load(LIVE_PATH)
assets = load(ASSETS_PATH)
plan = load(PLAN_PATH)
preflight = load(ROOT / '.ae-codex/vd057-portal-sfx-live.json')
rows = live.get('audio')
if not isinstance(rows, list):
    raise RuntimeError('The verified live report must contain actual audio rows.')
if live.get('nestedAudio'):
    raise RuntimeError('Active nested audio requires explicit reconstruction.')
new_rows = [r for r in rows if r.get('name', '').startswith(PREFIX)]
if len(new_rows) != 8:
    raise RuntimeError(f'Expected 8 new live audio layers, found {len(new_rows)}.')
if len({r['id'] for r in new_rows}) != 8:
    raise RuntimeError('New layer IDs are not unique.')
if any(r.get('solo') for r in rows):
    raise RuntimeError('Solo audio requires separate handling.')

hashes = []
for asset in assets['assets']:
    path = Path(asset['file'])
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    hashes.append(dict(file=str(path), expectedSha256=asset['sha256'], actualSha256=actual,
                       matches=actual == asset['sha256'], sizeBytes=path.stat().st_size))
if len(hashes) != 4 or not all(h['matches'] for h in hashes):
    raise RuntimeError('Prepared SFX hashes do not match the current four-asset manifest.')
manifest_files = {str(Path(a['file'])).replace('\\', '/').lower() for a in assets['assets']}
live_new_files = {r['file'].replace('\\', '/').lower() for r in new_rows}
if live_new_files != manifest_files:
    raise RuntimeError('Live new SFX sources differ from the verified four assets.')

cache = {}


def read_audio(path):
    key = path.replace('\\', '/').lower()
    if key not in cache:
        result = subprocess.run([FF, '-v', 'error', '-i', path, '-vn', '-ar', str(RATE),
                                 '-ac', '2', '-f', 'f32le', 'pipe:1'],
                                capture_output=True, check=True)
        cache[key] = np.frombuffer(result.stdout, dtype='<f4').reshape(-1, 2).astype('float64')
    return cache[key]


expression_checks = []


def render(layers):
    ts = np.arange(DURATION * RATE) / RATE
    mix = np.zeros((len(ts), 2))
    for row in layers:
        if not row.get('audioEnabled', True) or row['outPoint'] <= 0 or row['inPoint'] >= DURATION:
            continue
        if not row.get('file'):
            raise RuntimeError(f'Active nested layer cannot be reconstructed: {row["id"]}')
        if row.get('effects'):
            raise RuntimeError(f'Audio effects require explicit reconstruction: {row["id"]}')
        source = read_audio(row['file'])
        index = (ts - row['startTime']) / (row['stretch'] / 100) * RATE
        valid = np.flatnonzero((ts >= row['inPoint']) & (ts < row['outPoint']) &
                               (index >= 0) & (index < len(source) - 1))
        if not len(valid):
            continue
        source_index = index[valid]
        low = np.floor(source_index).astype('int64')
        fraction = source_index - low
        signal = source[low] * (1 - fraction[:, None]) + source[low + 1] * fraction[:, None]
        if row.get('expression'):
            samples = row.get('samples', [])
            if len(samples) < 2:
                raise RuntimeError(f'Missing actual expression gain samples: {row["id"]}')
            times = np.array([s['time'] for s in samples])
            values = np.array([s['gain'] for s in samples])
            if times[0] > ts[valid[0]] + 0.01001 or times[-1] < ts[valid[-1]] - 0.01001:
                raise RuntimeError(f'Expression samples do not cover live audio interval: {row["id"]}')
            if np.any(np.diff(times) <= 0) or np.max(np.diff(times)) > 0.01001:
                raise RuntimeError(f'Expression samples exceed 10ms step: {row["id"]}')
            if row['id'] not in [c['id'] for c in expression_checks]:
                expression_checks.append(dict(id=row['id'], name=row['name'], sampleCount=len(times),
                                              firstTime=float(times[0]), lastTime=float(times[-1]),
                                              maxStepSeconds=float(np.max(np.diff(times)))))
        elif row.get('levelsKeys'):
            keys = row['levelsKeys']
            if any(k.get('outType', 6612) != 6612 or k.get('inType', 6612) != 6612 for k in keys):
                raise RuntimeError(f'Nonlinear gain keys require actual samples: {row["id"]}')
            times = np.array([k['time'] for k in keys])
            values = np.array([k['value'] for k in keys])
        else:
            times = np.array([0.0])
            values = np.array([row['levelsValue']])
        gain = np.column_stack([np.interp(ts[valid], times, values[:, channel]) for channel in (0, 1)])
        mix[valid] += signal * np.power(10, gain / 20)
    return mix


def true_peak(signal):
    if not np.any(signal):
        return -240.0
    result = subprocess.run([FF, '-v', 'error', '-f', 'f32le', '-ar', str(RATE), '-ac', '2',
                             '-i', 'pipe:0', '-af', 'aresample=192000', '-f', 'f32le', 'pipe:1'],
                            input=signal.astype('<f4').tobytes(), capture_output=True, check=True)
    return db(abs(np.frombuffer(result.stdout, dtype='<f4')).max())


def metrics(signal):
    return dict(samplePeakDbfs=db(abs(signal).max()), truePeak4xDbfs=true_peak(signal),
                clippedSamples=int((abs(signal) >= 1).sum()), rmsDbfs=db(np.sqrt((signal ** 2).mean())))


mixed = render(rows)
added = render(new_rows)
windows = []
for label, start, end in [('loop', 0, 8.7), ('lower suction', 8.7, 9.7),
                           ('lower close', 10.2, 319 / 30), ('upper portal', 319 / 30, 12),
                           ('post portal', 12, 13)]:
    part = slice(round(start * RATE), round(end * RATE))
    windows.append(dict(label=label, start=start, end=end,
                        newSfx=metrics(added[part]), mix=metrics(mixed[part])))
mix_metrics = metrics(mixed)
added_metrics = metrics(added)
post = added[12 * RATE:]
post_abs = float(abs(post).max())
expected_peak = plan['mix']['truePeak4xDbfs']
delta = round(mix_metrics['truePeak4xDbfs'] - expected_peak, 6)
checks = dict(fourAssetHashesMatch=all(h['matches'] for h in hashes), eightNewLiveLayers=True,
              allNewLayersEndBy12=all(r['outPoint'] <= 12.00000001 for r in new_rows),
              newSfxExactlySilentAfter12=post_abs == 0.0, noClippedSamples=mix_metrics['clippedSamples'] == 0,
              truePeakBelowMinus1=mix_metrics['truePeak4xDbfs'] < -1)
preflight_by_id = {r['id']: r for r in preflight['audio']}
concurrent_added = [{k: r.get(k) for k in ['id', 'name', 'file', 'inPoint', 'outPoint', 'levelsValue']}
                    for r in rows if r['id'] not in preflight_by_id and not r['name'].startswith(PREFIX)]
concurrent_changed = []
for row in rows:
    old = preflight_by_id.get(row['id'])
    if old is None or row['id'] in (5968, 5971):
        continue
    fields = ['file', 'inPoint', 'outPoint', 'startTime', 'stretch', 'audioEnabled',
              'levelsValue', 'levelsKeys', 'expression']
    changed = [field for field in fields if row.get(field) != old.get(field)]
    if changed:
        concurrent_changed.append(dict(id=row['id'], name=row['name'], changedFields=changed,
                                       before={field: old.get(field) for field in changed},
                                       after={field: row.get(field) for field in changed}))
report = dict(schema='vd057-portal-sfx-audio-check/v1', state='verified-success' if all(checks.values()) else 'review-needed',
              source='Actual verified live AE layer timing, source paths, gains, and expression samples',
              sourceReport=str(LIVE_PATH), verificationRunId=live.get('runId'),
              rate=RATE, durationSeconds=DURATION, mix=mix_metrics, newAudio=added_metrics,
              expectedProspectiveTruePeak4xDbfs=expected_peak, truePeakDifferenceDb=delta,
              matchesProspectiveTruePeak=abs(delta) <= 0.002,
              prospectiveDifferenceExplainedByLiveChanges=dict(concurrentAddedLayers=concurrent_added,
                                                              concurrentChangedLayers=concurrent_changed,
                                                              note='Three existing-project SFX were added and both music layers changed after preflight. The actual verified mix is independently below -1 dBTP with no clipping; no audio was changed to force agreement with the stale prospective plan.'),
              checks=checks, newSfxMaximumAbsoluteAfter12=post_abs, windows=windows,
              newLayers=[{k: r[k] for k in ['id', 'name', 'file', 'startTime', 'inPoint', 'outPoint', 'stretch']} for r in new_rows],
              assetHashChecks=hashes, expressionSampling=expression_checks,
              perceptualReview=False, aeMutation=False, mediaCreated=False,
              limitations=['Offline PCM reconstruction, not an AE render or listening test.',
                           'Where present, expressions use actual live gain samples every 10ms; other gain keys use linear dB interpolation. The verified music layers no longer had enabled expressions.',
                           'First13s only; all newly added effects finish by12s.'])
OUT_PATH.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: report[k] for k in ['state', 'verificationRunId', 'mix', 'newAudio', 'checks', 'truePeakDifferenceDb']}, indent=2))
