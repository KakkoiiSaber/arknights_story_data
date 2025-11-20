import json

def get_story_meta_table():
    print("Generating story_meta_table...")
    database = json.load(open("config/database.json", "r", encoding="utf-8"))
    SERVER_LIST = database["serverList"]

    for server in SERVER_LIST:
        print(f"Processing server: {server}...")
        story_review_table = json.load(open(f"assets/{server}/story_review_table.json", "r", encoding="utf-8"))
        stage_table = json.load(open(f"assets/{server}/stage_table.json", "r", encoding="utf-8"))
        story_meta_table = {}
        for key, value in story_review_table.items():
            print(f"Processing story meta info for id: {key}...")
            if key in stage_table.keys():
                # merge two dict
                story_meta_table[key] = {**value, **stage_table[key]}
                # sort infoUnlockDatas to be the last
                infoUnlockDatas = story_meta_table[key].pop("infoUnlockDatas")
                story_meta_table[key]["infoUnlockDatas"] = infoUnlockDatas
        with open(f"assets/{server}/story_meta_table.json", "w", encoding="utf-8") as f:
            json.dump(story_meta_table, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    get_story_meta_table()


