# ADR-002: Why Gemini Only Interprets?

- **Status:** Accepted
- **Context:** Gemini is a powerful multimodal model that could theoretically make classification decisions. However, AI classification decisions are difficult to explain, reproduce, and audit — especially for government stakeholders.
- **Decision:** Gemini is used exclusively for evidence interpretation (what is visible in the image/audio/text). The deterministic correlation engine makes all operational decisions.
- **Consequences:** + Clean separation of AI and domain logic. + Every decision is explainable. + Gemini can be swapped without affecting classification. − Two-step process adds latency (~10s for Gemini).
