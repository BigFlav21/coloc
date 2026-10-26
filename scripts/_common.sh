#!/usr/bin/env bash
# Toutes les commandes ne portent que sur le projet compose "coloc".
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  echo "Fichier .env manquant : cp .env.example .env puis remplis-le." >&2
  exit 1
fi
# Le conteneur écrit dans ./data avec l'uid de l'utilisateur courant.
# Le dossier doit exister avant le démarrage, sinon Docker le crée en root.
export COLOC_UID="$(id -u)" COLOC_GID="$(id -g)"
mkdir -p data
dc() { docker compose -p coloc "$@"; }
