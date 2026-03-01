
# Category: HARDWARE

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