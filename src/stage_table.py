import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo
'''
"setId_mainline_0_1": {
            "storySetId": "setId_mainline_0_1",
            "storySetType": "MAINLINE",
            "sortByYear": 1,
            "sortWithinYear": 1,
            "kvImageId": "kv_evil_time_part1",
            "titleImageId": "title_evil_time_part1",
            "haveVideoToPlay": true,
            "backgroundId": "bg_mainLine_0",
            "gameMusicId": null,
            "coreRewardType": "NONE",
            "coreRewardId": null,
            "relevantActivityId": null,
            "mainlineData": {
                "zoneId": "main_0",
                "retroId": null,
                "decoImageId": "deco_evil_time_part1"
            },
            "ssData": null,
            "collectData": null
        },
        "setId_ssLine_act8mini": {
            "storySetId": "setId_ssLine_act8mini",
            "storySetType": "COLLECT",
            "sortByYear": 3,
            "sortWithinYear": 2,
            "kvImageId": "kv_vigilo",
            "titleImageId": "title_vigilo",
            "haveVideoToPlay": false,
            "backgroundId": null,
            "gameMusicId": "music_3in1bg_act8mini",
            "coreRewardType": "CHAR_SKIN",
            "coreRewardId": "char_145_prove@wild#5",
            "relevantActivityId": "act8mini",
            "mainlineData": null,
            "ssData": null,
            "collectData": {
                "name": "如我所见",
                "desc": "来自过去的人，\n行驶于当下的航船，\n自未来中升起的目光。",
                "backgroundId": "storybg_vigilo"
            }
        },
        "setId_ssLine_act33side": {
            "storySetId": "setId_ssLine_act33side",
            "storySetType": "SS",
            "sortByYear": 5,
            "sortWithinYear": 10,
            "kvImageId": "kv_babel",
            "titleImageId": "title_babel",
            "haveVideoToPlay": false,
            "backgroundId": null,
            "gameMusicId": "music_3in1bg_act33side",
            "coreRewardType": "CHAR",
            "coreRewardId": "char_4131_odda",
            "relevantActivityId": "act33side",
            "mainlineData": null,
            "ssData": {
                "name": "巴别塔",
                "desc": "巴别塔，自过去呼唤未来的理想之地。\n弥合隔阂的高塔指向真理。\n魔王盗取希望之火。火星散落，战火重起。\n同胞刀戈相向，英雄从废墟中站起。\n分歧止于一场刺杀，命运却早已与真相绑在一起。\n远见者用呐喊书写理想家的墓志铭。\n魔王虽逝，理想犹存。",
                "backgroundId": "storybg_babel",
                "tags": [
                    "tag_11",
                    "tag_13",
                    "tag_16"
                ],
                "reopenActivityId": "act33sre",
                "retroActivityId": "permanent_sub_6_Babel",
                "isRecommended": false,
                "recommendHideStageId": null,
                "overrideStageList": null
            },
            "collectData": null
        },
'''

def simplify_stage_table():
    print("Simplifying stage_table...")
    database = json.load(open("config/database.json", "r", encoding="utf-8"))

    SERVER_LIST = database["serverList"]
    GAME_DATABASE_URL = database["gameDatabaseURL"]
    STAGE_TABLE_PATH = database["stageTablePath"]
    

    for server in SERVER_LIST:
        print(f"Processing server: {server}...")
        stage_table = {}
       
        # get stage_table
        stage_table_url = f"{GAME_DATABASE_URL}/{server}/{STAGE_TABLE_PATH}"
        response = requests.get(stage_table_url)
        stage_table_origin = response.json()
        storylineStorySets = stage_table_origin["storylineStorySets"]
        # get id
        for key, value in list(storylineStorySets.items()):
            if value["storySetType"] == "MAINLINE":
                id = value["mainlineData"]["zoneId"]
                backgroundId = None
                if id == None: #main story from main_14 as activity
                    # for ep 15, relavant id is act2mainss => 15 = 13+ 2, split act and mainss
                    relavantId = value["relevantActivityId"]
                    id = "main_" + str(13 + int(relavantId.split("act")[-1].split("mainss")[0]))
            elif value["storySetType"] == "SS":
                id = value["relevantActivityId"]
                backgroundId = f"{value['ssData']['backgroundId']}.png" if value['ssData']['backgroundId'] else None
            elif value["storySetType"] == "COLLECT":
                id = value["relevantActivityId"]
                backgroundId = f"{value['collectData']['backgroundId']}.png" if value['collectData']['backgroundId'] else None
            else:
                print(f"Unknown storySetType: {value['storySetType']} from {key}")
                continue
            print(f"Processing stage info for id: {id}...")
            # get kvImageId, titleImageId, gameMusicId
            stage_table[id] = {
                # "kvImageId": f"assets/torappu/dynamicassets/arts/ui/mixstory/kvs/{value['kvImageId']}",
                # "titleImageId": f"assets/torappu/dynamicassets/arts/ui/mixstory/retrobkgs/{value['titleImageId']}",
                # "gameMusicId": f"assets/torappu/dynamicassets/arts/ui/mixstory/titles/{value['gameMusicId']}",
                "kvImageId": f"{value['kvImageId']}.png" if value['kvImageId'] else None,
                "titleImageId": f"{value['titleImageId']}.png" if value['titleImageId'] else None,
                "gameMusicId": value['gameMusicId'],
                "backgroundId": backgroundId
            }

        # save story_review_table to /assets/{server}/story_review_table.json
        with open(f"assets/{server}/stage_table.json", "w", encoding="utf-8") as f:
            json.dump(stage_table, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    simplify_stage_table()