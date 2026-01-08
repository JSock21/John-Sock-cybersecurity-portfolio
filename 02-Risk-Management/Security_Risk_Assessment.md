# Security Risk Assessment – Network Hardening Recommendations

This document summarizes a security risk assessment completed following a major data breach at a social media organization. The breach compromised customers’ personal information (e.g., names and addresses). The purpose of this assessment is to identify key vulnerabilities and recommend repeatable network hardening practices to reduce the likelihood of future attacks.

---

## Key Vulnerabilities Identified
- Employees share passwords
- Database administrator password is set to the default
- Firewalls lack inbound and outbound traffic filtering rules
- Multifactor authentication (MFA) is not enabled

---

## Risk Summary
These issues significantly increase the risk of credential compromise, unauthorized administrative access, and data exposure. If these vulnerabilities remain unaddressed, the organization is likely to experience additional security incidents, including account takeover, lateral movement, and recurring data breaches.

---

## Recommended Hardening Actions

### 1) Credential Hygiene and Access Accountability
- Prohibit password sharing and require unique user credentials
- Enforce strong password requirements (length, complexity, reuse restrictions)
- Encourage the use of an approved password manager to reduce insecure credential storage

### 2) Secure Administrative Access
- Replace default database administrator credentials immediately
- Restrict administrative access to authorized personnel only
- Apply least privilege to reduce unnecessary access to sensitive systems

### 3) Firewall Rule Management and Traffic Filtering
- Implement deny-by-default firewall rules and allow only required services
- Define inbound and outbound rules based on approved business needs
- Block unused ports and protocols to reduce the attack surface
- Review firewall rules on a regular cadence to ensure continued effectiveness

### 4) Multifactor Authentication (MFA)
- Require MFA for all administrative accounts and access to sensitive systems
- Extend MFA to remote access and critical internal applications
- Use MFA to reduce the risk of compromise even if passwords are stolen

---

## Expected Security Impact
Implementing these controls will reduce the organization’s attack surface, improve access control, and significantly lower the risk of credential-based compromise and unauthorized access. These measures strengthen the organization’s security posture and help protect sensitive customer information.

---

## How This Applies to a SOC Role
Risk assessments and hardening recommendations help SOC analysts understand organizational risk, identify high-impact control gaps, and support preventive measures that reduce future incidents and improve overall security posture.
