---
name: lxd
description: Manage LXD containers — launch, configure users, networking, storage, and snapshots.
---

# LXD Skill

Manage LXD containers on Ubuntu hosts — launch, configure users, network, storage, and snapshots.

## When to Use

- User asks to create, start, stop, or manage LXD containers
- Setting up default users with sudo access on LXD containers
- Configuring LXD networking (bridges, NAT, DHCP)
- Managing storage pools (ZFS, dir, btrfs)
- Taking/restoring snapshots
- Any LXD/LXC CLI interaction

## Preferred Approach: Helper Scripts

For common multi-step operations, reach for scripts in `scripts/` first:

| Script | Purpose |
|--------|---------|
| `scripts/setup-user.sh` | Create a user with passwordless sudo + optional SSH key injection |

```bash
# Usage:
./scripts/setup-user.sh <container> <username> [ssh_public_key_file_or_url]

# Examples:
./scripts/setup-user.sh pi bernard
./scripts/setup-user.sh webapp deploy /home/bernard/.ssh/id_ed25519.pub
```

Scripts keep variables in scope, handle cleanup, and reduce the chance of typos or forgotten steps.

## Core Patterns

### Launch a Container

```bash
lxc launch ubuntu:24.04 <name>
```

### Set Up a User (Correct Way)

**Do NOT** use `@filepath` with `-c user.user-data=` — LXD passes the literal string as cloud-init data.

**Instead**, either:

1. **Manual setup (simplest, most reliable):**
   ```bash
   lxc exec <container> -- bash -c '
     useradd -m -s /bin/bash <username>
     usermod -aG sudo <username>
     echo "<username> ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/<username>
     chmod 440 /etc/sudoers.d/<username>
   '
   ```

2. **Cloud-init via config-set (after launch):**
   ```bash
   lxc launch ubuntu:24.04 <name>
   lxc config set <name> user.user-data "$(cat cloud-init.yaml)"
   lxc exec <name> -- cloud-init clean --reboot
   ```

3. **Use the helper script** — `scripts/setup-user.sh`

### Verify Setup

```bash
lxc exec <container> -- id <username>
lxc exec <container> -- sudo -n whoami   # should return "root"
```

### SSH Access

```bash
ssh <username>@<container-ip>
```

Get the IP with: `lxc list`

### Container Lifecycle

```bash
lxc start <container>
lxc stop <container> [-f]              # force kill
lxc restart <container>
lxc delete <container> [-f]
lxc exec <container> -- bash
lxc shell <container>                  # interactive shell
```

### Snapshots

```bash
lxc snapshot <container> <tag>
lxc restore <container> <snapshot-name>
lxc delete <container>/<snapshot-name>
```

### Networking

```bash
lxc network list
lxc network show lxdbr0
lxc config set <container> network.eth0.ipv4.address <static-ip>  # static IP
```

### Storage

```bash
lxc storage list
lxc storage create <pool-name> zfs source=/dev/sdX
lxc storage attach <pool-name> <disk-device> <container> <mount-point>
```

## Gotchas

| Pitfall | Correct Approach |
|---------|-----------------|
| `@filepath` with `-c user.user-data=` | Pass raw YAML content, or use `lxc config set` after launch |
| User not found after cloud-init | Cloud-init may not have run; use manual setup or trigger `cloud-init clean --reboot` |
| Containers can't get DHCP on OCI | May need `iptables -P FORWARD ACCEPT` or similar |
| `lxd init` needs user in `lxd` group | `sudo usermod -aG lxd $USER && newgrp lxd` |
| Snap updates breaking LXD | Pin snap: `snap refresh lxd --hold=forever` (rare) |

## Decision Rules

- **Simple user setup?** → Manual `lxc exec` one-liner or `scripts/setup-user.sh`
- **Complex provisioning (packages, config files)?** → Cloud-init YAML via `lxc config set`
- **Need reproducibility?** → Snapshot before changes, or use `lxc copy`
- **Multi-host management?** → Use LXD remote: `lxc remote add <name> <host>`

## Reference: Common Images

| Image | Command |
|-------|---------|
| Ubuntu 24.04 | `lxc launch ubuntu:24.04 <name>` |
| Ubuntu 22.04 | `lxc launch ubuntu:22.04 <name>` |
| Debian 12 | `lxc launch images:debian/12 <name>` |
| Alpine | `lxc launch images:alpine/3.19 <name>` |
| Custom image | `lxc launch local:<name> <dest>` |
