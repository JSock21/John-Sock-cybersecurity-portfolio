# ICMP DDoS Incident Response – NIST CSF Analysis

This document summarizes a security incident involving a distributed denial-of-service (DDoS) attack caused by a flood of incoming ICMP packets. The incident response is documented using the NIST Cybersecurity Framework (CSF).

---

## Incident Summary
The organization experienced a sudden outage where all network services stopped responding. Investigation determined the disruption was caused by a distributed denial-of-service (DDoS) attack using an ICMP flood, overwhelming network resources and preventing legitimate traffic from being processed.

---

## NIST CSF Incident Analysis

### Identify
- A malicious actor launched an ICMP flood attack targeting the organization
- The attack affected the entire internal network
- Critical network resources required immediate protection and restoration

### Protect
- Firewall rules were updated to rate-limit incoming ICMP traffic
- An IDS/IPS solution was implemented to filter ICMP packets with suspicious characteristics

### Detect
- Source IP address verification was enabled on the firewall to identify spoofed IP addresses
- Network monitoring tools were configured to detect abnormal traffic patterns and spikes in ICMP traffic

### Respond
- Affected systems were isolated to prevent further network disruption
- Non-critical network services were temporarily stopped
- Critical systems and services were prioritized for restoration
- Network logs were analyzed to identify suspicious activity
- Incident details were documented and escalated to management and relevant stakeholders

### Recover
- Critical network services were restored first to resume essential operations
- ICMP flood traffic was blocked at the firewall
- Once traffic normalized, non-critical systems were brought back online
- Recovery procedures were reviewed to improve future response effectiveness

---

## How This Applies to a SOC Role
This incident demonstrates how SOC analysts detect and respond to DDoS attacks, analyze network traffic patterns, apply firewall and IDS controls, and follow a structured response process using the NIST Cybersecurity Framework.
