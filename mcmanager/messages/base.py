
import json
import re

COLOURS = (
    "black", "dark_blue", "dark_green", "dark_aqua",
    "dark_red", "dark_purple", "gold", "gray",
    "dark_gray", "blue", "green", "aqua",
    "red", "light_purple", "yellow", "white",
)

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PLAYER_NAME = re.compile(r"^\w{1,16}$")

STYLES = ("bold", "italic", "underlined", "strikethrough", "obfuscated")


def _colour(value):
    if value in COLOURS or _HEX.match(value):
        return value
    raise ValueError(f"Unknown colour: {value!r}")


class Message:
    def __init__(self, target):
        self.target = target
        self.parts = []

    def text(self, text, color=None, hover=None, click_command=None, **styles):
        part = {"text": str(text)}

        if color is not None:
            part["color"] = _colour(color)

        for name, value in styles.items():
            if name not in STYLES:
                raise ValueError(f"Unknown style: {name}")
            if value:
                part[name] = True

        if hover is not None:
            part["hover_event"] = {
                "action": "show_text",
                "value": str(hover),
            }

        if click_command is not None:
            part["click_event"] = {
                "action": "run_command",
                "command": click_command,
            }

        self.parts.append(part)
        return self

    def components(self):
        return json.dumps(
            ["", *self.parts],
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def __repr__(self):
        return f"{type(self).__name__}({str(self)!r})"


def _validate_player(name):
    if not _PLAYER_NAME.fullmatch(name):
        raise ValueError(f"Not a player name: {name!r}")
