"""Kokoro mono 24 kHz para PCM estéreo 48 kHz exigido pelo Discord."""
def converter(audio):
    import numpy as np
    from scipy.signal import resample_poly
    mono = np.asarray(audio, dtype=np.float32).reshape(-1)
    if not mono.size:
        raise ValueError('Áudio vazio.')
    mono = resample_poly(np.nan_to_num(mono), 2, 1)
    pcm = (np.clip(mono, -1, 1) * 32767).astype('<i2')
    return np.repeat(pcm[:, None], 2, axis=1).tobytes()
