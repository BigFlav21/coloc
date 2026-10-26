#!/usr/bin/env bash
# Gère les colocataires dans le conteneur : ./scripts/seed.sh add Flav | reset Flav | list
source "$(dirname "$0")/_common.sh"
dc exec app python -m app.seed "$@"
