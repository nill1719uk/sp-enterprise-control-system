# S.P. Enterprise Cloud Control System v0.1

## Architecture
- Streamlit: web application
- Supabase PostgreSQL: cloud database
- Supabase Auth: individual employee logins
- Database UNIQUE constraint: duplicate protection
- Cloud deployment: Streamlit Community Cloud or equivalent

## Phase 1 included
- Login
- Stock item master
- Stock IN/OUT entry
- Date, quantity, invoice/challan/gate-pass, party/destination, vehicle and handler
- Current stock balance
- Negative-stock blocking
- Exact duplicate blocking at database level
- Movement register

## Critical design decision
Do not rely only on a Python duplicate check. Two employees may submit the same record at almost the same time. The PostgreSQL UNIQUE constraint on duplicate_fingerprint is the final safeguard.

## Duplicate policy
The first version blocks exact duplicates. It should NOT automatically block every similar transaction, because two legitimate deliveries can have the same item, quantity and date. In the production version, document/reference numbers and gate-pass numbers should be mandatory where applicable.

## Recommended roles
admin = full control
office = accounts + stock
factory = stock entry/view
viewer = read-only

Each employee should have an individual login. Never use one shared password.

## Next phases
1. Accounts registers
2. Customer/supplier balances
3. Bank/cash reconciliation
4. Loans/EMIs
5. GST tracker
6. Audit log and role permissions
7. Document repository
8. Stock reconciliation and suspicious-movement alerts
