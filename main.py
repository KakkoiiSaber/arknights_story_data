# 1: run story_review_table.py to generate story_review_table.json
# 2: run audio_table.py to generate audio_table.json

from src.story_review_table import story_review_table
from src.audio_table import audio_table

if __name__ == "__main__":
    story_review_table()
    audio_table()