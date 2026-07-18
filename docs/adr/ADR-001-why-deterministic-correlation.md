# ADR-001: Why Deterministic Correlation?

- **Status:** Accepted
- **Context:** Environmental signals affect municipal resource allocation. Decisions must be auditable, reproducible, and explainable to non-technical stakeholders. AI models are non-deterministic and difficult to explain.
- **Decision:** The correlation engine is entirely deterministic — no AI models, no randomness, no learned parameters. Given the same inputs, it produces the same outputs.
- **Consequences:** + Testable, auditable, transparent. + Easy to explain to municipal teams. − Cannot learn from historical patterns. − Requires manual threshold tuning (addressed by calibration dashboard).
