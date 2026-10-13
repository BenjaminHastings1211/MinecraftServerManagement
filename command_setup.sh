#!/bin/bash

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="/usr/local/bin"

# Command name -> script filename
declare -A COMMANDS=(
    [mc-confirm]="mc-confirm.py"
    [mc-delete]="mc-delete.py"
    [mc-list]="mc-list.py"
    [build-rcon]="build-rcon.py"
    [mc-cmd]="mc-cmd.py"
    [mc-backup]="mc-backup.py"
    [mc-stop]="mc-stop.py"
    [mc-create]="mc-create.py"
    [mc-monitor]="mc-monitor.py"
    [mc-config]="mc-config.py"
    [mc-start]="mc-start.py"
    [mc-upgrade]="mc-upgrade.py"
)

echo "Setting up Minecraft commands..."
echo "Project root: $ROOT"
echo

# Remove existing Minecraft command symlinks.
echo "Removing existing Minecraft command symlinks..."

shopt -s nullglob

for link in "$BIN"/mc-* "$BIN"/build-rcon; do
    if [[ -L "$link" ]]; then
        echo "Removing: $link"
        sudo rm "$link"
    fi
done

echo
echo "Creating command symlinks..."

for command in "${!COMMANDS[@]}"; do
    target="$ROOT/scripts/${COMMANDS[$command]}"
    link="$BIN/$command"

    if [[ ! -f "$target" ]]; then
        echo "Skipping $command: $target not found"
        continue
    fi

    sudo ln -s "$target" "$link"
    echo "Linked: $command -> $target"
done

echo
echo "Command setup complete."