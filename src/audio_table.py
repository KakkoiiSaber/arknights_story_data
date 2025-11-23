# get keys from story_review_table.json
import json
import requests

def audio_table():
    print("Generating audio_table...")
    database = json.load(open("config/database.json", "r", encoding="utf-8"))

    SERVER_LIST = database["serverList"]
    GAME_DATABASE_URL = database["gameDatabaseURL"]
    AUDIO_DATA_PATH = database["audioDataPath"]
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
        print(f"Processing server: {server}...")
        url = f"{GAME_DATABASE_URL}/{server}/{AUDIO_DATA_PATH}"
        response = requests.get(url)
        original_audio_table = response.json()

        musics = original_audio_table["musics"]
        bankAlias = original_audio_table["bankAlias"]
        bgmBanks = original_audio_table["bgmBanks"]

        audio_table = {}

        story_meta_table = json.load(open(f"assets/{server}/story_meta_table.json", "r", encoding="utf-8"))
        processed_audio_table = {}
        for key, value in story_meta_table.items():
            print(f"Processing story meta: {key}...")
            if value["gameMusicId"] is None:
                story_meta_table[key]["gameMusicName"] = None
                continue
            else:
                gameMusicId = value["gameMusicId"]
                # find value in musics with id == gameMusicId
                music_value = next((item for item in musics if item["id"] == gameMusicId), None)

                bankId = music_value["bank"]
                bankName = bankAlias.get(str(bankId), bankId)
                story_meta_table[key]["gameMusicName"] = bankName
                bank_info = next((item for item in bgmBanks if item["name"] == bankName), None)
                if bank_info["intro"] is not None:
                    bank_info["intro"] = bank_info["intro"].lower() + ".mp3"
                if bank_info["loop"] is not None:
                    bank_info["loop"] = bank_info["loop"].lower() + ".mp3"
                processed_audio_table[bankName] = bank_info

        # sort infoUnlockDatas to be the last
        for key, value in story_meta_table.items():
            infoUnlockDatas = story_meta_table[key].pop("infoUnlockDatas")
            story_meta_table[key]["infoUnlockDatas"] = infoUnlockDatas

        with open(f"assets/{server}/audio_table.json", "w", encoding="utf-8") as f:
            json.dump(processed_audio_table, f, ensure_ascii=False, indent=4)
        with open(f"assets/{server}/story_meta_table.json", "w", encoding="utf-8") as f:
            json.dump(story_meta_table, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    audio_table()