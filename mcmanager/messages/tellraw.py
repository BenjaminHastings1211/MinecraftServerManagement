from mcmanager.messages.base import Message, _validate_player

class Tellraw(Message):
    def __str__(self):
        return f"tellraw {self.target} {self.components()}"


def to_player(name):
    _validate_player(name)
    return Tellraw(name)


def to_all():
    return Tellraw("@a")
