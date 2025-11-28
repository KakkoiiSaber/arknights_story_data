import json
import logging
from typing import Optional
from pathlib import Path
import re

from utils.save_json import save_json
from utils.event_decoder import decode_event

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
fmt = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
ch.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(ch)



def txt2json(txt_file: str, story_variables: json) -> dict:
    events_table = []
    for line_number, line in enumerate(txt_file.splitlines(), start=1):
        event = decode_event(line_number, line)
        match event["type"]:
            case "image" | "background":
                try:
                    event["image"] = f"{event["image"]}.png"
                except Exception as e:
                    pass
            case "charslot":
                try:
                    event["name"] = f"{event["name"]}.png"
                except Exception as e:
                    pass
            case "play_music" | "play_sound":
                try:
                    var = event["intro"].split("$")[1]
                    event["intro"] = story_variables[var].lower() + ".mp3"
                except Exception as e:
                    # logger.debug(f"Error processing play_music event at line {line_number}: {e}")
                    pass
                try:
                    var = event["key"].split("$")[1]
                    event["key"] = story_variables[var].lower() + ".mp3"
                except Exception as e:
                    # logger.debug(f"Error processing play_music event at line {line_number}: {e}")
                    pass

        events_table.append(event)
    return events_table

def main():
    # Load database config
    database = json.load(open("config/database.json", "r", encoding="utf-8"))
    GAME_DATABASE_CN = database["gameDatabaseCN"]
    GAME_DATABASE_GLOBAL = database["gameDatabaseGlobal"]
    STORY_PATH = database["storyPath"]
    STORY_VARIABLES_PATH = database["storyVariablesPath"]
    SERVER_LIST = database["serverList"]

    for server in SERVER_LIST:
    # for server in ["zh_CN"]:
        logger.debug(f"[Server: {server}] Loading story_meta_table...")
        story_meta_table = json.load(open(f"assets/{server}/story_meta_table.json", "r", encoding="utf-8"))
        logger.debug(f"[Server: {server}] Loading storyCache...")
        storyCache = json.load(open(f"cache/{server}/story.json", "r", encoding="utf-8"))
        story_variables = json.load(open(f"{GAME_DATABASE_CN}/{server}/{STORY_VARIABLES_PATH}" if server == "zh_CN" else f"{GAME_DATABASE_GLOBAL}/{server}/{STORY_VARIABLES_PATH}", "r", encoding="utf-8"))

        for id in story_meta_table.keys():
            if id in storyCache:
                logger.debug(f"[Server: {server}] Story {id} found in cache, skip.")
                continue
            else:
                logger.debug(f"[Server: {server}] Story {id} not found in cache, fetching...")
                logger.info(f"[Server: {server}] Processing story {id}...")

                logger.debug(f"[Server: {server}] Loading review info for story {id}...")
                review_info = json.load(open(f"assets/{server}/story_review_info/{id}.json", "r", encoding="utf-8"))
                for info in review_info["infoUnlockDatas"]:
                    storyTxtBasePath = f"{GAME_DATABASE_CN}/{server}/{STORY_PATH}" if server == "zh_CN" else f"{GAME_DATABASE_GLOBAL}/{server}/{STORY_PATH}"
                    storyTxtPath = info["storyTxt"]
                    try:
                        logger.debug(f"[Server: {server}] Loading story txt file: {storyTxtBasePath}/{storyTxtPath}...")
                        storyTxt = open(f"{storyTxtBasePath}/{storyTxtPath}", "r", encoding="utf-8").read()
                        # process each line of the txt file
                        events_table = txt2json(storyTxt, story_variables)
                        save_json(events_table, f"assets/{server}/story/{storyTxtPath.replace('.txt', '.json')}")
                    except Exception as e:
                        logger.error(f"[Server: {server}] Failed to load story txt file: {storyTxtBasePath}/{storyTxtPath}. Error: {e}")
                        continue

                storyCache.append(id)
        # save_json(storyCache, f"cache/{server}/story.json")

if __name__ == "__main__":
    main()