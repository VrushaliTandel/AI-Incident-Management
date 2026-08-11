"""
Document loader: loads .txt, .pdf, .md, .docx files from knowledge_base directory.
"""
import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def load_documents(knowledge_base_path: str) -> List[Document]:
    """Load all supported documents from the knowledge base directory."""
    from langchain_community.document_loaders import (
        TextLoader,
        PyPDFLoader,
        UnstructuredMarkdownLoader,
        Docx2txtLoader,
    )

    docs: List[Document] = []
    kb_path = Path(knowledge_base_path)

    if not kb_path.exists():
        logger.warning("Knowledge base path does not exist: %s", kb_path)
        kb_path.mkdir(parents=True, exist_ok=True)
        _create_default_knowledge_base(kb_path)

    loaders_map = {
        ".txt": TextLoader,
        ".md": UnstructuredMarkdownLoader,
        ".pdf": PyPDFLoader,
        ".docx": Docx2txtLoader,
    }

    for file_path in kb_path.rglob("*"):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower()
        loader_cls = loaders_map.get(suffix)
        if not loader_cls:
            continue
        try:
            loader = loader_cls(str(file_path))
            file_docs = loader.load()
            # Tag each doc with source metadata
            for doc in file_docs:
                doc.metadata.setdefault("source", file_path.name)
            docs.extend(file_docs)
            logger.info("Loaded %d chunks from %s", len(file_docs), file_path.name)
        except Exception as exc:
            logger.error("Failed to load %s: %s", file_path, exc)

    if not docs:
        logger.warning("No documents loaded. Creating default knowledge base.")
        _create_default_knowledge_base(kb_path)
        # Retry once
        for file_path in kb_path.rglob("*.txt"):
            try:
                loader = TextLoader(str(file_path))
                docs.extend(loader.load())
            except Exception as exc:
                logger.error("Retry load failed: %s", exc)

    logger.info("Total documents loaded: %d", len(docs))
    return docs


def _create_default_knowledge_base(kb_path: Path) -> None:
    """Create default troubleshooting guides when no docs exist."""
    guides = {
        "vpn_troubleshooting.txt": """VPN Troubleshooting Guide

COMMON VPN ISSUES AND SOLUTIONS

Issue: VPN Not Connecting
Root Cause: Network connectivity, credential errors, or service outage.

L1 Resolution Steps:
1. Check your internet connection first - try opening a website.
2. Restart the VPN client application completely.
3. Verify your VPN credentials (username and password).
4. Check if the VPN service is experiencing an outage.
5. Try connecting to a different VPN server/region.
6. Disable and re-enable your network adapter.

L2 Resolution Steps:
1. Check Windows Firewall or antivirus blocking VPN ports (UDP 500, 4500, TCP 443).
2. Flush DNS cache: run 'ipconfig /flushdns' on Windows.
3. Reset TCP/IP stack: run 'netsh int ip reset'.
4. Reinstall the VPN client software.
5. Check if split tunneling is misconfigured.
6. Verify the VPN server certificate is valid and not expired.

L3 Resolution Steps:
1. Capture VPN logs and analyze authentication failures.
2. Check RADIUS/LDAP authentication server connectivity.
3. Verify PKI certificates for client-based authentication.
4. Review network routing tables for conflicts.
5. Check if ISP is blocking VPN protocols.
6. Consider switching VPN protocol (OpenVPN, IKEv2, WireGuard).

Authentication Error Troubleshooting:
- Verify Active Directory account is not locked
- Check if MFA token is synchronized
- Confirm group policy allows VPN access

Connection Timeout Troubleshooting:
- Check if UDP 500 and 4500 are open
- Try TCP 443 as fallback
- Check MTU settings (recommended: 1400)
""",
        "network_troubleshooting.txt": """Network Troubleshooting Guide

COMMON NETWORK ISSUES

Issue: No Internet Connectivity
L1 Steps:
1. Check all physical cable connections.
2. Restart modem and router (power cycle).
3. Run Windows Network Diagnostics.
4. Check if other devices on the same network have internet.
5. Try connecting via ethernet instead of WiFi.

L2 Steps:
1. Release and renew IP address: ipconfig /release and ipconfig /renew.
2. Reset Winsock: netsh winsock reset.
3. Check DHCP server is reachable and assigning addresses.
4. Verify DNS server settings (try 8.8.8.8).
5. Check for IP address conflicts.

Issue: Slow Network Performance
L1 Steps:
1. Run speed test to measure actual speeds.
2. Check for background downloads or updates.
3. Move closer to WiFi router.
4. Restart network equipment.

L2 Steps:
1. Check for network congestion using ping tests.
2. Update network adapter drivers.
3. Check for packet loss with extended ping.
4. Verify QoS settings on router.

Issue: WiFi Not Connecting
L1 Steps:
1. Forget and reconnect to the WiFi network.
2. Restart WiFi adapter.
3. Check WiFi password is correct.
4. Move closer to the access point.

L2 Steps:
1. Check if SSID is being broadcast.
2. Verify security settings (WPA2 vs WPA3 compatibility).
3. Check MAC address filtering on router.
4. Update WiFi driver.
""",
        "email_troubleshooting.txt": """Email Troubleshooting Guide

COMMON EMAIL ISSUES

Issue: Cannot Send or Receive Emails
L1 Steps:
1. Check internet connectivity.
2. Verify email account credentials.
3. Check spam/junk folder for missing emails.
4. Restart email client.
5. Check if email service is experiencing outage.

L2 Steps:
1. Verify SMTP/IMAP/POP3 server settings.
2. Check if port 25, 465, 587 (SMTP) or 993 (IMAP) are open.
3. Clear email client cache.
4. Reconfigure email account from scratch.
5. Check email storage quota (mailbox full).

L3 Steps:
1. Review mail server logs for bounce codes.
2. Check SPF, DKIM, DMARC records for email authentication.
3. Verify email routing rules and forwarding settings.
4. Check if email domain is blacklisted.

Issue: Outlook Not Opening
L1 Steps:
1. Restart Outlook.
2. Run Outlook in safe mode: outlook.exe /safe.
3. Disable add-ins.
4. Repair Office installation.

L2 Steps:
1. Rebuild Outlook profile.
2. Run ScanPST.exe to repair .pst file.
3. Check Windows Event Viewer for errors.
4. Reinstall Office.
""",
        "authentication_troubleshooting.txt": """Authentication & Login Troubleshooting Guide

COMMON AUTHENTICATION ISSUES

Issue: Cannot Login / Account Locked
L1 Steps:
1. Verify you are using the correct username and password.
2. Check CAPS LOCK is not enabled.
3. Try password reset if available.
4. Check if account is locked after too many attempts.
5. Clear browser cache and cookies.

L2 Steps:
1. Check Active Directory for account lockout status.
2. Verify account expiry date has not passed.
3. Check if account is disabled by administrator.
4. Review group policy for lockout threshold.
5. Check for Kerberos ticket issues.

Issue: MFA Not Working
L1 Steps:
1. Verify device time is synchronized (NTP).
2. Try generating a new OTP code.
3. Check if backup codes are available.
4. Contact IT to reset MFA device.

L2 Steps:
1. Re-enroll MFA device.
2. Check RADIUS server connectivity.
3. Verify MFA policy is correctly configured.
4. Review authentication logs for error codes.

Issue: SSO Not Working
L1 Steps:
1. Clear browser cookies and cache.
2. Try different browser.
3. Check if SSO provider is accessible.

L2 Steps:
1. Verify SAML/OAuth configuration.
2. Check identity provider metadata.
3. Review SSO error logs.
4. Verify service provider ACS URL.
""",
        "server_troubleshooting.txt": """Server & Infrastructure Troubleshooting Guide

COMMON SERVER ISSUES

Issue: Server Not Responding
L1 Steps:
1. Ping the server to check basic connectivity.
2. Check if server is powered on.
3. Verify network connection to server.
4. Check server console/IPMI.
5. Check if other users can reach the server.

L2 Steps:
1. Check CPU, memory, and disk usage.
2. Review system logs for errors.
3. Check if critical services are running.
4. Verify firewall rules allow the traffic.
5. Check if server is in maintenance mode.

L3 Steps:
1. Analyze core dumps and crash reports.
2. Check hardware health (RAID, PSU, temperature).
3. Review kernel logs for hardware errors.
4. Consider failover to backup server.
5. Engage vendor support for hardware issues.

Issue: High CPU Usage
L1 Steps:
1. Identify high CPU processes using Task Manager / top.
2. Restart the problematic service.
3. Check for runaway processes.

L2 Steps:
1. Profile application for CPU bottlenecks.
2. Check for malware or crypto-mining.
3. Review scheduled tasks running at peak time.
4. Scale server resources.

Issue: Disk Full
L1 Steps:
1. Check disk usage with df -h (Linux) or Disk Management (Windows).
2. Clear temporary files.
3. Empty recycle bin.
4. Check for large log files.

L2 Steps:
1. Identify largest directories and files.
2. Archive or delete old backups.
3. Configure log rotation.
4. Add additional disk capacity.
""",
        "router_troubleshooting.txt": """Router & Switch Troubleshooting Guide

COMMON ROUTER ISSUES

Issue: Router Not Working
L1 Steps:
1. Check power LED is on.
2. Power cycle the router (unplug 30 seconds).
3. Check all cable connections.
4. Try factory reset as last resort.
5. Check router admin page for errors.

L2 Steps:
1. Check ISP connection light on router.
2. Connect directly to modem to isolate router issue.
3. Update router firmware.
4. Check DHCP pool is not exhausted.
5. Review router logs for WAN errors.

L3 Steps:
1. Analyze routing table for incorrect entries.
2. Check BGP/OSPF routing protocol issues.
3. Review spanning tree configuration.
4. Check for routing loops.
5. Engage ISP for upstream issues.

Issue: Cannot Access Router Admin Page
L1 Steps:
1. Verify you are connected to the router's network.
2. Try 192.168.1.1 or 192.168.0.1.
3. Check default gateway: ipconfig /all.
4. Clear browser cache.

L2 Steps:
1. Try from different device.
2. Disable browser extensions.
3. Try different browser.
4. Try HTTPS if HTTP fails.
""",
        "camera_troubleshooting.txt": """Camera & Video Conferencing Troubleshooting Guide

COMMON CAMERA ISSUES

Issue: Camera Not Working
L1 Steps:
1. Check if camera is physically connected.
2. Restart the application using the camera.
3. Check camera privacy cover is open.
4. Test camera in a different application (e.g., Camera app).
5. Check if camera is selected as default device.

L2 Steps:
1. Update camera drivers in Device Manager.
2. Check if another application is using the camera (exclusive access).
3. Roll back driver to previous version.
4. Uninstall and reinstall camera drivers.
5. Check Windows Camera privacy settings.

L3 Steps:
1. Check Device Manager for error codes.
2. Test camera on different USB port.
3. Replace USB cable for external cameras.
4. Test on different computer.
5. RMA defective hardware.

Issue: Poor Video Quality
L1 Steps:
1. Check internet bandwidth (need minimum 2Mbps upload).
2. Close other bandwidth-intensive applications.
3. Move closer to WiFi router.
4. Lower video quality settings in the app.

L2 Steps:
1. Update camera firmware/drivers.
2. Adjust camera resolution settings.
3. Check lighting conditions.
4. Reduce background processes using CPU.
""",
    }

    for filename, content in guides.items():
        file_path = kb_path / filename
        file_path.write_text(content, encoding="utf-8")
        logger.info("Created default knowledge base file: %s", filename)
