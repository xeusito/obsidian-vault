#!/bin/bash
# Install tempmon systemd timer + sudoers entry on the Pi.
# Run with:  sudo bash /home/pi/grocery-scanner/systemd/install.sh
set -euo pipefail

SRC="/home/pi/grocery-scanner/systemd"

# Sudoers — allow `pi` to run /sbin/shutdown without a password.
echo 'pi ALL=(ALL) NOPASSWD: /sbin/shutdown' > /etc/sudoers.d/grocery-scanner-shutdown
chmod 0440 /etc/sudoers.d/grocery-scanner-shutdown
visudo -c -f /etc/sudoers.d/grocery-scanner-shutdown

# systemd units
install -m 0644 "$SRC/grocery-tempmon.service" /etc/systemd/system/grocery-tempmon.service
install -m 0644 "$SRC/grocery-tempmon.timer"   /etc/systemd/system/grocery-tempmon.timer

systemctl daemon-reload
systemctl enable --now grocery-tempmon.timer

echo "OK. Status:"
systemctl status --no-pager grocery-tempmon.timer
