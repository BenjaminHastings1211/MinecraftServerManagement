#!/bin/bash

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="/usr/local/bin"

# Command name -> script filename
declare -A COMMANDS=(
    [mc-confirm]="confirm_eula.py"
    [mc-delete]="delete_server.py"
    [mc-list]="list_servers.py"
    [build-rcon]="restart_rcon.py"
    [mc-cmd]="send_command.py"
    [mc-backup]="smart_backup.py"
    [mc-stop]="stop_server.py"
    [mc-create]="create_server.py"
    [mc-monitor]="monitor_server.py"
    [mc-config]="set_config.py"
    [mc-start]="start_server.py"
    [mc-upgrade]="upgrade_server.py"
)

echo "Setting up Minecraft commands..."
echo "Project root: $ROOT"
echo

for command in "${!COMMANDS[@]}"; do
    target="$ROOT/scripts/${COMMANDS[$command]}"
    link="$BIN/$command"

    if [[ ! -f "$target" ]]; then
        echo "Skipping $command: $target not found"
        continue
    fi

    if [[ -L "$link" && "$(readlink "$link")" == "$target" ]]; then
        echo "Already configured: $command"
        continue
    fi

    if [[ -e "$link" || -L "$link" ]]; then
        echo "Replacing existing command: $link"
    fi

    sudo ln -sfn "$target" "$link"
    echo "Linked: $command -> $target"
done

echo
echo "Command setup complete."