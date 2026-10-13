"""Entry point for `python -m mcmanager.listener <server-id>`."""

from mcmanager import cli
from mcmanager.listener.listener import main


cli.run(main)
