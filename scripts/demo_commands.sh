#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m agent.app ask "How long does a regular customer have to return an unused backpack?"
python3 -m agent.app ask "Where is ORD-1007 and when should it arrive?" --debug
printf 'Do you ship internationally?\nWhat about Canada, and how long does it take?\nexit\n' | python3 -m agent.app chat
python3 -m agent.app ask "Can I put the entire Breeze Tumbler in the dishwasher?"
python3 evals/run_evals.py

