#!/usr/bin/env bash
# Install the ipynb->py pre-commit hook into .git/hooks/.
# Idempotent: re-running just refreshes the symlink.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
hook_src="$repo_root/tools/hooks/pre-commit"
hook_dst="$repo_root/.git/hooks/pre-commit"

if [ ! -x "$hook_src" ]; then
    chmod +x "$hook_src"
fi

if [ -e "$hook_dst" ] && [ ! -L "$hook_dst" ]; then
    backup="$hook_dst.backup.$(date +%s)"
    echo "Existing non-symlink hook found; backing up to $backup"
    mv "$hook_dst" "$backup"
fi

ln -sf ../../tools/hooks/pre-commit "$hook_dst"
echo "Installed: $hook_dst -> tools/hooks/pre-commit"
