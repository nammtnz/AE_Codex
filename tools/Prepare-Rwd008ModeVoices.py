from pathlib import Path
import wave, json
import numpy as np

root = Path(__file__).resolve().parents[1]
voices = root / 'assets' / 'rwd008-mode-voices'
records = []
for mode in ['easy', 'normal', 'hard']:
    src = voices / (mode + '-mode.wav')
    dst = voices / (mode + '-mode-ready.wav')
    if dst.exists():
        raise RuntimeError('Already prepared: ' + str(dst))
    with wave.open(str(src), 'rb') as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise RuntimeError('Unexpected speech WAV format')
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float64) / 32768
    active = np.flatnonzero(np.abs(x) > 10 ** (-48 / 20))
    if not len(active):
        raise RuntimeError('Silent voice')
    x = x[max(0, int(active[0]) - int(rate * .012)):min(len(x), int(active[-1]) + int(rate * .08))]
    x *= 10 ** (-4 / 20) / np.max(np.abs(x))
    fade = min(int(rate * .006), len(x) // 2)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    with wave.open(str(dst), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(np.rint(x * 32767).astype('<i2').tobytes())
    records.append(dict(phrase=mode.capitalize() + ' mode!', voice='Microsoft Mark', rate=1,
                        file=str(dst), duration=len(x)/rate, peak_dbfs=20*np.log10(np.max(np.abs(x))),
                        rms_dbfs=20*np.log10(np.sqrt(np.mean(x*x))), clipped_samples=int(np.sum(np.abs(x)>=1))))
out = root / '.ae-codex' / 'rwd008-mode-voice-assets.json'
out.write_text(json.dumps(records, indent=2), encoding='utf-8')
print(out.read_text(encoding='utf-8'))
