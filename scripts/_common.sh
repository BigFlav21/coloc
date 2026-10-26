#!/usr/bin/env bash
# Toutes les commandes ne portent que sur le projet compose "coloc".
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  echo "Fichier .env manquant : cp .env.example .env puis remplis-le." >&2
  exit 1
fi
dc() { docker compose -p coloc "$@"; }
