# get keys from story_review_table.json
import json
import requests

def audio_table():
    database = json.load(open("config/database.json", "r", encoding="utf-8"))

    SERVER_LIST = database["serverList"]
    GAME_DATABASE_URL = database["gameDatabaseURL"]
    GAME_ASSETS_BASE_URL = database["gameAssetsBaseURL"]
    STORY_REVIEW_TABLE_PATH = database["storyReviewTablePath"]
    AUDIO_DATA_PATH = database["audioDataPath"]
    AUDIO_ASSETS_PATH = database["audioAssetsPath"]
    MUSIC_KEY = ["name", "intro", "loop", "crossfade"]
    '''
    {
        "intro": "Audio/Sound_Beta_2/Music/beta1_180603/m_sys_void_intro",
        "loop": "Audio/Sound_Beta_2/Music/beta1_180603/m_sys_void_loop",
        "volume": 1.0,
        "crossfade": 0.5,
        "delay": 0.0,
        "fadeStyleId": null,
        "name": "sys.ON_SCENE_LOADED.home"
    },
    '''

    for server in SERVER_LIST:
        url = f"{GAME_DATABASE_URL}/{server}/{AUDIO_DATA_PATH}"
        response = requests.get(url)
        original_audio_table = response.json()

        story_review_table = json.load(open(f"assets/{server}/story_review_table.json", "r", encoding="utf-8"))
        processed_audio_table = {}
        keys = story_review_table.keys()
        for key in keys:
            # for all element in original_audio_table["bgmBanks"], find element["name"] == "sys.ON_ACTIVITY_LOADED." + key
            target_name = "sys.ON_ACTIVITY_LOADED." + key
            target_entry = next((entry for entry in original_audio_table["bgmBanks"] if entry["name"] == target_name), None)
            if target_entry:
                processed_audio_table[key] = {k: target_entry[k] for k in MUSIC_KEY}
                introPath = processed_audio_table[key]["intro"]
                loopPath = processed_audio_table[key]["loop"]
                if introPath:
                    processed_audio_table[key]["intro"] = f"{GAME_ASSETS_BASE_URL}/{AUDIO_ASSETS_PATH}/{introPath.lower()}.mp3"
                if loopPath:
                    processed_audio_table[key]["loop"] = f"{GAME_ASSETS_BASE_URL}/{AUDIO_ASSETS_PATH}/{loopPath.lower()}.mp3"
            else:
                processed_audio_table[key] = None
        with open(f"assets/{server}/audio_table.json", "w", encoding="utf-8") as f:
            json.dump(processed_audio_table, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    audio_table()