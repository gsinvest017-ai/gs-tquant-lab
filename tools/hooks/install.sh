#!/usr/bin/env bash
# Install the ipynb->py git hooks (pre-commit + pre-push) into .git/hooks/.
# Idempotent: re-running just refreshes the symlinks.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)

for hook in pre-commit pre-push; do
    hook_src="$repo_root/tools/hooks/$hook"
    hook_dst="$repo_root/.git/hooks/$hook"

    if [ ! -x "$hook_src" ]; then
        chmod +x "$hook_src"
    fi

    if [ -e "$hook_dst" ] && [ ! -L "$hook_dst" ]; then
        backup="$hook_dst.backup.$(date +%s)"
        echo "Existing non-symlink hook found; backing up to $backup"
        mv "$hook_dst" "$backup"
    fi

    ln -sf "../../tools/hooks/$hook" "$hook_dst"
    echo "Installed: $hook_dst -> tools/hooks/$hook"
done
