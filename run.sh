#! /bin/bash

export TWITCH_CREDENTIALS_PATH="$HOME/.config/twitch.yaml"
uv run -m tctk
