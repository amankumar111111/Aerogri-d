# ADR-005: Why CQRS?

- **Status:** Accepted
- **Context:** The command centre requires fast reads (signal list, map, detail) while observation ingestion requires fast writes (submit, interpret, correlate). These workloads have different performance characteristics.
- **Decision:** Separate command (write) and query (read) paths at the application layer. Synchronous materialization for signal list. Event-driven projection for dashboard aggregates.
- **Consequences:** + Optimized read and write paths independently. + Signal list is always fast (pre-materialized). + Dashboard can be eventually consistent.
