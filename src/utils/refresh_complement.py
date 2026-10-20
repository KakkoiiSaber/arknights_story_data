"""Refresh only curated theme fields, preserving existing story text/descriptions.

Usage: python src/utils/refresh_complement.py --audio-data path/to/audio_data.json
The input must be the original game audio_data, not this repo's generated table.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review import apply_stage_complement, copy_theme_fields, resolve_stage_audio
from utils.save_json import save_json


def refresh(root, server, original_audio):
    root = Path(root)
    assets = root / "assets"
    complement = json.loads((assets / "stage_table_complement.json").read_text(encoding="utf-8"))
    folder = assets / server
    meta = json.loads((folder / "story_meta_table.json").read_text(encoding="utf-8"))
    audio = json.loads((folder / "audio_data.json").read_text(encoding="utf-8"))
    updated = []
    for story_id, extra in complement.items():
        if story_id not in meta or server not in extra.get("servers", [server]):
            continue
        path = folder / "story_review_info" / f"{story_id}.json"
        review = json.loads(path.read_text(encoding="utf-8"))
        stage = apply_stage_complement(review, extra, server)
        track = resolve_stage_audio(stage, original_audio)
        if track:
            audio[track["name"]] = track
            stage["gameMusicName"] = track["name"]
        copy_theme_fields(meta[story_id], stage)
        copy_theme_fields(review, stage)
        for key in ("backgroundId", "gameMusicId", "gameMusicName"):
            review[key] = stage.get(key)
        save_json(review, path)
        updated.append(story_id)
    save_json(meta, folder / "story_meta_table.json")
    save_json(audio, folder / "audio_data.json")
    return updated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-data", required=True)
    parser.add_argument("--server", default="zh_CN")
    args = parser.parse_args()
    original = json.loads(Path(args.audio_data).read_text(encoding="utf-8"))
    print("Updated:", ", ".join(refresh(Path(__file__).resolve().parents[2], args.server, original)))
