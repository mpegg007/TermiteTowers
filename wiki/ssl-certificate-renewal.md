<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/ssl-certificate-renewal.md:147 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 7e3f17098634f1f5a913092dd0278e1cf64e22e4 %
  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
  %ccm_git_commit_count: 147 %
  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: june bulk update %
  %ccm_git_modify_date: 2026-06-10 17:10:33 %
  %ccm_git_file_last_modified: 2026-06-10 17:10:33 %
  %ccm_git_file_name: ssl-certificate-renewal.md %
  %ccm_git_path: wiki/ssl-certificate-renewal.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 5075 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: 2025-11-30 mpegg  cleanup  % -->
<!-- %git_commit_history: november changes % -->
# SSL Certificate Renewal Guide - TermiteTowers

## Current Certificates

### Wildcard Certificate (Primary)
- **Domain**: `*.termitetowers.ca` and `termitetowers.ca`
- **Cert Name**: `termitetowers.ca-0001`
- **Certificate Path**: `/etc/letsencrypt/live/termitetowers.ca-0001/fullchain.pem`
- **Private Key Path**: `/etc/letsencrypt/live/termitetowers.ca-0001/privkey.pem`
- **Type**: ECDSA
- **Valid For**: 90 days (Let's Encrypt standard)
- **Last Renewed**: 2026-05-16, expires 2026-08-14

### Chat Subdomain
- **Domain**: `chat.termitetowers.ca`
- **Certificate Path**: `/etc/letsencrypt/live/chat.termitetowers.ca/fullchain.pem`
- **Private Key Path**: `/etc/letsencrypt/live/chat.termitetowers.ca/privkey.pem`
- **Last Renewed**: 2026-05-16, expires 2026-08-14

## Automation Setup (Current)

Renewal is fully automated via GoDaddy API DNS hooks + snap certbot timer.

- **Certbot**: snap (`certbot-eff`, v5.6+)
- **Auth hook**: `infra/certbot/godaddy-auth-hook.sh`
- **Cleanup hook**: `infra/certbot/godaddy-cleanup-hook.sh`
- **Credentials**: `/etc/letsencrypt/godaddy.env` (chmod 600, not in repo)
- **Timer**: `snap.certbot.renew.timer` (runs twice daily)

Check timer status:
```bash
sudo systemctl status snap.certbot.renew.timer
```

The hooks are stored in the renewal config — `sudo certbot renew` will use them automatically.

## Quick Renewal Commands

### Check Certificate Status
```bash
sudo certbot certificates
```

### Renew All (automatic — hooks fire via GoDaddy API)
```bash
sudo certbot renew --dry-run   # test first
sudo certbot renew
```

### Force Renew Specific Certificate
```bash
cd /home/mpegg-adm/source/TermiteTowers

# Wildcard
sudo certbot certonly \
  --manual --preferred-challenges dns \
  --manual-auth-hook "$(pwd)/infra/certbot/godaddy-auth-hook.sh" \
  --manual-cleanup-hook "$(pwd)/infra/certbot/godaddy-cleanup-hook.sh" \
  -d termitetowers.ca -d "*.termitetowers.ca" \
  --cert-name termitetowers.ca-0001 --force-renewal

# Chat subdomain
sudo certbot certonly \
  --manual --preferred-challenges dns \
  --manual-auth-hook "$(pwd)/infra/certbot/godaddy-auth-hook.sh" \
  --manual-cleanup-hook "$(pwd)/infra/certbot/godaddy-cleanup-hook.sh" \
  -d chat.termitetowers.ca \
  --cert-name chat.termitetowers.ca --force-renewal
```

### Reload Nginx After Renewal
```bash
sudo systemctl reload nginx
```

## Troubleshooting

### Certificate Expired - Force Renewal
Use the force renew commands above.

### Hook Fails / TXT Record Issue
- The auth hook fetches existing TXT records and appends — required for wildcard+apex (two hooks fire, one record name)
- Check GoDaddy API credentials are in `/etc/letsencrypt/godaddy.env`
- Verify DNS propagation: `dig -t TXT _acme-challenge.termitetowers.ca @1.1.1.1`
- Increase `sleep` in auth hook if propagation is slow (currently 90s)

### Check Nginx Configuration
```bash
sudo nginx -t
```

### View Certbot Logs
```bash
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

## Certificate Validation

### Check Expiration Date
```bash
# From file
sudo openssl x509 -in /etc/letsencrypt/live/termitetowers.ca/fullchain.pem -noout -dates

# From live site
echo | openssl s_client -servername termitetowers.ca -connect termitetowers.ca:443 2>/dev/null | openssl x509 -noout -dates
```

### Test SSL Configuration
```bash
# Test local nginx SSL config
curl -I https://termitetowers.ca

# Detailed SSL test
openssl s_client -connect termitetowers.ca:443 -servername termitetowers.ca
```

## Services Using These Certificates

The following nginx sites use the wildcard certificate:
- vault.termitetowers.ca
- eso.termitetowers.ca
- sops.termitetowers.ca
- hal.termitetowers.ca
- wiki.termitetowers.ca
- pihole.termitetowers.ca
- kuma.termitetowers.ca
- packages.termitetowers.ca
- And all other `*.termitetowers.ca` subdomains

## Post-Renewal Checklist

1. ✅ Verify certificate renewed: `sudo certbot certificates`
2. ✅ Check expiration date is in the future
3. ✅ Reload nginx: `sudo systemctl reload nginx`
4. ✅ Test a few sites in browser (check for SSL errors)
5. ✅ Verify no certificate warnings in browser
6. ✅ Check nginx logs for errors: `sudo tail /var/log/nginx/error.log`

## Important Notes

- **Let's Encrypt certificates expire in 90 days**
- **Recommended renewal time: 30 days before expiration**
- **Certbot auto-renewal should run twice daily via systemd timer**
- **Wildcard certs require DNS-01 challenge** (manual TXT record update)
- **Regular subdomains can use HTTP-01 challenge** (automatic via webroot)

## Emergency Contact

If renewal fails and you need help:
1. Check `/var/log/letsencrypt/letsencrypt.log`
2. Verify DNS is pointing to correct server
3. Ensure port 443 and 80 are open
4. Check nginx is running: `sudo systemctl status nginx`
5. For wildcard cert issues, verify you have DNS provider access

## References

- Let's Encrypt: https://letsencrypt.org/
- Certbot Documentation: https://certbot.eff.org/
- DNS Challenge Guide: https://certbot.eff.org/docs/using.html#dns-plugins
