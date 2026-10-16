from mcmanager.messages.base import Message, _validate_player

class Title(Message):
    def __init__(self, target, position="title"):
        if position not in ("title", "subtitle"):
            raise ValueError("Position must be 'title' or 'subtitle'.")

        super().__init__(target)
        self.position = position

    def __str__(self):
        return f"title {self.target} {self.position} {self.components()}"


def to_player(name):
    _validate_player(name)
    return Title(name)


def to_all():
    return Title("@a")


def subtitle_to_player(name):
    _validate_player(name)
    return Title(name, position="subtitle")


def subtitle_to_all():
    return Title("@a", position="subtitle")
