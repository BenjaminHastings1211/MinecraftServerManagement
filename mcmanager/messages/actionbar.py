from mcmanager.messages.base import Message, _validate_player

class Actionbar(Message):
    def __str__(self):
        return f"title {self.target} actionbar {self.components()}"


def to_player(name):
    _validate_player(name)
    return Actionbar(name)


def to_all():
    return Actionbar("@a")
