import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from review import apply_stage_complement, resolve_stage_audio, copy_theme_fields
from utils.refresh_complement import refresh


class ComplementTests(unittest.TestCase):
    def setUp(self):
        self.bank = {"name": "sys.example", "intro": None, "loop": "Audio/Example"}
        self.audio = {"musics": [{"id": "music_example", "bank": 42}],
                      "bankAlias": {"42": "sys.example"}, "bgmBanks": [self.bank]}

    def test_native_id_alias_and_bank_name_resolve_without_mutating_source(self):
        original = copy.deepcopy(self.audio)
        by_id = resolve_stage_audio({"gameMusicId": "music_example"}, self.audio)
        by_bank = resolve_stage_audio({"gameMusicName": "sys.example"}, self.audio)
        self.assertEqual(by_id, by_bank)
        self.assertEqual(by_id["loop"], "audio/example.mp3")
        self.assertEqual(self.audio, original)

    def test_verified_urls_override_bank_paths_without_losing_bank_identity(self):
        track = resolve_stage_audio({"gameMusicId": "music_example", "audio": {
            "intro": None, "loop": "https://example.com/track.wav"}}, self.audio)
        self.assertEqual(track["name"], "sys.example")
        self.assertEqual(track["loop"], "https://example.com/track.wav")

    def test_chinese_complement_does_not_leak_into_other_locales(self):
        stage = {"backgroundId": "original.png"}
        extra = {"servers": ["zh_CN"], "backgroundId": "new.png"}
        self.assertEqual(apply_stage_complement(stage, extra, "en_US"), stage)
        self.assertEqual(apply_stage_complement(stage, extra, "zh_CN")["backgroundId"], "new.png")
        self.assertEqual(stage["backgroundId"], "original.png")

    def test_generated_fields_preserve_composite_background_and_media_urls(self):
        extra = {"backgroundUrls": ["https://example.com/left.png", "https://example.com/right.png"],
                 "backgroundAspectRatio": 1.625, "audio": {"loop": "https://example.com/a.mp3"}}
        self.assertEqual(copy_theme_fields({}, extra), extra)

    def test_unknown_music_is_reported_instead_of_inventing_id(self):
        with self.assertRaisesRegex(ValueError, "Unknown music ID"):
            resolve_stage_audio({"gameMusicId": "missing"}, self.audio)

    def test_explicit_story_fallback_can_be_resolved_again_after_refresh(self):
        stage = {"gameMusicName": "story.path", "audio": {
            "name": "story.path", "intro": None, "loop": "https://example.com/path.mp3"}}
        self.assertEqual(resolve_stage_audio(stage, self.audio), stage["audio"])

    def test_refresh_is_idempotent_and_preserves_existing_chapters(self):
        with tempfile.TemporaryDirectory() as folder:
            assets = Path(folder) / "assets"
            reviews = assets / "zh_CN" / "story_review_info"
            reviews.mkdir(parents=True)
            files = {
                assets / "stage_table_complement.json": {
                    "collab": {"servers": ["zh_CN"], "kvImageId": "https://example.com/card.png",
                               "backgroundId": "new.png", "gameMusicId": "music_example"}},
                assets / "zh_CN" / "story_meta_table.json": {"collab": {"name": "Test"}, "ordinary": {"kvImageId": "old.png"}},
                assets / "zh_CN" / "audio_data.json": {},
                reviews / "collab.json": {"id": "collab", "desc": "Keep this", "infoUnlockDatas": [{"storyTxt": "unchanged.txt"}]},
            }
            for path, data in files.items():
                path.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(refresh(folder, "zh_CN", self.audio), ["collab"])
            once = {path: path.read_bytes() for path in files}
            refresh(folder, "zh_CN", self.audio)
            self.assertEqual(once, {path: path.read_bytes() for path in files})
            result = json.loads((reviews / "collab.json").read_text(encoding="utf-8"))
            self.assertEqual(result["infoUnlockDatas"], files[reviews / "collab.json"]["infoUnlockDatas"])
            self.assertEqual(result["desc"], "Keep this")
            meta = json.loads((assets / "zh_CN" / "story_meta_table.json").read_text())
            self.assertEqual(meta["ordinary"], {"kvImageId": "old.png"})


if __name__ == "__main__":
    unittest.main()
