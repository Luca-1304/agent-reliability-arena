# Audit delivery pack verification contract

A release of the audit template pack must verify that:

- every file listed in `AUDIT_PACKAGE_INDEX.md` exists;
- the machine-readable status remains valid JSON;
- `external_client_audit_completed` remains false until evidence supports changing it;
- client-outcome and production-reliability claims remain disabled by default;
- no credential-shaped fields or private evidence are present;
- public service wording retains the scope and claims boundaries.
