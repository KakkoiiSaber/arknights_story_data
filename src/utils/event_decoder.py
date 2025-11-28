import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
fmt = "%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
ch.setFormatter(logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S"))
logger.addHandler(ch)

# ---------------------------------------
# Helper: extract key=value props from [Command(foo=1, bar="xx")]
# ---------------------------------------
def extract_props(line: str) -> Dict[str, Any]:
    props: Dict[str, Any] = {}

    # Grab content inside parentheses: Command( ... )
    match = re.search(r'\((.*)\)', line)
    if not match:
        return props

    inner = match.group(1)

    # key=value, key="value", key=1.23
    # pairs = re.findall(r'(\w+)=(".*?"|\S+)', inner)
    pairs = re.findall(r'(\w+)\s*=\s*(".*?"|\S+)', inner)

    for key, value in pairs:
        value = value.strip()

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value == "true":
            value = True
        elif value == "false":
            value = False
        else:
            # try int / float, else keep as string
            try:
                if "." in value:
                    value = float(value)
                else:
                    value = int(value)
            except Exception:
                pass

        props[key] = value

    return props


# ---------------------------------------
# Main parser: one line -> one event dict
# ---------------------------------------
def decode_event(id: int, line: str) -> Dict[str, Any]:
    event: Dict[str, Any] = {"id": int(id), "raw": line}
    line = line.strip()

    # Empty line
    if not line:
        event["type"] = "empty"
        return event

    # --------------------------------------------------
    # Pattern 1: [name="XXX"] or [name= "XXX"] dialog / narration text
    # - If name is empty string ("") → treat as narration (location/time text)
    # --------------------------------------------------
    m = re.match(r'\[name\s*=\s*["\'](.*?)["\']\](.*)', line)
    if m:
        speaker = m.group(1).strip()
        content = m.group(2).strip()

        if speaker == "":
            # Narration / title card
            return {
                "id": id,
                "raw": line,
                "type": "narration",
                "content": content,
            }
        else:
            # Normal dialog
            return {
                "id": id,
                "raw": line,
                "type": "dialog",
                "speaker": speaker,
                "content": content,
            }

    # --------------------------------------------------
    # Pattern 2: multiline dialog
    # [multiline(name="XXX", delay=0.04, ...)]Text
    # --------------------------------------------------
    m = re.match(r'\[multiline\((.*?)\)\](.*)', line)
    if m:
        props_str = m.group(1)
        content = m.group(2).strip()

        props: Dict[str, Any] = {}
        pairs = re.findall(r'(\w+)=(".*?"|\S+)', props_str)

        for key, value in pairs:
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value == "true":
                value = True
            elif value == "false":
                value = False
            else:
                try:
                    if "." in value:
                        value = float(value)
                    else:
                        value = int(value)
                except Exception:
                    pass
            props[key] = value

        return {
            "id": id,
            "raw": line,
            "type": "dialog",
            "speaker": props.get("name"),
            "content": content,
            **props,
        }

    # --------------------------------------------------
    # Pattern 3: bugged delay syntax like [delay=0.51] or [Delay=2]
    # --------------------------------------------------
    m = re.match(r'\[(?:delay|Delay)\s*=\s*(\d+(\.\d+)?)\]', line)
    if m:
        sec = float(m.group(1))
        return {
            "id": id,
            "raw": line,
            "type": "delay",
            "time": sec,
        }

    # --------------------------------------------------
    # All supported commands (case-insensitive)
    # --------------------------------------------------
    KNOWN_COMMANDS = {
        # Backgrounds / BG animation
        "background": "background",
        "backgroundtween": "background_tween",
        "gridbg": "grid_background",
        "largebg": "large_bg",
        "largebgtween": "large_bg_tween",
        "verticalbg": "vertical_bg",
        "bgeffect": "bg_effect",

        # Music
        "playmusic": "play_music",
        "stopmusic": "stop_music",
        "stopmucis": "stop_music",   # typo in scripts
        "musicvolume": "music_volume",
        "musicvolune": "music_volume",  # typo

        # Sound
        "playsound": "play_sound",
        "stopsound": "stop_sound",
        "soundvolume": "sound_volume",
        "palysound": "play_sound",   # HG typo

        # Characters
        "charslot": "charslot",
        "charslsot": "charslot",     # typo
        "character": "character",
        "characteraction": "character_action",
        "charactercutin": "character_cutin",

        # Images
        "image": "image",
        "imagetween": "image_tween",
        "imagerotate": "image_rotate",
        "imgeffect": "image_effect",  # typo variant from logs

        # Text / dialog markers
        "subtitle": "subtitle",
        "dialog": "dialog_marker",
        "dialo": "dialog_marker",    # typo
        "dialogs": "dialogs_marker", # from 'Dialogs' log

        # Stickers & sticker control
        "sticker": "sticker",
        "stickerclear": "sticker_clear",

        # FX
        "effect": "effect",
        "camerashake": "camera_shake",
        "cameraeffect": "camera_effect",
        "focusout": "focus_out",
        "focusparam": "focus_param",

        # Curtain transitions
        "curtain": "curtain",

        # Timers
        "timersticker": "timer_sticker",
        "timerclear": "timer_clear",

        # CG items
        "cgitem": "cg_item",
        "hidecgitem": "hide_cg_item",

        # Item popup (story item images)
        "showitem": "show_item",
        "hideitem": "hide_item",

        # Warp (roguelike / special)
        "warp": "warp",

        # Special modes (theater mode, etc.)
        "theater": "theater_mode",

        # Branching logic
        "decision": "decision",
        "predicate": "predicate",

        # Interlude / mask channels (new)
        "interlude": "interlude",

        # Display helper for overlays (new)
        "avgdisplay": "avg_display",

        # Animated location text (new)
        "animtext": "anim_text",
        "animtextclean": "anim_text_clean",

        # Skip / video / tutorial / battle (from newer logs)
        "skipnode": "skip_node",
        "video": "video",
        "skiptothis": "skip_to_this",
        "startbattle": "start_battle",
        "tutorial": "tutorial_signal",
        "gotopage": "goto_page",

        # Delays (including script typos)
        "delay": "delay",
        "delayt": "delay",
        "delat": "delay",
        "delau": "delay",
        "dealy": "delay",
        "daley": "delay",

        # Misc / no-op
        "blocker": "blocker",
        "header": "header",
        "duration": "noop",  # bare [duration] we just ignore
        "chaa": "noop",      # appears alone, treat as no-op
    }

    # --------------------------------------------------
    # Pattern 4: generic [Command(...)] / [Command] (with optional trailing text)
    # --------------------------------------------------
    if line.startswith("[") and "]" in line:
        # Split once at first closing bracket to keep trailing text
        before, after = line.split("]", 1)
        cmd_part = before[1:]  # strip leading '['
        cmd_full = cmd_part.split("(", 1)[0].strip()
        cmd_lower = cmd_full.lower()

        if cmd_lower in KNOWN_COMMANDS:
            event["type"] = KNOWN_COMMANDS[cmd_lower]
            props = extract_props(line)
            event.update(props)

            extra_text = after.strip()
            if extra_text:
                # For things like animtext [...] <p=1>...</> or other trailing text
                event["content"] = extra_text

            return event

        # Unknown command → log and keep as 'unknown'
        event["type"] = "unknown"
        event["command"] = cmd_full
        event["message"] = "Unknown script command"

        logger.warning(
            f"[decode_event] Unknown command '{cmd_full}' at event {id}: {line}"
        )

        return event

    # --------------------------------------------------
    # Fallback: plain narration text
    # --------------------------------------------------
    return {
        "id": id,
        "raw": line,
        "type": "narration",
        "content": line,
    }
