from mcmanager.messages.base import Message, _validate_player

class Tellraw(Message):
    def __str__(self):
        return f"tellraw {self.target} {self.components()}"


def to_player(name):
    _validate_player(name)
    return Tellraw(name)


def to_all():
    return Tellraw("@a")

def duration(seconds):
    """Format seconds as e.g. '2d 3h 14m', '5m 12s', or '42s'."""
    seconds = int(seconds or 0)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"