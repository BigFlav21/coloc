#!/usr/bin/env bash
source "$(dirname "$0")/_common.sh"
dc logs -f --tail=100 app
