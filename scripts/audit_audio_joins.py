#!/usr/bin/env python3
"""Compare an exported audio join with the same original film sound.

Python standard library + ffmpeg/ffprobe. See references/technical-checks.md.
This diagnoses gain discontinuities, not perceptual quality or speech leakage.
"""
import argparse
from array import array
import json
import math
from pathlib import Path
import subprocess
import sys

SR = 48000


def run(args):
    p = subprocess.run(args, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace")[-2000:])
    return p.stdout


def probe(path):
    return json.loads(run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=index,codec_type,codec_name,width,height,sample_rate,channels,duration,start_time:format=duration,size",
        "-of", "json", str(path),
    ]))


def audio(path, start, duration, audio_stream=0):
    if start < 0:
        raise ValueError("Probe window starts before source/timeline zero")
    if not isinstance(audio_stream, int) or audio_stream < 0:
        raise ValueError("audio_stream must be a nonnegative integer counting audio tracks only")
    data = run([
        "ffmpeg", "-v", "error", "-ss", str(start), "-i", str(path),
        "-t", str(duration), "-map", f"0:a:{audio_stream}", "-vn", "-ar", str(SR), "-ac", "2",
        "-f", "f32le", "-",
    ])
    samples = array("f")
    samples.frombytes(data)
    if sys.byteorder != "little":
        samples.byteswap()
    expected = round(duration * SR) * 2
    if len(samples) < expected - 4:
        raise ValueError("Audio ends before the complete probe window")
    if not all(math.isfinite(x) for x in samples):
        raise ValueError("Non-finite PCM sample")
    return samples


def rms_db(samples):
    if not samples:
        raise ValueError("Empty measurement window")
    return 20 * math.log10(max(1e-12, math.sqrt(sum(x*x for x in samples) / len(samples))))


def levels(path, at, window, gap, audio_stream=0):
    samples = audio(path, at-window, 2*window, audio_stream)
    n = round((window-gap)*SR)*2
    i = round((window+gap)*SR)*2
    before, after = rms_db(samples[:n]), rms_db(samples[i:i+n])
    return {"before_dbfs": before, "after_dbfs": after, "step_db": after-before}


def video_hash(path):
    return run([
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0",
        "-c", "copy", "-f", "hash", "-hash", "sha256", "-",
    ]).decode().strip()


def analyze(config, base, window=.25, gap=.05, threshold=3.0):
    if not 0 <= gap < window:
        raise ValueError("Require 0 <= gap < window")
    if threshold <= 0:
        raise ValueError("Threshold must be positive")

    def resolve(value):
        p = Path(value).expanduser()
        p = p if p.is_absolute() else base / p
        if not p.is_file():
            raise FileNotFoundError(p)
        return p

    exported = resolve(config["export"])
    export_stream = config.get("export_audio_stream", 0)
    result = {"export": str(exported), "export_audio_stream": export_stream, "probe": probe(exported), "joins": [],
              "warnings": [], "limitations": "Gain comparison only; not a listening, stem-purity, or subtitle-timing test."}
    for entry in config.get("joins", []):
        at, source_at = float(entry["at"]), float(entry["source_at"])
        source_stream = entry.get("source_audio_stream", 0)
        row = {"label": entry.get("label", str(at)), "at": at, "source_at": source_at,
               "source_audio_stream": source_stream}
        if entry.get("probe_has_no_added_speech") is not True:
            row.update(status="skipped", reason="Added narration in the probe makes source-relative gain inconclusive")
        else:
            row["source"] = levels(resolve(entry["source"]), source_at, window, gap, source_stream)
            row["export"] = levels(exported, at, window, gap, export_stream)
            delta = row["export"]["step_db"] - row["source"]["step_db"]
            row["source_relative_gain_step_db"] = delta
            if min(row["source"]["before_dbfs"], row["source"]["after_dbfs"]) < -80:
                row.update(status="inconclusive", reason="Source window is too quiet for reliable gain comparison")
            elif abs(delta) > threshold:
                row.update(status="review", reason="Gain changes more than the configured review threshold")
                result["warnings"].append(f"{row['label']}: inspect gain step {delta:.2f} dB")
            else:
                row["status"] = "no_large_gain_step_detected"
        result["joins"].append(row)
    if config.get("picture_reference"):
        reference = resolve(config["picture_reference"])
        ref_hash, new_hash = video_hash(reference), video_hash(exported)
        same = ref_hash == new_hash
        result["picture_comparison"] = {"reference": str(reference), "reference_sha256": ref_hash,
                                        "export_sha256": new_hash, "same_packet_content": same,
                                        "note": "Checks encoded video packet bytes; inspect timestamps separately."}
        if not same:
            result["warnings"].append("Video packet content differs; determine whether this change was intended")
    if config.get("subtitles") or config.get("subtitle_reference"):
        if not (config.get("subtitles") and config.get("subtitle_reference")):
            raise ValueError("Provide both subtitles and subtitle_reference")
        same = resolve(config["subtitles"]).read_bytes() == resolve(config["subtitle_reference"]).read_bytes()
        result["same_subtitle_bytes"] = same
        if not same:
            result["warnings"].append("Subtitle bytes differ; inspect whether edits were intended")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--window", type=float, default=.25)
    p.add_argument("--gap", type=float, default=.05)
    p.add_argument("--threshold", type=float, default=3.0)
    a = p.parse_args()
    try:
        if a.config.resolve() == a.output.resolve():
            raise ValueError("Output must not overwrite input config")
        config = json.loads(a.config.read_text(encoding="utf-8"))
        inputs = [config.get(k) for k in ("export", "picture_reference", "subtitles", "subtitle_reference")]
        inputs += [x.get("source") for x in config.get("joins", [])]
        for value in filter(None, inputs):
            candidate = Path(value).expanduser()
            candidate = candidate if candidate.is_absolute() else a.config.resolve().parent / candidate
            if candidate.resolve() == a.output.resolve():
                raise ValueError("Report output must not overwrite an input media/subtitle file")
        report = analyze(config, a.config.resolve().parent, a.window, a.gap, a.threshold)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"report": str(a.output.resolve()), "joins": len(report["joins"]),
                          "warnings": report["warnings"]}, ensure_ascii=False))
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as e:
        print(f"Audit failed: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
