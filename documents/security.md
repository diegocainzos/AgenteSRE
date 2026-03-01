# Category: SECURITY

## 5. SSH Brute Force Attack Detected
**Zabbix Error ID:** `SEC-SSH-BRUTE-010`

**Description:** 
A high volume of failed SSH login attempts (Threshold: >50 in 60 seconds) detected from a single source IP.

**Step-by-step Solution:**
1. **Identify Source:** Check `/var/log/auth.log` (Ubuntu/Debian) or `/var/log/secure` (RHEL) to find the offending IP.
2. **Verify Fail2Ban:** Ensure `fail2ban` service is active: `systemctl status fail2ban`.
3. **Manual Block:** If Fail2Ban didn't catch it, block manually: `iptables -A INPUT -s [Attacker_IP] -j DROP`.
4. **Review Access:** Check if any successful logins occurred from that IP: `last | grep [Attacker_IP]`.
5. **Update Policy:** Ensure `PasswordAuthentication no` is set in `/etc/ssh/sshd_config`.

---

## 6. SSL/TLS Certificate Expiry Warning
**Zabbix Error ID:** `SEC-CERT-EXP-003`

**Description:** 
The SSL certificate for a production endpoint will expire in less than 7 days. This indicates a failure in the automated renewal (Certbot/Let's Encrypt or Vault).

**Step-by-step Solution:**
1. **Check Expiry:** Run `openssl s_client -connect [Domain]:443 | openssl x509 -noout -dates`.
2. **Check Renewal Logs:** Inspect Certbot logs: `/var/log/letsencrypt/letsencrypt.log`.
3. **Manual Renewal:** Attempt manual trigger: `certbot renew --dry-run`.
4. **Fix Validation Failure:** Ensure the `.well-known/acme-challenge` directory is reachable via Nginx/Apache.
5. **Reload Webserver:** After renewal, reload the service: `systemctl reload nginx`.

---

## 7. Anomalous API Token Usage (Rate Limit Exceeded)
**Zabbix Error ID:** `SEC-API-ANOM-007`

**Description:** 
A specific API key is performing 500% more requests than the historical baseline, suggesting a token leak or a compromised service account.

**Step-by-step Solution:**
1. **Identify Token ID:** Extract the `user_id` or `token_id` from the application access logs.
2. **Audit Source:** Check the source IP of the requests. If it’s outside our VPC, treat as a leak.
3. **Revoke Token:** Immediately disable the token in the database or admin dashboard.
4. **Notify Owner:** Contact the developer/team responsible for that service account.
5. **Rotate Credentials:** Generate a new secret and update the CI/CD pipeline or Secrets Manager (Vault/AWS Secrets Manager).

---

## 8. Directory Traversal Attempt Detected (WAF Alert)
**Zabbix Error ID:** `SEC-WAF-TRAV-012`

**Description:** 
The Web Application Firewall (WAF) has blocked multiple requests containing `../` or `/etc/passwd` patterns.

**Step-by-step Solution:**
1. **Analyze WAF Logs:** Identify if the attacks are targeted or generic bot noise.
2. **Sanitize Inputs:** Review the code responsible for the targeted endpoint to ensure input sanitization is implemented.
3. **Verify File Permissions:** Ensure the webserver user (`www-data`) has no read access to sensitive system files.
4. **Update ModSecurity Rules:** If the WAF is false-positive, tune the rule. If valid, move the IP to a temporary blacklist (6-24 hours).
5. **Patch System:** Ensure the application framework (Laravel/BookStack) is on the latest security patch.

---
