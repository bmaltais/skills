#!/usr/bin/env bash
# setup-user.sh — Create a user in an LXD container with passwordless sudo and optional SSH key.
#
# Usage:
#   ./setup-user.sh <container> <username> [ssh_public_key_file_or_url]
#
# Examples:
#   ./setup-user.sh pi bernard
#   ./setup-user.sh webapp deploy /home/bernard/.ssh/id_ed25519.pub
#   ./setup-user.sh webapp deploy https://github.com/deploykey.keys

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <container> <username> [ssh_public_key_file_or_url]" >&2
  exit 1
fi

CONTAINER="$1"
USERNAME="$2"
SSH_KEY_FILE="${3:-}"

# Check container exists and is running
STATE=$(lxc info "$CONTAINER" 2>/dev/null | grep -i "^Status:" | awk '{print $2}' || true)
if [[ -z "$STATE" ]]; then
  echo "Error: container '$CONTAINER' not found" >&2
  exit 1
fi

echo "Setting up user '$USERNAME' in container '$CONTAINER'..."

# Create user and grant passwordless sudo
lxc exec "$CONTAINER" -- bash -c "
  # Create user with home directory and bash
  useradd -m -s /bin/bash '${USERNAME}'

  # Add to sudo group
  usermod -aG sudo '${USERNAME}'

  # Set up passwordless sudo
  echo '${USERNAME} ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/${USERNAME}
  chmod 440 /etc/sudoers.d/${USERNAME}
"

echo "  ✓ User '${USERNAME}' created with passwordless sudo"

# Inject SSH key if provided
if [[ -n "$SSH_KEY_FILE" ]]; then
  SSH_KEY=""

  if [[ -f "$SSH_KEY_FILE" ]]; then
    SSH_KEY=$(cat "$SSH_KEY_FILE")
  elif echo "$SSH_KEY_FILE" | grep -qE '^https?://'; then
    SSH_KEY=$(curl -sf "$SSH_KEY_FILE" 2>/dev/null || echo "")
  else
    echo "Warning: '$SSH_KEY_FILE' is neither a file nor a URL, skipping SSH key injection" >&2
  fi

  if [[ -n "$SSH_KEY" ]]; then
    lxc exec "$CONTAINER" -- bash -c "
      mkdir -p /home/${USERNAME}/.ssh
      echo '${SSH_KEY}' >> /home/${USERNAME}/.ssh/authorized_keys
      chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/.ssh
      chmod 700 /home/${USERNAME}/.ssh
      chmod 600 /home/${USERNAME}/.ssh/authorized_keys
    "
    echo "  ✓ SSH key injected for '${USERNAME}'"
  fi
fi

# Verify
echo ""
echo "Verification:"
lxc exec "$CONTAINER" -- id "$USERNAME"
lxc exec "$CONTAINER" -- sudo -n whoami

echo ""
echo "Done. SSH access: ssh ${USERNAME}@\$(lxc list $CONTAINER | awk 'NR>2{print \$3}')"
