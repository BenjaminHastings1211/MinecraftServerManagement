#!/usr/bin/env python3
"""mc-setconfig: interactively override a server.properties value."""

import _bootstrap

from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter
from prompt_toolkit.shortcuts import CompleteStyle

from mcmanager import cli


def select_property(keys):
    completer = FuzzyWordCompleter(sorted(keys), WORD=True)

    while True:
        key = prompt(
            "Search property: ",
            completer=completer,
            complete_while_typing=True,
            complete_style=CompleteStyle.MULTI_COLUMN,
        ).strip()

        if key in keys:
            return key

        print(f"Unknown property: {key}. Try again.\n")


def main():
    parser = cli.parser(
        "Pick a server.properties key and set an override for it in "
        "config.json. Overrides are applied every time the server starts.",
        target=cli.ONE,
    )
    args = parser.parse_args()

    (server,) = cli.resolve(args.server)

    if not server.properties_path.is_file():
        raise cli.CommandError(f"{cli.server_label(server)} has no server.properties yet.")

    key = select_property(server.server_properties().keys())
    current = server.get_property(key, "")
    value = prompt(f"{key} [{current}]: ").strip()

    if not value or value == current:
        print("Unchanged.")
        return

    server.config["properties"][key] = value
    server.save()

    print(cli.green(f"\nUpdated {cli.server_label(server)}"))
    print(f"  {key} = {value}")

    if server.is_running():
        print(f"  Takes effect after a restart (mc-stop {server.id}, then mc-start {server.id}).")


if __name__ == "__main__":
    cli.run(main)
