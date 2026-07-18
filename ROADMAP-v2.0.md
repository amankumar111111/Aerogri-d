# AEROGRID v2.0 Roadmap

**These are research problems, not feature requests.**

Each item below is an open question that requires investigation, experimentation, and validation before implementation. None of these are "build a button" tasks.

---

## 1. Observation Independence ML

**Research question:** Can we learn to distinguish independent observations from dependent ones without hand-crafted rules?

The current independence dimension uses simple heuristics (same device, same session, fingerprint matching). A learned model could capture subtler patterns — observations that reference each other, observations from the same household, observations triggered by the same event but reported by different people.

**Open questions:**
- What features predict independence? (device metadata, temporal patterns, linguistic cues, spatial clustering)
- Can we train a classifier on labeled observation pairs?
- How do we handle the cold start problem (no labeled data)?
- What's the precision/recall tradeoff vs. the current heuristic?

---

## 2. Policy Calibration Dashboard

**Research question:** How do we enable municipalities to tune correlation thresholds without breaking the system?

The calibration API exists but the UX is undefined. Municipal operators need to understand the impact of threshold changes before committing them.

**Open questions:**
- What visualization best communicates the precision/recall tradeoff?
- How do we replay historical incidents under proposed thresholds?
- What guardrails prevent dangerous configurations (e.g., threshold too low = noise, too high = missed events)?
- How do we version and rollback policy changes safely?

---

## 3. Municipal Pilot

**Research question:** Does AEROGRID actually help municipalities make better decisions?

We have a system. We don't yet have evidence that it works in practice. A pilot with real operators and real observations is the only way to validate.

**Open questions:**
- Do municipal operators trust the signals enough to dispatch field teams?
- What's the false positive tolerance before operators ignore the system?
- How does the system perform in areas with low citizen participation?
- What's the minimum viable signal count for a ward to benefit?

---

## 4. Crowdsourced Trust Score

**Research question:** Can we infer observation reliability from community patterns?

Not by scoring citizens (explicitly a non-goal). By analyzing patterns: observations that consistently correlate with verified events vs. observations that don't. This is a statistical signal about observation quality, not a citizen ranking.

**Open questions:**
- What patterns predict observation accuracy? (media quality, description specificity, timing)
- Can we compute a reliability score without storing citizen identity?
- How do we prevent gaming (coordinated false reports)?
- What's the ethical boundary between quality inference and surveillance?

---

## 5. Sensor Integration

**Research question:** How do we incorporate low-cost IoT sensors as observation sources?

Citizen observations are qualitative. IoT sensors provide quantitative data. Combining them could strengthen signal confidence — a citizen reports smoke, and a nearby PM2.5 sensor confirms elevated readings.

**Open questions:**
- What sensor protocols do we support? (MQTT, LoRa, HTTP push)
- How do we normalize sensor readings into the correlation engine?
- What's the trust model for uncalibrated citizen-deployed sensors?
- How do we handle sensor data that contradicts citizen observations?

---

## 6. Drone Imagery

**Research question:** Can aerial imagery provide ground truth for signal verification?

Drones could verify signals before dispatching field teams. A drone flyover could confirm whether a reported smoke plume is real, reducing false positives.

**Open questions:**
- What resolution is needed for environmental event classification?
- How do we integrate drone flight paths with signal locations?
- What's the latency from signal creation to drone deployment?
- Is this cost-effective vs. just sending a field team?

---

## 7. Predictive Intelligence

**Research question:** Can we predict environmental events before they're reported?

If we know that certain conditions (weather + industrial activity + citizen patterns) historically precede events, can we forecast likely hotspots?

**Open questions:**
- What historical patterns predict environmental events?
- How far in advance can we predict with acceptable accuracy?
- What are the ethical implications of predicting pollution events?
- How do we avoid false alarms that erode trust?

---

## 8. Multi-City Deployment

**Research question:** How does the architecture hold across different municipalities with different regulations?

Pune's environmental regulations differ from Delhi's. The correlation engine is city-agnostic, but the policies, thresholds, and provider integrations may need per-city configuration.

**Open questions:**
- What's the minimum configuration needed per city?
- How do we handle cities with different primary environmental concerns?
- Can we share learned patterns across cities without sharing citizen data?
- What regulatory compliance is needed per jurisdiction?

---

## Timeline

| Quarter | Focus | Deliverable |
|---|---|---|
| Q3 2026 | Municipal Pilot | Pilot ward deployment, metrics collection |
| Q4 2026 | Policy Calibration | Calibration dashboard, threshold tuning UX |
| Q1 2027 | Trust Score Research | Labeled dataset, classifier prototype |
| Q2 2027 | Sensor Integration | MQTT adapter, sensor normalization |
| Q3 2027 | Multi-City | Configuration framework, second city deployment |
| Q4 2027 | Predictive Intelligence | Historical pattern analysis, forecasting prototype |

---

## Principle

Every item on this roadmap is a research problem. We don't implement until we understand. We don't deploy until we've validated. We don't scale until we've measured.
