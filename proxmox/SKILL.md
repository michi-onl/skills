---
name: proxmox
description: "Manage a Proxmox VE server over SSH. Covers VM and LXC lifecycle (start, stop, create, destroy), configuration editing, snapshots, backups, storage, monitoring, networking, templates, and maintenance. TRIGGER when: user mentions Proxmox, PVE, pve, QEMU, KVM, LXC containers, VM management on their server, container IDs (e.g. 'container 103'), named VMs/containers (e.g. 'home assistant VM', 'metube container'), network bridges (vmbr0), server resource adjustments (memory, CPU, disk for VMs/containers), snapshots, backups, storage pools, or server status/updates. Also trigger when the user says 'check my server', 'list my VMs', or refers to their homelab. DO NOT TRIGGER when: user asks about Docker, docker-compose, VirtualBox, cloud VPS providers, Raspberry Pi, or conceptual virtualization questions with no server management intent."
---

# Proxmox VE Management

You manage a single-node Proxmox VE server via SSH. Every command runs through:

```
ssh root@<PROXMOX_IP> '<command>'
```

Use the Bash tool for all SSH commands. Quote the remote command in single quotes to avoid local shell expansion. For commands with single quotes inside, use double quotes or escaping as needed.

## Core principles

**Read before write.** Always show the current state before making changes. For config edits, display the current config and get user confirmation before applying.

**Confirm before destroying.** Any operation that deletes data, destroys a VM/LXC, overwrites a backup, or could cause downtime requires explicit user confirmation. This includes: `qm destroy`, `pct destroy`, `qm rollback`, `pct rollback`, `qm restore` (overwriting), `pct restore` (overwriting), `rm` of backup files, and `reboot`.

**Summarize output.** Don't dump raw CLI output. Parse it and present it in tables or concise summaries. Show VMID and name together (e.g., `101 (debian-web)`).

**Be efficient with SSH.** Combine related queries into a single SSH call when possible, using `&&` or `;` to chain commands. This avoids unnecessary round trips.

## Tool reference

### VM management (QEMU)
- `qm list` — list all VMs
- `qm status <vmid>` — check VM status
- `qm start/stop/reboot/suspend/resume <vmid>` — lifecycle
- `qm config <vmid>` — show config
- `qm set <vmid> [options]` — modify config (e.g., `--memory 4096 --cores 2`)
- `qm destroy <vmid>` — delete VM (DESTRUCTIVE)
- `qm clone <vmid> <newid> --name <name>` — clone
- `qm template <vmid>` — convert to template
- `qm snapshot <vmid> <snapname>` — create snapshot
- `qm listsnapshot <vmid>` — list snapshots
- `qm rollback <vmid> <snapname>` — rollback (DESTRUCTIVE)
- `qm delsnapshot <vmid> <snapname>` — delete snapshot

### Container management (LXC)
- `pct list` — list all containers
- `pct status <ctid>` — check container status
- `pct start/stop/reboot/suspend/resume <ctid>` — lifecycle
- `pct config <ctid>` — show config
- `pct set <ctid> [options]` — modify config
- `pct destroy <ctid>` — delete container (DESTRUCTIVE)
- `pct clone <ctid> <newid>` — clone
- `pct template <ctid>` — convert to template
- `pct snapshot <ctid> <snapname>` — create snapshot
- `pct listsnapshot <ctid>` — list snapshots
- `pct rollback <ctid> <snapname>` — rollback (DESTRUCTIVE)
- `pct delsnapshot <ctid> <snapname>` — delete snapshot
- `pct exec <ctid> -- <command>` — run command inside container
- `pct enter <ctid>` — (interactive, avoid in scripts)

### Backups
- `vzdump <vmid> --storage <storage> --mode snapshot` — backup a VM/LXC
- `vzdump <vmid> --compress zstd` — backup with compression
- List backups: `ls -lh /var/lib/vz/dump/` or check the configured backup storage
- Restore VM: `qmrestore <backup-file> <vmid>`
- Restore LXC: `pct restore <ctid> <backup-file>`

### Storage
- `pvesm status` — list storage pools with usage
- `pvesm list <storage>` — list volumes in a storage pool
- `pvesm alloc <storage> <vmid> <filename> <size>` — allocate disk
- `pvesm free <storage>:<volume>` — free volume
- `df -h` — filesystem usage
- `zpool status` — ZFS pool health (if ZFS is used)
- `zpool list` — ZFS pool capacity
- `zfs list` — ZFS datasets

### Monitoring
- `pvesh get /nodes/localhost/status` — node status (CPU, memory, uptime)
- `pvesh get /cluster/resources --type vm` — all VMs/LXCs with resource usage
- `top -bn1 | head -20` — process overview
- `free -h` — memory usage
- `iostat -x 1 2` — disk I/O (if sysstat installed)
- `journalctl -u pvedaemon --since '1 hour ago'` — recent PVE logs
- `journalctl -u pve-cluster --since '1 hour ago'` — cluster logs
- `systemctl status pvedaemon pveproxy pvestatd` — PVE service status
- `cat /var/log/syslog | tail -50` — recent syslog

### Networking
- `cat /etc/network/interfaces` — network config
- `ip addr` — current IP addresses
- `ip link` — network interfaces
- `brctl show` — bridge details
- `pvesh get /nodes/localhost/network` — PVE network config
- Firewall: `pve-firewall status`, rules in `/etc/pve/firewall/`

### Maintenance
- `apt update && apt list --upgradable` — check for updates
- `apt upgrade -y` — apply updates (confirm first)
- `pveversion -v` — Proxmox version info
- `uptime` — system uptime
- `reboot` — reboot node (DESTRUCTIVE, confirm first)
- `unattended-upgrades --dry-run --verbose` — test auto-upgrade config
- `journalctl -u unattended-upgrades` — auto-upgrade log

### PVE Backup Jobs (built-in scheduler)
PVE has a native backup scheduler that shows history in the UI. Manage via `pvesh`:

```bash
# List jobs
pvesh get /cluster/backup --output-format json

# Create job — note: retention uses --prune-backups, NOT --keep-last
pvesh create /cluster/backup \
  --schedule "00:30" \
  --storage local \
  --mode snapshot \
  --compress zstd \
  --vmid "101,102,103" \
  --enabled 1 \
  --prune-backups "keep-last=2" \
  --mailnotification failure \
  --comment "Description"

# Delete job
pvesh delete /cluster/backup/<job-id>
```

Use `pvesh usage /cluster/backup --verbose` to see all available options. The `--keep-last` flag does NOT exist — retention is always via `--prune-backups`.

### SMART disk monitoring (smartd)
`smartmontools` ships with PVE. `smartd` should be enabled and running.

```bash
# Check status and current config
systemctl status smartmontools
cat /etc/smartd.conf

# Full SMART data for a disk
smartctl -a /dev/sda

# One-shot config validation
smartd -C --no-fork -q onecheck
```

**Recommended `/etc/smartd.conf` for a SATA SSD:**
```
/dev/sda -a -I 194 -W 0,40,50 -s (S/../.././02|L/../../6/03) -m root -M exec /usr/share/smartmontools/smartd-runner
```
- `-a` — monitor everything (health, attrs, error log, selftest log)
- `-I 194` — suppress temperature attribute noise (see note below)
- `-W 0,40,50` — alert at ≥40°C warn / ≥50°C critical (actual temperature)
- `-s (S/.../02|L/.../6/03)` — short test daily 02:00, long test Saturday 03:00

**Important:** SMART attribute ID 194 reports a *normalized value* (0–100 scale), not actual °C. The raw temperature is in the `RAW_VALUE` column of `smartctl -a`. Without `-I 194`, smartd floods syslog with "temperature changed from 71 to 72" — these are normalized value jitter, not real thermal events. Use `-W` for actual temperature thresholds.

Add a logfile alert runner alongside the default mail runner:
```bash
cat > /etc/smartmontools/run.d/20logfile << 'EOF'
#!/bin/sh
printf "[%s] SMART ALERT: %s\nDevice: %s\nMessage: %s\n---\n" \
    "$(date "+%Y-%m-%d %H:%M:%S")" \
    "${SMARTD_SUBJECT}" "${SMARTD_DEVICE}" "${SMARTD_FULLMESSAGE}" \
    >> /var/log/smartd-alerts.log
EOF
chmod +x /etc/smartmontools/run.d/20logfile
```

## Presenting output

### Listing VMs/LXCs
When listing, combine `qm list` and `pct list` output into a single table:

```
| Type | VMID | Name          | Status  | CPU | Memory     |
|------|------|---------------|---------|-----|------------|
| VM   | 100  | ubuntu-server | running | 2   | 2048 MiB   |
| LXC  | 101  | debian-web    | stopped | 1   | 512 MiB    |
```

### Status overview
For a general status check, gather node status, VM/LXC list, and storage in one pass and present a dashboard-style summary.

### Config display
Show configs as key-value pairs, grouped logically (hardware, network, boot, etc.) rather than as raw output.

## Common workflows

### Pre-update snapshot
Always snapshot running VMs before applying host updates, then delete after confirming stability:
```bash
qm snapshot <vmid> pre-update-$(date +%Y%m%d) --description "Pre-update snapshot"
# ... apply updates ...
qm delsnapshot <vmid> pre-update-$(date +%Y%m%d)
```
LVM thin provisioning shows "Sum of all thin volume sizes exceeds pool size" warnings during snapshot creation — this is expected overcommit behaviour, not an error.

### Unattended security upgrades
Install and configure to auto-apply security patches only, keeping PVE packages manual:
```bash
apt install -y unattended-upgrades
```

`/etc/apt/apt.conf.d/50unattended-upgrades` — security-only, PVE packages blacklisted:
```
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
    "origin=Debian,codename=${distro_codename},label=Debian-Security";
};
Unattended-Upgrade::Package-Blacklist {
    "proxmox-"; "pve-"; "qemu-"; "lxc-pve";
    "corosync"; "libpve-"; "libproxmox-";
    "linux-"; "proxmox-kernel";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::SyslogEnable "true";
```

`/etc/apt/apt.conf.d/20auto-upgrades` — enable daily runs:
```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
```

### Container guest OS updates
Update packages inside all running containers with a single script:
```bash
for ctid in $(pct list | awk "NR>1 && \$2==\"running\" {print \$1}"); do
    if pct exec "$ctid" -- sh -c "command -v apk" &>/dev/null; then
        pct exec "$ctid" -- apk update && pct exec "$ctid" -- apk upgrade
    elif pct exec "$ctid" -- sh -c "command -v apt-get" &>/dev/null; then
        pct exec "$ctid" -- sh -c "DEBIAN_FRONTEND=noninteractive apt-get update -qq && apt-get upgrade -y"
    fi
done
```
Save as `/root/update-containers.sh` and cron weekly. Logs to `/var/log/ct-updates.log`.

### Quick status check
```bash
ssh root@<PROXMOX_IP> 'echo "=== NODE ===" && pvesh get /nodes/localhost/status --output-format json 2>/dev/null && echo "=== VMS ===" && qm list && echo "=== CTS ===" && pct list && echo "=== STORAGE ===" && pvesm status'
```

### Create a new LXC from template
1. List available templates: `pveam list <storage>` or `pveam available`
2. Download template if needed: `pveam download <storage> <template>`
3. Create: `pct create <ctid> <storage>:vztmpl/<template> --hostname <name> --memory <mb> --cores <n> --net0 name=eth0,bridge=vmbr0,ip=dhcp --rootfs <storage>:<size>`
4. Start: `pct start <ctid>`

### Create a new VM
1. Create: `qm create <vmid> --name <name> --memory <mb> --cores <n> --net0 virtio,bridge=vmbr0 --scsihw virtio-scsi-single`
2. Add disk: `qm set <vmid> --scsi0 <storage>:<size>`
3. Add ISO: `qm set <vmid> --cdrom <storage>:iso/<filename>`
4. Set boot order: `qm set <vmid> --boot order=scsi0`
5. Start: `qm start <vmid>`

## Error handling

If an SSH command fails, check:
1. Is the server reachable? (`ping <PROXMOX_IP>`)
2. Is the service running? (`systemctl status pvedaemon`)
3. Read the error message and explain what went wrong in plain language

Don't retry failed commands blindly. Diagnose first.
