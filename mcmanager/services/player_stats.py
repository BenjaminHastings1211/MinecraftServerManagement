import json
from pathlib import Path


class PlayerStatsService:
    def __init__(self, stats_dir):
        self.stats_dir = Path(stats_dir)
        self._cache = {}

    def get(self, uuid):
        """Return cached stats, loading them if necessary."""
        if uuid not in self._cache:
            return self.reload(uuid)

        return self._cache[uuid]

    def reload(self, uuid):
        """Reload a player's stats from disk."""
        path = self.stats_dir / f"{uuid}.json"

        try:
            with path.open("r", encoding="utf-8") as file:
                stats = json.load(file)
        except FileNotFoundError:
            self._cache.pop(uuid, None)
            return None

        self._cache[uuid] = stats
        return stats

    def reload_all(self):
        """Reload stats for all player UUIDs found in the stats directory."""
        for path in self.stats_dir.glob("*.json"):
            self.reload(path.stem)

    def unload(self, uuid):
        """Remove a player's stats from the cache."""
        self._cache.pop(uuid, None)

    def clear(self):
        """Clear the entire cache."""
        self._cache.clear()

    def get_playtime_seconds(self, uuid):
        stats = self.get(uuid)

        if stats is None:
            return None

        ticks = stats.get("stats", {}).get(
            "minecraft:custom", {}
        ).get("minecraft:play_time", 0)

        return ticks // 20

    def get_deaths(self, uuid):
        stats = self.get(uuid)

        if stats is None:
            return None

        return stats.get("stats", {}).get(
            "minecraft:custom", {}
        ).get("minecraft:deaths", 0)