import json
from pathlib import Path


class PlayerStatsService:
    def __init__(self, stats_dir):
        self.stats_dir = Path(stats_dir)
        self._cache = {}

    def get(self, uuid):
        """Return cached player stats, loading them if necessary."""
        if uuid not in self._cache:
            return self.reload(uuid)

        return self._cache[uuid]

    def reload(self, uuid):
        """Reload a player's stats JSON file from disk."""
        path = self.stats_dir / f"{uuid}.json"

        try:
            with path.open("r", encoding="utf-8") as file:
                stats = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            self._cache.pop(uuid, None)
            return None

        self._cache[uuid] = stats
        return stats

    def reload_all(self):
        """Reload stats for every player with a JSON file."""
        if not self.stats_dir.is_dir():
            return

        for path in self.stats_dir.glob("*.json"):
            self.reload(path.stem)

    def unload(self, uuid):
        """Remove a player's stats from the cache."""
        self._cache.pop(uuid, None)

    def clear(self):
        """Clear all cached player stats."""
        self._cache.clear()

    def get_player_stats(self, uuid):
        """Return the player's stats dictionary, or None if unavailable."""
        data = self.get(uuid)

        if data is None:
            return None

        return data.get("stats", {})

    def get_custom_stats(self, uuid):
        """Return the player's custom stats, or None if unavailable."""
        stats = self.get_player_stats(uuid)

        if stats is None:
            return None

        return stats.get("minecraft:custom", {})

    def get_playtime_seconds(self, uuid):
        """Return lifetime playtime in seconds."""
        custom = self.get_custom_stats(uuid)

        if custom is None:
            return None

        return custom.get("minecraft:play_time", 0) // 20

    def get_deaths(self, uuid):
        """Return the death count from Minecraft's stats."""
        custom = self.get_custom_stats(uuid)

        if custom is None:
            return None

        return custom.get("minecraft:deaths", 0)

    def get_mobs_killed(self, uuid):
        """Return the player's total mob kills."""
        custom = self.get_custom_stats(uuid)

        if custom is None:
            return None

        return custom.get("minecraft:mob_kills", 0)

    def get_blocks_mined(self, uuid):
        """Return total blocks mined across all block types."""
        stats = self.get_player_stats(uuid)

        if stats is None:
            return None

        return sum(stats.get("minecraft:mined", {}).values())

    def get_distance_traveled_km(self, uuid):
        """Return total distance traveled in kilometers."""
        custom = self.get_custom_stats(uuid)

        if custom is None:
            return None

        distance_cm = sum(
            value
            for key, value in custom.items()
            if key.endswith("_one_cm")
        )

        return distance_cm / 100000

    def get_fish_caught(self, uuid):
        """Return the number of fish caught."""
        custom = self.get_custom_stats(uuid)

        if custom is None:
            return None

        return custom.get("minecraft:fish_caught", 0)

    def get_animals_bred(self, uuid):
        """Return the number of animals bred."""
        custom = self.get_custom_stats(uuid)

        if custom is None:
            return None

        return custom.get("minecraft:animals_bred", 0)

    def get_villager_trades(self, uuid):
        """Return the number of trades with villagers."""
        custom = self.get_custom_stats(uuid)

        if custom is None:
            return None

        return custom.get("minecraft:traded_with_villager", 0)