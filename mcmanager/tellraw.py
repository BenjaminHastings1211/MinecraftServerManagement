"""
Build /tellraw commands piece by piece.

    from mcmanager.messages import tellraw

    message = (
        tellraw.to_player("Steve")
        .text("Welcome ", bold=True, color="red")
        .text("Steve", color="gold", hover="First visit!")
        .text(" [spawn]", color="aqua", click_command="/spawn")
    )

    server.notify(message)           # or server.command(str(message))

Each text() is styled on its own; styles don't carry over to the next
piece. Colours are Minecraft's names (see COLOURS) or "#RRGGBB" hex.
"""

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

    raise ValueError(
        f"Unknown colour: {value!r}. Use one of {', '.join(COLOURS)} or '#RRGGBB'."
    )


class Tellraw:
    def __init__(self, target):
        self.target = target
        self.parts = []

    def text(self, text, color=None, hover=None, click_command=None, **styles):
        """
        Add a piece of text. styles are bold, italic, underlined,
        strikethrough and obfuscated (True/False). hover is text shown
        on mouse-over; click_command runs when the text is clicked.
        """
        part = {"text": str(text)}

        if color is not None:
            part["color"] = _colour(color)

        for name, value in styles.items():
            if name not in STYLES:
                raise ValueError(f"Unknown style: {name}. Use {', '.join(STYLES)}.")

            if value:
                part[name] = True

        if hover is not None:
            part["hover_event"] = {"action": "show_text", "value": str(hover)}

        if click_command is not None:
            part["click_event"] = {"action": "run_command", "command": click_command}

        self.parts.append(part)
        return self

    def __str__(self):
        # The leading "" keeps the first piece's style from spreading to the rest.
        component = json.dumps(["", *self.parts], ensure_ascii=False, separators=(",", ":"))
        return f"tellraw {self.target} {component}"

    def __repr__(self):
        return f"Tellraw({str(self)!r})"


def to_player(name):
    """A message for one player, by name."""
    if not _PLAYER_NAME.match(name):
        raise ValueError(f"Not a player name: {name!r}")

    return Tellraw(name)


def to_all():
    """A message for everyone online."""
    return Tellraw("@a")
