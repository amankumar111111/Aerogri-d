# ADR-004: Why Cloud Run?

- **Status:** Accepted
- **Context:** The system needs to be deployed for demonstration and potential production use. The team needs fast iteration without infrastructure management overhead.
- **Decision:** Google Cloud Run as the deployment target. Single container service (monolith) for prototype. Auto-scaling 0–10 instances.
- **Consequences:** + Zero infrastructure management. + Auto-scale to zero (cost-effective). + Fast deployment from container.
