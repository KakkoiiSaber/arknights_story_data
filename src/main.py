import requests
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from typing import Optional
import copy
from pathlib import Path



logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
fmt = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
ch.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(ch)

def simplify_story_review_table(table: json) -> json:
    '''
    "act45side": {
        "id": "act45side",
        "name": "无忧梦呓",
        "entryType": "ACTIVITY",
        "actType": "ACTIVITY_STORY",
        "startTime": 1756958400,
        "endTime": -1,
        "startShowTime": 1758744000,
        "endShowTime": -1,
        "remakeStartTime": -1,
        "remakeEndTime": -1,
        "storyEntryPicId": "storyEntryPic_act45side",
        "storyPicId": null,
        "storyMainColor": null,
        "customType": 0,
        "storyCompleteMedalId": null,
        "rewards": {},
        "infoUnlockDatas": []
    '''
    # filter required keys and values
    simplified_table = {
        "id": table["id"],
        "name": table["name"],
        "type": table["actType"],
        "startTime": datetime.fromtimestamp(table["startTime"], tz=ZoneInfo("Asia/Shanghai")).strftime("%Y-%m"),
        "infoUnlockDatas": table["infoUnlockDatas"]
    }
    return simplified_table

def simplify_stage_table(table: json) -> json:
    '''
    "setId_ssLine_act9d0": {
                "storySetId": "setId_ssLine_act9d0",
                "storySetType": "SS",
                "sortByYear": 1,
                "sortWithinYear": 14,
                "kvImageId": "kv_darknights_memoir",
                "titleImageId": "title_darknights_memoir",
                "haveVideoToPlay": false,
                "backgroundId": null,
                "gameMusicId": "music_3in1bg_act9d0",
                "coreRewardType": "CHAR",
                "coreRewardId": "char_333_sidero",
                "relevantActivityId": "act9d0",
                "mainlineData": null,
                "ssData": {
                    "name": "生于黑夜",
                    "desc": "这是一个佣兵的故事，战场之上，出生入死。\n这是一个追随者的故事，得他人信任，却未能守护。\n这是一个抗争者的故事，蔑视生死，从未停止战斗。\n这是W，与她同伴们的故事。",
                    "backgroundId": "storybg_darknights_memoir",
                    "tags": [
                        "tag_01",
                        "tag_13"
                    ],
                    "reopenActivityId": "act17d5",
                    "retroActivityId": "permanent_sub_1_Darknights_Memoir",
                    "isRecommended": true,
                    "recommendHideStageId": "act9d0_08",
                    "overrideStageList": null
                },
                "collectData": null
            },
    '''
    if table["storySetType"] == "MAINLINE":
        id = table["mainlineData"]["zoneId"]
        if id == None: 
            # main story from main_14 as activity
            # for ep 15, relavant id is act2mainss => 15 = 13+ 2, split act and mainss
            relavantId = table["relevantActivityId"]
            id = "main_" + str(13 + int(relavantId.split("act")[-1].split("mainss")[0]))
        # set backgrounId as storybg_main_#
        backgroundId = f"storybg_{id}.png"
        desc = None
    elif table["storySetType"] == "SS":
        id = table["relevantActivityId"]
        backgroundId = f"{table['ssData']['backgroundId']}.png" if table['ssData']['backgroundId'] else None
        desc = table['ssData']['desc'] if table['ssData']['desc'] else None
    elif table["storySetType"] == "COLLECT":
        id = table["relevantActivityId"]
        backgroundId = f"{table['collectData']['backgroundId']}.png" if table['collectData']['backgroundId'] else None
        desc = table['collectData']['desc'] if table['collectData']['desc'] else None

    # get kvImageId, titleImageId, gameMusicId
    simplified_table = {
        "id": id,
        "desc": desc,
        "kvImageId": f"{table['kvImageId']}.png" if table['kvImageId'] else None,
        "titleImageId": f"{table['titleImageId']}.png" if table['titleImageId'] else None,
        "gameMusicId": table['gameMusicId'],
        "backgroundId": backgroundId
    }
    return simplified_table

def get_story_meta_table(review_table: json, stage_table: Optional[json]) -> json:
    '''
    Merge story_review_table and stage_table to get story_meta_table
    '''
    story_meta_table = {
        "id": review_table["id"],
        "name": review_table["name"],
        "type": review_table["type"],
        "startTime": review_table["startTime"],
        "kvImageId": stage_table["kvImageId"] if stage_table else None,
        "titleImageId": stage_table["titleImageId"] if stage_table else None,
    }
    return story_meta_table

def get_review_info(review_table: json, stage_table: Optional[json], story_desc_path: str) -> json:
    '''
    Get review info from story_review_table and stage_table
    '''
    infoUnlockDatas = review_table["infoUnlockDatas"]
    info_list = []
    for data in infoUnlockDatas:
        if data['storyInfo'] is not None:
            try:
                # storyDesc = requests.get(f"{story_desc_path}/[uc]{data['storyInfo']}.txt").text
                storyDesc = open(f"{story_desc_path}/[uc]{data['storyInfo']}.txt", "r", encoding="utf-8").read()
            except FileNotFoundError:
                storyDesc = None
        else:
            storyDesc = None
        info = {
            "storyId": data["storyId"],
            "storyCode": data["storyCode"] if data["storyCode"] != "" else None,
            "storyName": data["storyName"],
            "storyDesc": storyDesc,
            "storyTxt": f"{data['storyTxt']}.txt",
            "avgTag": data["avgTag"]
        }
        info_list.append(info)
    review_info = {
        "id": review_table["id"],
        "name": review_table["name"],
        "desc": stage_table["desc"] if stage_table else None,
        "gameMusicId": stage_table["gameMusicId"] if stage_table else None,
        "backgroundId": stage_table["backgroundId"] if stage_table else None,
        "infoUnlockDatas": info_list
    }
    return review_info

def get_audio_table(gameMusicId: str, audio_data: json) -> json:
    musics_table = audio_data["musics"]
    bankAlias_table = audio_data["bankAlias"]
    bgmBanks_table = audio_data["bgmBanks"]

    music_value = next((item for item in musics_table if item["id"] == gameMusicId), None)
    bank_alias = music_value["bank"]
    bankName = bankAlias_table.get(str(bank_alias), bank_alias)
    # use copy to avoid duplicated .mp3.mp3. //TODO: But why??
    bank_info = copy.deepcopy(next((item for item in bgmBanks_table if item["name"] == bankName), None))
    if bank_info["intro"] is not None:
        bank_info["intro"] = bank_info["intro"].lower() + ".mp3"
    if bank_info["loop"] is not None:
        bank_info["loop"] = bank_info["loop"].lower() + ".mp3"
    return bank_info

def save_table(table: json, path: str):
    '''
    Save table to json file
    '''
    Path(path).parent.mkdir(parents=True, exist_ok=True)  # ensure assets/{server} exists
    with open(path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=4)

def main():
    # Load database config
    database = json.load(open("config/database.json", "r", encoding="utf-8"))
    SERVER_LIST = database["serverList"]
    STORY_REVIEW_TABLE_PATH = database["storyReviewTablePath"]
    STAGE_TABLE_PATH = database["stageTablePath"]
    AUDIO_DATA_PATH = database["audioDataPath"]
    STORY_INFO_PATH = database["storyInfoPath"]

    for server in SERVER_LIST:
        GAME_DATABASE_URL = database["gameDatabaseURLCN"] if server == "zh_CN" else database["gameDatabaseURLGlobal"]

        logger.info(f"Processing server: {server}...")
        # Load story_review_table
        logger.info(f"Loading story_review_table for server: {server}...")
        review_url = f"{GAME_DATABASE_URL}/{server}/{STORY_REVIEW_TABLE_PATH}"
        review_response = requests.get(review_url)
        review_table_origin = review_response.json()

        # Load stage_table
        logger.info(f"Loading stage_table for server: {server}...")
        stage_url = f"{GAME_DATABASE_URL}/{server}/{STAGE_TABLE_PATH}"
        stage_response = requests.get(stage_url)
        stage_table_origin = stage_response.json()["storylineStorySets"]
        stage_table_complement = json.load(open(f"assets/stage_table_complement.json", "r", encoding="utf-8"))
        # merge stage_table_origin and stage_table_complement
        # if there are same keys, update entries using stage_table_complement
        stage_table_origin.update(stage_table_complement)

        # Load audio_data
        logger.info(f"Loading audio_data for server: {server}...")
        audio_url = f"{GAME_DATABASE_URL}/{server}/{AUDIO_DATA_PATH}"
        audio_response = requests.get(audio_url)
        audio_data_origin = audio_response.json()

        review_table = {}
        logger.info(f"Simplifying story_review_table for server: {server}...")
        for id, entry in review_table_origin.items():
            if entry["actType"] in ["MINI_STORY", "ACTIVITY_STORY", "MAIN_STORY"]:
                simplified_review = simplify_story_review_table(entry)
                review_table[id] = simplified_review

        stage_table = {}
        logger.info(f"Simplifying stage_table for server: {server}...")
        for id, entry in stage_table_origin.items():
            if entry["storySetType"] in ["MAINLINE", "SS", "COLLECT"]:
                simplified_stage = simplify_stage_table(entry)
                # assign id as key, instead of using "setId_ssLine_act37side"
                stage_table[simplified_stage["id"]] = simplified_stage

        # print number of keys in review_table and stage_table
        logger.info(f"Number of entries in simplified story_review_table for server {server}: {len(review_table)}")
        logger.info(f"Number of entries in simplified stage_table for server {server}: {len(stage_table)}")

        story_meta_table = {}
        review_info_table = {}
        audio_data = {}

        home_bgm_info = get_audio_table("music_bg_default", audio_data_origin)
        audio_data[home_bgm_info["name"]] = home_bgm_info

        logger.info(f"Generating story_meta_table and review_info_table for server: {server}...")
        for id in review_table.keys():
            logger.info(f"Processing story id: {id}...")
            review_entry = review_table[id]
            stage_entry = stage_table.get(id, None)

            gameMusicId = stage_entry["gameMusicId"] if stage_entry else None
            if gameMusicId is not None:
                audio_info = get_audio_table(gameMusicId, audio_data_origin)
                audio_data[audio_info["name"]] = audio_info
                stage_entry["gameMusicId"] = audio_info["name"]

            story_meta_table[id] = get_story_meta_table(review_entry, stage_entry)

            # review_info = get_review_info(review_entry, stage_entry, f"{GAME_DATABASE_URL}/{server}/{STORY_INFO_PATH}")
            local_path = "assets_origin" if server == "zh_CN" else "assets_origin_yostar"
            review_info = get_review_info(review_entry, stage_entry, f"{local_path}/{server}/{STORY_INFO_PATH}")
            review_info_table[id] = review_info


        # Save story_meta_table and review_info_table
        logger.info(f"Saving story_meta_table and review_info_table for server: {server}...")
        save_table(story_meta_table, f"assets/{server}/story_meta_table.json")
        save_table(audio_data, f"assets/{server}/audio_data.json")
        for id, entry in review_info_table.items():
            save_table(entry, f"assets/{server}/story_review_info/{id}.json")

if __name__ == "__main__":
    main()


