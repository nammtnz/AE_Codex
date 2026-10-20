"""Create VD057 portal audio from installed WAV sources; never contacts AE."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RATE = 48000
CHANNELS = 2
TARGET_PEAK = 10.0 ** (-3.0 / 20.0)
DEFAULT_FFMPEG = Path('C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe')
BASE = Path('E:/Audio/SFX/Cartoon')
SOURCES = {
    'swirl': BASE / '1950+ Cinematic Sound Effect/Other whooshes/Swirl Swoosh Fluctuating LookAE.com.wav',
    'wind': BASE / '1950+ Cinematic Sound Effect/General Whooshes/whoosh artificial-wind-low LookAE.com.wav',
    'suck_body': BASE / '8 Epic Garden_SFX/JDwasabi/Suck 1.wav',
    'suck_short': BASE / '8 Epic Garden_SFX/JDwasabi/Suck 1V2.wav',
    'magic_close': BASE / 'whoosh/magical-whoosh-5EGCWBU/Magical Whoosh 2.wav',
}


def db(value):
    return 20.0 * math.log10(max(float(value), 1e-15))


def run_ff(ffmpeg, arguments, data=None):
    return subprocess.run([str(ffmpeg), '-v', 'error'] + arguments,
                          input=data, capture_output=True, check=True).stdout


def decode(ffmpeg, path, start, duration, filters):
    raw = run_ff(ffmpeg, ['-i', str(path), '-ss', str(start), '-t', str(duration),
                         '-vn', '-af', filters, '-ac', str(CHANNELS), '-ar', str(RATE),
                         '-f', 'f32le', 'pipe:1'])
    return np.frombuffer(raw, dtype='<f4').reshape(-1, CHANNELS).copy()


def crossfade_repeat(source, target_frames, overlap_frames):
    """Repeat with equal-power overlap; maintain independent source channels."""
    if len(source) <= overlap_frames:
        raise ValueError('Crossfade must be shorter than source')
    mix = source.copy()
    phase = np.linspace(0, math.pi / 2, overlap_frames, endpoint=True)[:, None]
    fade_out, fade_in = np.cos(phase), np.sin(phase)
    while len(mix) < target_frames:
        blend = mix[-overlap_frames:] * fade_out + source[:overlap_frames] * fade_in
        mix = np.concatenate((mix[:-overlap_frames], blend, source[overlap_frames:]))
    return mix[:target_frames]


def retime_linear(source, target_frames):
    old = np.arange(len(source))
    new = np.linspace(0, len(source) - 1, target_frames)
    return np.column_stack([np.interp(new, old, source[:, c]) for c in range(CHANNELS)])


def edge_fade(audio, frames=240):
    frames = min(frames, len(audio) // 2)
    ramp = np.linspace(0, 1, frames, endpoint=True)[:, None]
    audio[:frames] *= ramp
    audio[-frames:] *= ramp[::-1]
    return audio


def norm(audio, peak=1.0):
    value = float(np.max(np.abs(audio)))
    if value <= 0 or not np.isfinite(audio).all():
        raise ValueError('Empty, silent or invalid signal')
    return audio * (peak / value)


def level_vortex(ffmpeg, audio):
    # The source has very brief high peaks; 1 ms attack controls those peaks
    # while retaining the 0.1-0.3 s rhythmic air movement between them.
    audio = norm(edge_fade(audio.astype(np.float64, copy=True)), TARGET_PEAK)
    filt = ('acompressor=threshold=0.025118864315095794:ratio=4:attack=1:'
            'release=80:knee=6:makeup=1:detection=peak:link=maximum')
    raw = run_ff(ffmpeg, ['-f', 'f32le', '-ar', str(RATE), '-ac', str(CHANNELS),
                          '-i', 'pipe:0', '-af', filt, '-f', 'f32le', 'pipe:1'],
                 audio.astype('<f4').tobytes())
    return np.frombuffer(raw, dtype='<f4').reshape(-1, CHANNELS).copy(), filt


def file_provenance(path):
    return dict(path=path.as_posix(), sizeBytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def save_asset(ffmpeg, path, audio, transforms, source_names):
    audio = edge_fade(audio.astype(np.float64, copy=True))
    before_peak = float(np.max(np.abs(audio)))
    audio = norm(audio, TARGET_PEAK)
    run_ff(ffmpeg, ['-f', 'f32le', '-ar', str(RATE), '-ac', str(CHANNELS),
                    '-i', 'pipe:0', '-c:a', 'pcm_s24le', '-y', str(path)],
           audio.astype('<f4').tobytes())
    decoded = np.frombuffer(run_ff(ffmpeg, ['-i', str(path), '-f', 'f32le', 'pipe:1']),
                            dtype='<f4').reshape(-1, CHANNELS)
    peak = float(np.max(np.abs(decoded)))
    rms = float(np.sqrt(np.mean(decoded.astype(np.float64) ** 2)))
    corr = float(np.corrcoef(decoded[:, 0], decoded[:, 1])[0, 1])
    result = dict(file=path.as_posix(), durationSeconds=len(decoded) / RATE,
                  frames=len(decoded), sampleRate=RATE, channels=CHANNELS, codec='PCM signed 24-bit LE WAV',
                  peakDbfs=db(peak), rmsDbfs=db(rms), normalizationGainDb=db(TARGET_PEAK / before_peak),
                  clippedSamples=int(np.count_nonzero(np.abs(decoded) >= 1)),
                  channelCorrelation=corr, edgeFadeMilliseconds=5,
                  stereo='Preserve original channel differences; no hard panning or mono collapse',
                  transformations=transforms,
                  sources=[file_provenance(SOURCES[name]) for name in source_names],
                  sizeBytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if len(decoded) != len(audio) or result['clippedSamples'] or abs(result['peakDbfs'] + 3) > 0.001:
        raise RuntimeError('Output validation failed: ' + str(path))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ffmpeg', type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument('--only-vortex', action='store_true',
                        help='Update vortex WAV and its manifest entry only; leave all other WAVs byte-identical')
    args = parser.parse_args()
    for path in [args.ffmpeg] + list(SOURCES.values()):
        if not path.is_file():
            raise FileNotFoundError(path)
    destination = ROOT / 'assets/vd057-portal-sfx/ready'
    destination.mkdir(parents=True, exist_ok=True)
    rows = []

    filt = 'highpass=f=120:p=2,lowpass=f=4500:p=2'
    swirl = decode(args.ffmpeg, SOURCES['swirl'], 0.08, 2.506, filt)
    bed = crossfade_repeat(swirl, 11 * RATE, round(0.32 * RATE))
    bed, compressor = level_vortex(args.ffmpeg, bed)
    rows.append(save_asset(args.ffmpeg, destination / 'vortex-bed.wav', bed,
                           dict(sourceRangeSeconds=[0.08, 2.586], filters=filt,
                                repeat='Equal-power crossfade repeats', overlapSeconds=0.32,
                                compressorInputPeakDbfs=-3, compressor=compressor,
                                compressorThresholdDbfs=-32, compressorRatio=4,
                                compressorAttackMilliseconds=1, compressorReleaseMilliseconds=80,
                                compressorKneeLinear=6,
                                compressionNote='Control narrow transient peaks while retaining rhythmic air movement; normalize output peak again to -3 dBFS',
                                outputDurationSeconds=11), ['swirl']))

    if args.only_vortex:
        manifest = ROOT / '.ae-codex/vd057-portal-sfx-assets.json'
        report = json.loads(manifest.read_text(encoding='utf-8'))
        previous = report['assets'][0]
        rows[0]['previousPeakDbfs'] = previous['peakDbfs']
        rows[0]['previousRmsDbfs'] = previous['rmsDbfs']
        rows[0]['previousSha256'] = previous['sha256']
        for other in report['assets'][1:]:
            actual = hashlib.sha256(Path(other['file']).read_bytes()).hexdigest()
            if actual != other['sha256']:
                raise RuntimeError('Unrelated WAV changed unexpectedly: ' + other['file'])
        report['assets'][0] = rows[0]
        report['timestampUtc'] = datetime.now(timezone.utc).isoformat()
        report['latestUpdate'] = dict(assets=['vortex-bed.wav'], otherAssetsByteIdentical=True,
                                     reason='Lower high crest factor for audible ambience at restrained peak level')
        manifest.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(dict(file=rows[0]['file'], peakDbfs=rows[0]['peakDbfs'],
                              rmsDbfs=rows[0]['rmsDbfs'], otherAssetsByteIdentical=True), indent=2))
        return

    filt = 'highpass=f=180:p=2,lowpass=f=3500:p=2'
    wind = decode(args.ffmpeg, SOURCES['wind'], 0.8, 3.9, filt)
    bed = crossfade_repeat(wind, 11 * RATE, round(0.45 * RATE))
    rows.append(save_asset(args.ffmpeg, destination / 'inward-wind-bed.wav', bed,
                           dict(sourceRangeSeconds=[0.8, 4.7], filters=filt,
                                repeat='Equal-power crossfade repeats', overlapSeconds=0.45,
                                outputDurationSeconds=11), ['wind']))

    filt = 'highpass=f=70:p=2,lowpass=f=6500:p=2'
    source_duration = 2.9812708333333333
    body = decode(args.ffmpeg, SOURCES['suck_body'], source_duration - 0.64, 0.64, filt)
    body = retime_linear(body, round(0.64 * RATE))
    short = decode(args.ffmpeg, SOURCES['suck_short'], 0, 0.4407083333333333, filt)
    intake = norm(body) * 0.55
    offset = round(0.18 * RATE)
    short = edge_fade(norm(short)) * 0.85
    end = min(len(intake), offset + len(short))
    intake[offset:end] += short[:end - offset]
    rows.append(save_asset(args.ffmpeg, destination / 'train-suction.wav', intake,
                           dict(bodyRangeSeconds=[source_duration - 0.64, source_duration],
                                bodyDurationSeconds=0.64, bodyWeight=0.55,
                                shortRangeSeconds=[0, 0.4407083333333333], shortStartSeconds=0.18,
                                shortWeight=0.85, componentPeaksNormalizedBeforeBlend=True,
                                filters=filt, outputDurationSeconds=0.64), ['suck_body', 'suck_short']))

    filt = 'highpass=f=500:p=2,lowpass=f=6000:p=2'
    tail = decode(args.ffmpeg, SOURCES['magic_close'], 0.35, 0.8, filt)
    close = retime_linear(tail[::-1], 16000)
    # Quiet rising air followed by a short soft pinch at the portal close.
    envelope = np.linspace(0.38, 1, len(close))[:, None]
    pinch = round(0.055 * RATE)
    envelope[-pinch:] *= np.cos(np.linspace(0, math.pi / 2, pinch))[:, None] ** 1.4
    close *= envelope
    rows.append(save_asset(args.ffmpeg, destination / 'portal-air-close.wav', close,
                           dict(sourceRangeSeconds=[0.35, 1.15], reverse=True,
                                retimeMethod='Linear source resampling; shortened from0.8s to16000samples',
                                filters=filt, riseEnvelope=[0.38, 1], softPinchSeconds=0.055,
                                outputDurationSeconds=16000 / RATE,
                                intent='Short filtered airy reverse rise and soft pinch; low-frequency blast removed'),
                           ['magic_close']))

    report = dict(schema='vd057-portal-sfx-assets/v1', state='prepared-verified',
                  timestampUtc=datetime.now(timezone.utc).isoformat(),
                  script=(ROOT / 'tools/Prepare-Vd057PortalSfx.py').as_posix(),
                  ffmpeg=args.ffmpeg.as_posix(), numpyVersion=np.__version__,
                  perceptualReview=False,
                  reviewNote='Sources decoded and prepared assets technically verified. Audio-input audition is unavailable; no listening claim.',
                  aeMutation=False, assets=rows)
    manifest = ROOT / '.ae-codex/vd057-portal-sfx-assets.json'
    manifest.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(manifest=manifest.as_posix(), assets=[
        {k: row[k] for k in ['file', 'durationSeconds', 'peakDbfs', 'rmsDbfs', 'sizeBytes', 'clippedSamples']}
        for row in rows]), indent=2))


if __name__ == '__main__':
    main()
