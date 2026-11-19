#!/usr/bin/env bash
for f in "$@"; do case "$f" in .env|*/.env|*.sqlite) echo "Refusing to commit $f"; exit 1;; esac; done
