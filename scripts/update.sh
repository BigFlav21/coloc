#!/usr/bin/env bash
# Met à jour uniquement ce projet : git pull + rebuild + relance.
source "$(dirname "$0")/_common.sh"
git pull --ff-only
dc up -d --build
