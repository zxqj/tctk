#! /bin/bash

uv tool uninstall tctk
rm -r build dist *.egg-info
rm -r tctk/__pyc*
uv build
uv tool install --no-cache .
