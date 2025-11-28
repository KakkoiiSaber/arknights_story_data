
import json
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
fmt = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
ch.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(ch)

def main():
    database = json.load(open("config/database.json", "r", encoding="utf-8"))
    SERVER_LIST = database["serverList"]
    for server in SERVER_LIST:
        review_cache_path = f"cache/{server}/review.json"
        story_cache_path = f"cache/{server}/story.json"
        # write empty json file with []
        try:
            with open(review_cache_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            with open(story_cache_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            logger.info(f"[Server: {server}] Cleared cache files.")
        except Exception as e:
            logger.error(f"[Server: {server}] Error clearing cache files: {e}")

if __name__ == "__main__":
    main()