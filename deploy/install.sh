#!/usr/bin/env bash
# Install Lightman as a boot-time service on a Raspberry Pi (Raspberry Pi OS Bookworm or newer).
# Run from anywhere inside the copied repository:  bash deploy/install.sh
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$USER}"
CONFIG=/etc/lightman.toml
UNIT=/etc/systemd/system/lightman.service

echo "Installing Lightman from $INSTALL_DIR to run as $RUN_USER"

if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    echo "Python 3.11 or newer is required (found $(python3 --version))." >&2
    exit 1
fi

# venv support, and espeak for text-to-speech (voice is optional: Lightman runs without it).
sudo apt-get update
sudo apt-get install -y python3-venv espeak-ng
sudo apt-get install -y libespeak1 || echo "libespeak1 not available; voice feedback may be disabled."

python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

if [ ! -f "$CONFIG" ]; then
    sudo install -m 644 "$INSTALL_DIR/lightman.example.toml" "$CONFIG"
    echo "Created $CONFIG (all defaults). Edit it to set ports, GPS and the start/finish line."
else
    echo "Keeping existing $CONFIG"
fi

# Serial ports (OBD-II, GPS) and audio output.
sudo usermod -aG dialout,audio "$RUN_USER"

sed -e "s|@INSTALL_DIR@|$INSTALL_DIR|g" -e "s|@USER@|$RUN_USER|g" \
    "$INSTALL_DIR/deploy/lightman.service" | sudo tee "$UNIT" > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable lightman.service

echo
echo "Lightman will start at boot. Start it now with:  sudo systemctl start lightman"
echo "Logs:  journalctl -u lightman -f      Dashboard:  http://$(hostname).local:5000/"
