# NETWORKING

## 1. BGP Session Down: Neighbor Peer Loss
**Zabbix Error ID:** `NET-BGP-ERR-001`

**Description:** 
The BGP session with a primary upstream provider or internal core router has transitioned from `Established` to `Idle` or `Active`. This usually indicates a physical link failure, a mismatch in TTL, or a prefix limit violation.

**Step-by-step Solution:**
1. **Verify State:** Log into the router and run `show ip bgp neighbors [Neighbor_IP]` to confirm the current state and "Last Reset" reason.
2. **Check Layer 1/2:** Ping the neighbor interface to ensure local connectivity. If pings fail, check the physical interface status (`show interface`).
3. **Verify Prefix Limits:** Check if the peer sent more prefixes than the configured `maximum-prefix` limit. If exceeded, clear the session: `clear ip bgp [Neighbor_IP]`.
4. **Log Review:** Check syslog for "BGP-3-NOTIFICATION" errors indicating hold-time expiration or MD5 password mismatches.
5. **Escalate:** If local config is correct, contact the ISP/Provider NOC with the circuit ID.

---

## 2. VLAN Tagging Mismatch (Trunk Port Configuration)
**Zabbix Error ID:** `NET-VLAN-ERR-042`

**Description:** 
Packet loss or total connectivity failure between Hypervisors and Top-of-Rack (ToR) switches. This occurs when a new VLAN is added to the application stack but is not allowed on the physical trunk port.

**Step-by-step Solution:**
1. **Identify Affected Nodes:** Use Zabbix triggers to identify which specific hosts are unreachable on the management or data plane.
2. **Check Switch Port:** Log into the ToR switch and run `show interfaces trunk`.
3. **Verify VLAN Database:** Ensure the VLAN ID exists in the switch database: `show vlan brief`.
4. **Update Trunk:** If missing, add the VLAN to the allowed list: 
   `conf t` -> `interface [Int_ID]` -> `switchport trunk allowed vlan add [VLAN_ID]`.
5. **Verify Host-Side:** On the Linux host, ensure the sub-interface (e.g., `eth0.100`) is UP and tagged correctly via `ip addr show`.

---

## 3. Anycast Routing Latency Spike
**Zabbix Error ID:** `NET-LAT-ANY-009`

**Description:** 
Internal Anycast VIPs are experiencing >50ms latency. This typically indicates a "Routing Flap" where traffic is being routed to a geographically distant PoP instead of the local node.

**Step-by-step Solution:**
1. **Trace Route:** Run `mtr -rn [VIP_Address]` from the affected client zone to see the path.
2. **Identify Node:** Check which node is currently "winning" the BGP advertisement for that VIP.
3. **Verify Health Check:** Check if the local health-checking daemon (e.g., Bird or ExaBGP) has withdrawn the route due to a local service failure.
4. **Force Re-convergence:** Restart the BGP daemon on the local node to re-announce the route with a lower MED or shorter AS-Path.
5. **Review Quagga/Bird Logs:** Look for "Route flap dampened" messages.

---

## 4. MTU Mismatch (ICMP Blackhole)
**Zabbix Error ID:** `NET-MTU-SIZE-005`

**Description:** 
Standard packets pass, but large packets (HTTPS/DB queries) fail or hang. This happens when a GRE tunnel or VXLAN adds overhead, exceeding the 1500-byte MTU without proper fragmentation.

**Step-by-step Solution:**
1. **Path MTU Discovery Test:** Run `ping -M do -s 1472 [Destination_IP]`. If it fails, decrease the size until it passes to find the ceiling.
2. **Check Interface Config:** Inspect interfaces on all hops: `ip link show`.
3. **Adjust MSS Clamping:** If using IPTables, force MSS clamping: 
   `iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu`.
4. **Update Config:** Set `mtu 1450` (or appropriate value) in the persistent net-plan or interface config file.
5. **Restart Service:** Apply changes with `sysctl -p`.

---

# SECURITY

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

# HARDWARE

## 9. SSD S.M.A.R.T. Failure Prediction
**Zabbix Error ID:** `HW-DISK-SMART-002`

**Description:** 
The `smartd` daemon reports that a physical SSD (typically `/dev/sda` or `/dev/nvme0n1`) has exceeded its wear-level threshold or has an increasing "Reallocated Sector Count."

**Step-by-step Solution:**
1. **Run Diagnostic:** Execute `smartctl -a /dev/[device]` to see the specific failure attribute.
2. **Verify RAID Status:** If the drive is part of a RAID, check its health: `mdadm --detail /var/md0` or use the hardware controller utility (e.g., `hpacucli` or `perccli`).
3. **Trigger Backup:** Ensure the latest backup/snapshot is successful before proceeding.
4. **Set to Faulty:** If in a RAID, fail the drive manually: `mdadm --manage /dev/md0 --fail /dev/[device]`.
5. **Physical Replacement:** Schedule a DC tech to replace the drive and monitor the rebuild process.

---

## 10. Chassis Fan RPM Below Threshold
**Zabbix Error ID:** `HW-FAN-SPEED-008`

**Description:** 
Fan sensor `Fan_4_CPU_Exhaust` is reporting <500 RPM. This can lead to thermal throttling and hardware damage.

**Step-by-step Solution:**
1. **Check Temperature:** Run `sensors` to see if CPU temperatures are rising above 80°C.
2. **Visual Inspection:** (If remote) Check IPMI/iDRAC/ILO logs for "Fan redundancy lost" or "Mechanical failure."
3. **Increase Duty Cycle:** Try to force fan speeds to 100% via IPMI to see if the fan clears a dust obstruction.
4. **Schedule Maintenance:** If RPM remains low, the fan bearing has likely failed. Order a replacement part.
5. **Workload Migration:** Drain the node of all containers/VMs to reduce heat until the hardware is repaired.

---

## 11. ECC Memory: Correctable Error Rate High
**Zabbix Error ID:** `HW-MEM-ECC-004`

**Description:** 
The kernel (EDAC) is reporting a high frequency of single-bit flips on a specific DIMM slot. While corrected by the hardware, this usually precedes a multi-bit uncorrectable failure.

**Step-by-step Solution:**
1. **Locate DIMM:** Check `dmesg | grep -i edac` or `ipmitool sel list` to identify the physical slot (e.g., DIMM_A1).
2. **Clear Logs:** Clear the IPMI log to see if the error count continues to increment in real-time.
3. **Schedule Reseat:** Sometimes thermal expansion causes loose seating. Schedule a window to shut down and reseat the RAM.
4. **Replace DIMM:** If errors persist after reseating, replace the DIMM module entirely.
5. **Memtest:** Run a `memtest86+` cycle if the server is off-production to verify the fix.

---

## 12. RAID Controller Battery (BBU) Failure
**Zabbix Error ID:** `HW-RAID-BBU-001`

**Description:** 
The Backup Battery Unit (BBU) or SuperCap for the RAID controller has failed or is in a "Learn Cycle." This causes the controller to switch from `Write-Back` to `Write-Through` mode, severely degrading disk I/O performance.

**Step-by-step Solution:**
1. **Check BBU Status:** Use the controller utility: `perccli /c0/bbu show` (for Dell) or `ssacli ctrl slot=0 show status` (for HP).
2. **Determine Mode:** If it is a "Learn Cycle," wait 24 hours for it to complete. Performance will return automatically.
3. **Check Voltage:** If the status is "Failed" or "Voltage Low," the battery must be replaced.
4. **Performance Mitigation:** If performance is critical and the risk is acceptable (UPS is stable), manually force `Write-Back` mode (Warning: Data loss risk on power failure).
5. **Physical Replace:** Order a replacement BBU and schedule a technician.