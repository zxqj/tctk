#! /bin/bash

uv tool uninstall tctk
rm -r build dist *.egg-info
uv build
uv tool install --no-cache .
