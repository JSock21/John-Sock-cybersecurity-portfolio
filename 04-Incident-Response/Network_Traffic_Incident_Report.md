# Network Traffic Incident Report – DNS Connectivity Issue

This document summarizes a network traffic incident analysis completed as part of the Google Cybersecurity Professional Certificate. The incident involved DNS connectivity failures identified through network traffic inspection and log analysis.

---

## Incident Summary
Users reported being unable to access a company website and received a “destination port unreachable” error. The issue was investigated using network traffic analysis to determine the cause and assess impact.

---

## Detection
- Multiple users reported website access failures
- Error message observed: destination port unreachable
- Network traffic analysis was initiated to identify the source of the issue

---

## Investigation and Analysis
- Network traffic analysis was performed using packet inspection tools
- ICMP responses indicated that UDP port 53 was unreachable
- Port 53 is associated with DNS services
- Repeated failed attempts to communicate with the DNS service were observed
- Findings suggested that DNS traffic was being blocked or the DNS server was unavailable

---

## Impact
- Users were unable to resolve the website’s domain name
- Website access was disrupted for multiple users
- Business operations relying on the website were affected

---

## Likely Cause
- DNS server outage, or
- Firewall or network rule blocking UDP port 53

---

## Response and Escalation
- Findings were documented clearly and concisely
- Incident details were escalated to senior security or network engineers
- Further remediation and root cause analysis were recommended

---

## How This Applies to a SOC Role
This incident demonstrates how SOC analysts investigate network-related alerts, analyze traffic to identify protocol and port issues, assess impact, and escalate incidents appropriately based on severity and business impact.
