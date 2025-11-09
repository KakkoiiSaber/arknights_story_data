import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo

def story_review_table():
    database = json.load(open("config/database.json", "r", encoding="utf-8"))

    SERVER_LIST = database["serverList"]
    GAME_DATABASE_URL = database["gameDatabaseURL"]
    STORY_REVIEW_TABLE_PATH = database["storyReviewTablePath"]

    ENTRY_TYPE = [
        "MINI_ACTIVITY", 
        "ACTIVITY", 
        "MAINLINE"]
    STORY_KEY = [
        "id", 
        "name", 
        "entryType", 
        "startTime", 
        "storyEntryPicId", 
        "storyPicId", 
        "storyMainColor", 
        "storyCompleteMedalId",
        "infoUnlockDatas"]
    STORY_INFO_KEY = [
        "storyId", 
        "storyCode", 
        "storyName", 
        "storyInfo", 
        "storyTxt", 
        "avgTag"]

    for server in SERVER_LIST:
        url = f"{GAME_DATABASE_URL}/{server}/{STORY_REVIEW_TABLE_PATH}"
        response = requests.get(url)
        table = response.json()
        keys = [
            key
            for key, value in table.items()
            if value["entryType"] in ENTRY_TYPE
        ]
        story_review_table = {}
        '''
        "1stact": {
            "id": "1stact",
            "name": "骑兵与猎人",
            "entryType": "ACTIVITY",
            "startTime": 1559181600,
            "storyEntryPicId": "storyEntryPic_act1d0",
            "storyPicId": null,
            "storyMainColor": null,
            "storyCompleteMedalId": null,
            "infoUnlockDatas": [
                {
                    "storyId": "1stact_level_a001_01_beg",
                    "storyCode": "GT-1",
                    "storyName": "日正当中",
                    "storyInfo": "info/activities/a001/level_a001_01_beg",
                    "storyTxt": "activities/a001/level_a001_01_beg",
                    "avgTag": "行动前"
                },
        '''
        for id in keys:
            entry = table[id]
            story_review_table[id] = {k: entry[k] for k in STORY_KEY}
            info_list = []
            for info in entry["infoUnlockDatas"]:
                # replace storyInfo and storyTxt with full url
                info["storyInfo"] = f"{GAME_DATABASE_URL}/{server}/gamedata/story/[uc]{info['storyInfo']}.txt"
                info["storyTxt"] = f"{GAME_DATABASE_URL}/{server}/gamedata/story/{info['storyTxt']}.txt"
                info_list.append({k: info[k] for k in STORY_INFO_KEY})
            story_review_table[id]["infoUnlockDatas"] = info_list

            # replace starttime from unix to "YYYY-MM"
            ts = entry["startTime"]
            story_review_table[id]["startTime"] = datetime.fromtimestamp(ts, tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m")


        # save story_review_table to /assets/{server}/story_review_table.json
        with open(f"assets/{server}/story_review_table.json", "w", encoding="utf-8") as f:
            json.dump(story_review_table, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    story_review_table()