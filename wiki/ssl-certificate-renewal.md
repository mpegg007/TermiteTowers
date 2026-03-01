<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/ssl-certificate-renewal.md:121 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: c3119189616421d7a4a1a498a526f66ad7c97d99 %
  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
  %ccm_git_commit_count: 121 %
  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: cleanup %
  %ccm_git_modify_date: 2025-11-30 12:28:03 %
  %ccm_git_file_last_modified: 2025-11-30 12:28:03 %
  %ccm_git_file_name: ssl-certificate-renewal.md %
  %ccm_git_path: wiki/ssl-certificate-renewal.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 4636 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: november changes % -->
# SSL Certificate Renewal Guide - TermiteTowers

## Current Certificates

### Wildcard Certificate (Primary)
- **Domain**: `*.termitetowers.ca` and `termitetowers.ca`
- **Certificate Path**: `/etc/letsencrypt/live/termitetowers.ca/fullchain.pem`
- **Private Key Path**: `/etc/letsencrypt/live/termitetowers.ca/privkey.pem`
- **Type**: ECDSA
- **Valid For**: 90 days (Let's Encrypt standard)

### Chat Subdomain
- **Domain**: `chat.termitetowers.ca`
- **Certificate Path**: `/etc/letsencrypt/live/chat.termitetowers.ca/fullchain.pem`
- **Private Key Path**: `/etc/letsencrypt/live/chat.termitetowers.ca/privkey.pem`

## Quick Renewal Commands

### Check Certificate Status
```bash
sudo certbot certificates
```

### Renew All Certificates (Dry Run - Test First)
```bash
sudo certbot renew --dry-run
```

### Renew All Certificates (Production)
```bash
sudo certbot renew
```

### Force Renew Specific Certificate
```bash
# Wildcard certificate
sudo certbot renew --cert-name termitetowers.ca --force-renewal

# Chat subdomain
sudo certbot renew --cert-name chat.termitetowers.ca --force-renewal
```

### Reload Nginx After Renewal
```bash
sudo systemctl reload nginx
```

## Automated Renewal

### Check Certbot Timer Status
```bash
sudo systemctl status certbot.timer
sudo systemctl list-timers certbot.timer
```

### Enable Automatic Renewal (if not already enabled)
```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

### Manual Cron Job (Alternative to systemd timer)
If you prefer cron over systemd timer:
```bash
sudo crontab -e
```

Add this line:
```
0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

## Troubleshooting

### Certificate Expired - Force Renewal
If certificate is already expired and normal renewal fails:
```bash
sudo certbot renew --cert-name termitetowers.ca --force-renewal
```

### DNS Challenge for Wildcard Certificates
Wildcard certificates (`*.termitetowers.ca`) require DNS-01 challenge. If renewal fails:

1. **Manual DNS Challenge**:
```bash
sudo certbot certonly --manual --preferred-challenges dns -d termitetowers.ca -d "*.termitetowers.ca"
```

2. Follow the prompts and add the TXT record to your DNS provider
3. Verify DNS propagation:
```bash
dig -t TXT _acme-challenge.termitetowers.ca
```

### HTTP Challenge for Regular Domains
For non-wildcard domains:
```bash
sudo certbot certonly --webroot -w /var/www/html -d chat.termitetowers.ca
```

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
