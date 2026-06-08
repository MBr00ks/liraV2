import numpy as np


TARGET_SR = 48000


def to_mono(data: np.ndarray) -> np.ndarray:
    if data.ndim == 1:
        return data
    if data.dtype == np.int16:
        return np.mean(data.astype(np.float32), axis=1).astype(np.int16)
    return np.mean(data, axis=1)


def resample_to_target(data: np.ndarray, orig_sr: int, target_sr: int = TARGET_SR) -> np.ndarray:
    data = to_mono(data)
    if orig_sr == target_sr:
        return data
    n = int(len(data) * target_sr / orig_sr)
    x_old = np.linspace(0, 1, len(data))
    x_new = np.linspace(0, 1, n)
    return np.interp(x_new, x_old, data).astype(data.dtype)


def normalize_rms(data: np.ndarray, target_rms: float = 2200) -> np.ndarray:
    if data.dtype != np.int16:
        return data
    current = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
    if current < 1:
        return data
    gain = target_rms / current
    result = data.astype(np.float32) * gain
    return np.clip(result, -32768, 32767).astype(np.int16)


def apply_fades(data: np.ndarray, sr: int = TARGET_SR, fade_in_ms: float = 15, fade_out_ms: float = 30) -> np.ndarray:
    if data.dtype != np.int16:
        return data
    result = data.astype(np.float32)
    n = len(result)

    fi = min(int(sr * fade_in_ms / 1000), n // 2)
    if fi > 0:
        result[:fi] *= np.linspace(0, 1, fi)

    fo = min(int(sr * fade_out_ms / 1000), n // 2)
    if fo > 0:
        result[-fo:] *= np.linspace(1, 0, fo)

    return result.astype(np.int16)


def gentle_lowpass(data: np.ndarray, strength: float = 0.3) -> np.ndarray:
    if data.dtype != np.int16:
        return data
    result = data.astype(np.float32)
    width = max(3, int(5 * strength))
    kernel = np.hanning(width)
    kernel /= kernel.sum()
    smoothed = np.convolve(result, kernel, mode="same")
    result = result * (1 - strength) + smoothed * strength
    return np.clip(result, -32768, 32767).astype(np.int16)


def pitch_shift(data: np.ndarray, semitones: float) -> np.ndarray:
    if data.dtype != np.int16 or abs(semitones) < 0.01:
        return data
    factor = 2 ** (-semitones / 12)
    n = len(data)
    temp_n = int(n / factor)
    x_old = np.linspace(0, 1, n)
    x_temp = np.linspace(0, 1, temp_n)
    stretched = np.interp(x_temp, x_old, data.astype(np.float32))
    x_new = np.linspace(0, 1, n)
    result = np.interp(x_new, x_temp, stretched)
    return np.clip(result, -32768, 32767).astype(np.int16)


def extract_best_segment(data: np.ndarray, sr: int = TARGET_SR, max_seconds: float = 2.5, fade_ms: float = 30, mode: str = "max") -> np.ndarray:
    if data.dtype != np.int16:
        return data
    n = int(sr * max_seconds)
    if len(data) <= n:
        return data
    result = data.astype(np.float32)
    window = int(sr * 0.05)
    energy = np.array([
        float(np.sqrt(np.mean(result[i:i+window].astype(np.float32)**2)))
        for i in range(0, len(result) - window + 1, window)
    ])
    kernel = np.ones(int(n / window)) / (n / window)
    smoothed = np.convolve(energy, kernel, mode="valid")
    start = (np.argmin if mode == "min" else np.argmax)(smoothed) * window
    seg = result[start:start + n]

    fo = min(int(sr * fade_ms / 1000), n // 2)
    if fo > 0:
        seg[:fo] *= np.linspace(0, 1, fo)
        seg[-fo:] *= np.linspace(1, 0, fo)
    return seg.astype(np.int16)
