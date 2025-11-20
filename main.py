# 1: run story_review_table.py to generate story_review_table.json
# 2: run audio_table.py to generate audio_table.json

from src.story_review_table import simplify_story_review_table
from src.stage_table import simplify_stage_table
from src.story_meta_table import get_story_meta_table

if __name__ == "__main__":
    simplify_story_review_table()
    simplify_stage_table()
    get_story_meta_table()