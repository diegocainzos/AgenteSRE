
# Category: NETWORKING

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