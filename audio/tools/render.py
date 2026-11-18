"""Create and restore a mono speech mixture, then plot the actual PCM files."""

import argparse
import json
import os
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def read_wave(path):
    with wave.open(str(path), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("Expected mono 16-bit PCM speech.")
        raw = audio.readframes(audio.getnframes())
        return audio.getframerate(), np.frombuffer(raw, dtype="<i2") / 32768.0


def write_wave(path, rate, samples):
    pcm = np.rint(samples * 32768).clip(-32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes(pcm.tobytes())


def rms(samples):
    return np.sqrt(np.mean(samples**2))


def active_rms(samples, rate):
    count = round(rate * 0.03)
    frames = samples[: len(samples) // count * count].reshape(-1, count)
    levels = np.sqrt(np.mean(frames**2, axis=1))
    return rms(frames[levels > np.max(levels) * 0.12])


def make_mixture(speech, rate):
    gain = min(10 ** (-20 / 20) / active_rms(speech, rate), 0.78 / np.max(np.abs(speech)))
    # Keep the whole take, including breaths and its natural ending.
    voice = np.pad(speech * gain, (round(0.70 * rate), 0))
    t = np.arange(voice.size) / rate
    hum = (0.024 * np.sin(2 * np.pi * 50 * t)
           + 0.009 * np.sin(2 * np.pi * 100 * t + 0.2)
           + 0.0035 * np.sin(2 * np.pi * 150 * t + 0.5))
    noise = np.random.default_rng(713).standard_normal(voice.size)
    # A little short-range correlation softens the noise at high frequencies.
    noise = np.convolve(noise, [0.57, 0.25, 0.12, 0.06], mode="same")
    return voice + hum + 0.009 * noise / rms(noise)


def restore(mixture, rate):
    # Measure harmonic amplitude and phase from the lead-in of the noisy WAV.
    t = np.arange(mixture.size) / rate
    harmonics = np.column_stack([
        fn(2 * np.pi * hz * t) for hz in (50, 100, 150) for fn in (np.cos, np.sin)
    ])
    lead = slice(round(0.06 * rate), round(0.64 * rate))
    amplitudes = np.linalg.lstsq(harmonics[lead], mixture[lead], rcond=None)[0]
    dehummed = mixture - harmonics @ amplitudes
    # Approximately 40 ms frequency analysis with 75% Hann-window overlap.
    nfft = 2 ** round(np.log2(0.040 * rate))
    hop = nfft // 4
    win = np.hanning(nfft)
    padded = np.pad(dehummed, (nfft, nfft + hop))
    starts = np.arange(0, len(padded) - nfft + 1, hop)
    frame_index = starts[:, None] + np.arange(nfft)
    freq = np.fft.rfftfreq(nfft, 1 / rate)
    spectra = np.fft.rfft(padded[frame_index] * win, axis=1)
    power = np.abs(spectra) ** 2
    noise_frames = (starts >= nfft) & (starts < nfft + 0.70 * rate - nfft)
    noise = np.mean(power[noise_frames], axis=0)
    # A small neighbourhood stabilises the estimate between frames and bins.
    kernel = [0.12, 0.23, 0.30, 0.23, 0.12]
    padded_power = np.pad(power, ((2, 2), (0, 0)), mode="edge")
    local_power = sum(k * padded_power[i : i + len(power)] for i, k in enumerate(kernel))
    gain = np.maximum(0.16, 1 - 1.8 * noise / (local_power + 1e-12))
    gain = np.pad(gain, ((0, 0), (1, 1)), mode="edge")
    gain = 0.15 * gain[:, :-2] + 0.70 * gain[:, 1:-1] + 0.15 * gain[:, 2:]
    highpass = 1 / np.sqrt(1 + (55 / np.maximum(freq, 0.001)) ** 8)
    filtered = np.fft.irfft(spectra * gain * highpass, n=nfft, axis=1) * win
    recovered = np.zeros_like(padded)
    weights = np.zeros_like(padded)
    for start, frame in zip(starts, filtered):
        recovered[start : start + nfft] += frame
        weights[start : start + nfft] += win**2
    recovered = (recovered / np.maximum(weights, 1e-9))[nfft : nfft + len(mixture)]
    return recovered


def db(level):
    return float(20 * np.log10(max(level, 1e-12)))


def measurements(samples, rate):
    return {
        "pause_rms_dbfs": round(db(rms(samples[round(0.15 * rate) : round(0.65 * rate)])), 2),
        "active_rms_dbfs": round(db(active_rms(samples, rate)), 2),
        "sample_peak_dbfs": round(db(np.max(np.abs(samples))), 2),
    }


W, H = 1200, 1200
BG, PAPER, SOFT = "#171B1C", "#F4EEDF", "#A9AFA8"
RULE, BEFORE, AFTER = "#49504E", "#FF957A", "#B7E5AF"


def artwork(path, before, after, info, stage=None):
    art = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(art)
    font_path = Path(os.environ["WINDIR"]) / "Fonts"
    def font(size, style="regular"):
        name = {"regular": "segoeui.ttf", "bold": "segoeuib.ttf", "mono": "consola.ttf"}[style]
        return ImageFont.truetype(str(font_path / name), size)
    def text(x, y, content, size, color=PAPER, style="regular", anchor="lt"):
        d.text((x, y), content, fill=color, font=font(size, style), anchor=anchor)
    def line(x1, y1, x2, y2, color=RULE, width=1):
        d.line((x1, y1, x2, y2), fill=color, width=width)
    def number_ru(value):
        return f"{abs(value):.1f}".replace(".", ",")
    def waveplot(signal, ymid, height, color):
        x0, x1 = 232, 1128
        for y in (ymid - height // 2, ymid, ymid + height // 2):
            line(x0, y, x1, y, "#363C39")
        for fraction in (0, 0.25, 0.5, 0.75, 1):
            x = x0 + round((x1 - x0) * fraction)
            line(x, ymid-height//2-5, x, ymid+height//2+5, "#3D4440")
        bins = np.linspace(0, len(signal), x1 - x0 + 2, dtype=int)
        m = max(np.max(np.abs(before)), np.max(np.abs(after)))
        scale = (height / 2 - 2) / m
        for i, (left, right) in enumerate(zip(bins[:-1], bins[1:])):
            chunk = signal[left:right]
            top, bottom = ymid - np.max(chunk)*scale, ymid - np.min(chunk)*scale
            line(x0 + i, round(top), x0 + i, round(bottom), color)
    # The waveform contour also serves as a small author mark.
    for i, half in enumerate([5, 11, 18, 10, 6]):
        line(75+i*7, 78-half, 75+i*7, 78+half, BEFORE, 4)
    text(127, 62, "СЕРАФИМ МЕЛЬНИК", 26, PAPER, "mono")
    text(1128, 62, "АУДИО  /  ДЕМО", 26, SOFT, "mono", "rt")
    line(72, 129, 1128, 129, RULE, 2)
    title = "Очистка голоса" if stage is None else ("До обработки" if stage == 0 else "После обработки")
    title_size = 102 if stage is None else 99
    text(67, 192, title, title_size, PAPER, "bold")
    sub = ("Русская речь · гул 50 Гц и фоновый шум" if stage is None else
           ("К записи добавлены гул и фоновый шум" if stage == 0 else "Та же фраза после шумоподавления"))
    text(73, 333, sub, 40, SOFT)
    duration = info["duration_seconds"]
    text(73, 444, "ДВЕ ВЕРСИИ ОДНОЙ ЗАПИСИ", 23, SOFT, "mono")
    text(1128, 444, f"МОНО  /  {duration:.1f} С".replace(".", ","), 23, SOFT, "mono", "rt")
    line(72, 493, 1128, 493, RULE, 2)
    c1, c2 = (BEFORE if stage != 1 else "#636861"), (AFTER if stage != 0 else "#636861")
    text(73, 551, "ДО", 33, c1, "bold")
    text(73, 605, "Вход", 23, SOFT, "mono")
    waveplot(before, 592, 130, c1)
    line(72, 699, 1128, 699, RULE)
    text(73, 754, "ПОСЛЕ", 33, c2, "bold")
    text(73, 808, "Выход", 23, SOFT, "mono")
    waveplot(after, 795, 130, c2)
    line(72, 900, 1128, 900, RULE, 2)
    text(73, 957, "Уровень фона в паузе", 36)
    text(73, 1027, "0,15–0,65 с  /  RMS, dBFS", 24, SOFT, "mono")
    b = "−" + number_ru(info["before"]["pause_rms_dbfs"])
    a = "−" + number_ru(info["after"]["pause_rms_dbfs"])
    text(790, 965, b, 54, BEFORE, "bold", "rt")
    text(865, 981, "→", 37, SOFT, "regular", "mt")
    text(1128, 965, a, 54, AFTER, "bold", "rt")
    line(72, 1109, 1128, 1109, RULE)
    text(73, 1132, "ГОЛОС ДЕНИСА  /  OPEN HOME FOUNDATION  /  CC0", 22, SOFT, "mono")
    text(1128, 1132, "16-БИТ PCM", 22, SOFT, "mono", "rt")
    art.save(path, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("voice", "output", "temp"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rate, speech = read_wave(args.voice)
    write_wave(args.output / "before.wav", rate, make_mixture(speech, rate))
    # The restoration stage only receives samples from the written noisy mix.
    _, before = read_wave(args.output / "before.wav")
    write_wave(args.output / "after.wav", rate, restore(before, rate))
    _, after = read_wave(args.output / "after.wav")
    info = {"sample_rate_hz": rate, "samples": len(before),
            "duration_seconds": round(len(before) / rate, 3),
            "before": measurements(before, rate), "after": measurements(after, rate)}
    artwork(args.output / "cover.png", before, after, info)
    artwork(args.temp / "before.png", before, after, info, 0)
    artwork(args.temp / "after.png", before, after, info, 1)
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
