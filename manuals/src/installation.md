# MagicBox Installation Guide

Goal: Portainer reachable from the LAN at **https://magicbox.local:9443/**.
`magicbox$` = on the Mini PC, `controller$` = on your workstation in this
repository. Replace `<...>` with your values.

## 1. Manual Steps (Mini PC)

### 1.1 Before you start

- [ ] Back up anything on the internal disk (the OS install erases it).
- [ ] Have: USB stick (4 GB+), Ethernet cable to the LAN, router admin access.
- [ ] Controller and Mini PC on the same subnet (not guest Wi-Fi).

### 1.2 Firmware (UEFI)

Setup key is usually `Del`, boot menu `F7` (check the boot screen).

- [ ] Apply a GMKtec firmware update for your model, if one exists.
- [ ] Boot mode: UEFI. Secure Boot: enabled.
- [ ] *Restore on AC Power Loss*: **Power On**.
- [ ] Save and exit.

### 1.3 Install Ubuntu Server 24.04 LTS

(Also supported: Ubuntu 26.04, Debian 12/13.)

- [ ] Download the ISO from `https://ubuntu.com/download/server`, verify its
      SHA-256, write it to the USB stick, boot from it.
- [ ] Network: wired, DHCP.
- [ ] Storage: entire internal disk, **no** passphrase encryption (it blocks
      unattended reboots).
- [ ] Server name: **`magicbox`**. Create your admin user (`<admin-user>`).
- [ ] Tick **Install OpenSSH server**. Featured snaps: **none**.
- [ ] Reboot, remove the USB stick, log in.

### 1.4 Update and collect facts

```text
magicbox$ sudo apt update && sudo apt full-upgrade -y && sudo reboot
magicbox$ cat /etc/os-release; uname -m     # supported OS, x86_64
magicbox$ ip -br link                       # LAN interface name
magicbox$ ip -br -4 addr; ip route          # address, subnet
magicbox$ ip link show <iface>              # MAC address
```

### 1.5 Stable address

- [ ] Router: DHCP reservation for the MAC address.
- [ ] `sudo reboot`, then `ip -br -4 addr` shows the reserved address.

### 1.6 SSH key

```text
controller$ ssh-keygen -t ed25519            # skip if you have a key
controller$ ssh-copy-id <admin-user>@<reserved-ip>
controller$ ssh <admin-user>@<reserved-ip> 'sudo -v && echo sudo-ok'
```

- [ ] Last command prints `sudo-ok`.
- [ ] Optional, after key login works (keep a session open while testing):

```text
magicbox$ echo 'PasswordAuthentication no' | sudo tee /etc/ssh/sshd_config.d/10-magicbox.conf
magicbox$ sudo sshd -t && sudo systemctl reload ssh
```

### 1.7 Values for the inventory

| Value | Source | Yours |
|-------|--------|-------|
| `ansible_host` | reserved IP | ______________ |
| `ansible_user` | admin user | ______________ |
| `magicbox_lan_interface` | `ip -br link` | ______________ |
| `magicbox_lan_cidr` | LAN subnet, e.g. 192.168.1.0/24 | ______________ |

## 2. Controller setup

- [ ] Install `uv` (`brew install uv`), `git`, `make`. Windows: use WSL2.

```text
controller$ make setup
controller$ make check
```

## 3. Configuration

```text
controller$ cp inventory/hosts.example.yml inventory/hosts.yml
controller$ uv run ansible-vault create inventory/group_vars/magicbox/vault.yml
```

- [ ] In `inventory/hosts.yml`: fill in the four values from 1.7.
- [ ] In `vault.yml`: `vault_portainer_admin_password: "<12+ chars>"`.
      Keep the vault password in your password manager.

```text
controller$ make secrets-check
controller$ uv run ansible magicbox -m ansible.builtin.ping    # expect "pong"
```

## 4. Deployment

```text
controller$ make deploy EXTRA="-K -e magicbox_confirm_destructive=true"   # first run
controller$ make deploy EXTRA="-K"                                        # later runs
```

`-K` asks for the sudo password. The first run needs the confirmation flag
because it enables the firewall. The CA certificate is saved to
`artifacts/magicbox-local-ca.crt`.

## 5. Verification

```text
controller$ make verify EXTRA="-K"
controller$ make idempotency VAULT_PASSWORD_FILE=<file> EXTRA="--become-password-file=<file>"
```

- [ ] `make verify` passes.
- [ ] `make idempotency` ends with "Idempotency check passed". Keep the
      password files outside the repo with mode 0600; delete them afterwards.
- [ ] From another LAN computer: `ping magicbox.local` works.
- [ ] Browser (CA trusted, section 6): `https://magicbox.local:9443/` opens with
      no warning; log in as `admin` with the vault password.
- [ ] `sudo reboot` on MagicBox: the page comes back, settings kept.
- [ ] `magicbox$ sudo ss -ltn | grep -E ':(9000|2375|2376) '` prints nothing.

## 6. TLS trust (each client, once)

- [ ] Check the fingerprints match:

```text
controller$ openssl x509 -in artifacts/magicbox-local-ca.crt -noout -fingerprint -sha256
magicbox$ sudo openssl x509 -in /opt/magicbox/portainer/certs/ca.crt -noout -fingerprint -sha256
```

- [ ] Copy `magicbox-local-ca.crt` to the client and install it:

| Client | Command / steps |
|--------|-----------------|
| macOS | `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain magicbox-local-ca.crt` |
| Windows (admin PowerShell) | `Import-Certificate -FilePath magicbox-local-ca.crt -CertStoreLocation Cert:\LocalMachine\Root` |
| Ubuntu/Debian | `sudo cp magicbox-local-ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates` |
| Firefox | Settings > Certificates > View Certificates > Authorities > Import > trust for websites |
| iOS | Install the profile, then General > About > Certificate Trust Settings > enable |
| Android | Settings > Security > Encryption & credentials > Install a certificate > CA certificate |

- [ ] Restart the browser.

The CA only covers `magicbox.local` and `magicbox`. The server certificate is
renewed automatically by any playbook run within 30 days of expiry.

### 6.1 If a client cannot resolve magicbox.local

mDNS works on macOS, iOS, Windows 10/11 and Linux with `libnss-mdns`. It does
not work across subnets or VLANs, or over VPN. Fallback: add
`<reserved-ip> magicbox.local` to the client's hosts file (`/etc/hosts` or
`C:\Windows\System32\drivers\etc\hosts`) or to the router's local DNS.

## 7. Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Unsupported OS" | Install Ubuntu Server 24.04 LTS |
| `magicbox_lan_interface` assertion | Use a name listed in the error |
| Admin password assertion | Create `vault.yml`; run with `--ask-vault-pass` |
| "ufw is inactive" | Add `-e magicbox_confirm_destructive=true` |
| Controller "outside" the LAN | Fix `magicbox_lan_cidr` or run from the LAN |
| Conflicting Docker packages | Check nothing uses them, then add the confirmation flag |
| Docker key fingerprint mismatch | Stop and verify Docker's key out of band |
| `magicbox.local` not resolving | `systemctl status avahi-daemon`; see 6.1 |
| Name became `magicbox-2.local` | Rename the other `magicbox` device; restart avahi-daemon |
| Certificate warning | Install the CA (section 6); restart the browser |
| Connection refused | `sudo docker ps -a`; `sudo docker logs portainer`; `sudo ufw status` |
| Vault password rejected at login | Portainer was already initialised: reset (8.3) |

## 8. Recovery

### 8.1 Repair drift

```text
controller$ make deploy EXTRA="-K"
```

### 8.2 Firewall lockout

At the console: `sudo ufw disable`, fix `magicbox_lan_cidr`, then redeploy
with `-e magicbox_confirm_destructive=true`.

### 8.3 Lost admin password

```text
magicbox$ sudo docker stop portainer
magicbox$ sudo docker run --rm -v portainer_data:/data portainer/helper-reset-password
magicbox$ sudo docker start portainer
```

### 8.4 Backup and restore

```text
magicbox$ sudo docker stop portainer
magicbox$ sudo tar -C / -czf /root/magicbox-backup-$(date +%F).tgz opt/magicbox var/lib/docker/volumes/portainer_data
magicbox$ sudo docker start portainer
```

The archive contains the CA key: store it encrypted, off the box. To restore,
reinstall (sections 1-4), stop Portainer, run `sudo tar -C / -xzf <archive>`,
and start Portainer.

### 8.5 Rotate the CA

Delete `/opt/magicbox/portainer/certs/` on MagicBox, run `make deploy`, and
install the new CA on every client. Remove the old CA from the clients.
