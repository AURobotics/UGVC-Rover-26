#!/usr/bin/env bash
set -e

echo "=== Configuring MiKTeX Auto-Package Downloads ==="
# Set MiKTeX to install missing packages automatically without asking (On-the-fly)
initexmf --set-config-value [MPM]AutoInstall=1

echo "=== Updating MiKTeX Package Databases ==="
# Synchronize package database repositories
miktex packages update-package-database

echo "=== Upgrading Existing Installed Packages ==="
# Upgrade pre-installed system packages to their newest versions
miktex packages update

echo "=== MiKTeX Setup Complete ==="