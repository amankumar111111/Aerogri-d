# ADR-003: Why PostgreSQL?

- **Status:** Accepted
- **Context:** The system needs reliable storage for observations, signals, interpretations, and audit logs. Data integrity is critical — no observation should be lost.
- **Decision:** PostgreSQL 15+ as primary database. JSONB for flexible provider data storage. Append-only audit log table. Alembic for schema migrations.
- **Consequences:** + ACID transactions guarantee data integrity. + JSONB supports flexible provider data without schema changes. + Rich query capabilities for signal filtering.
