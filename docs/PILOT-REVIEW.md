# Pilot Review Framework

## Pilot Parameters

| Parameter | Value |
|---|---|
| Ward | Ward-001 (Pune Pilot) |
| Duration | 4 weeks |
| Target observations | 100 |
| Target signals | 20 |
| Users | Municipal team (5 operators) |

## Metrics to Collect

### Operational Metrics

| Metric | Source | Target | How to Measure |
|---|---|---|---|
| Observation submissions | API counter | ≥ 100 total | `GET /analytics` |
| Unique submitters | Device ID tracking | ≥ 30 unique | `GET /analytics` |
| Signal generation rate | Signal counter | ≥ 1 per day | `GET /analytics` |
| Avg confidence score | Signal metadata | 0.4–0.7 | `GET /analytics` |
| Provider availability | Health checks | ≥ 95% uptime | `GET /providers/health` |
| Gemini latency | Metrics store | < 5s average | `GET /metrics/live` |
| API response time | Middleware | < 500ms p95 | `GET /metrics/live` |

### Quality Metrics

| Metric | How to Measure | Target |
|---|---|---|
| False positives | Field verification of High Confidence signals | ≤ 15% |
| False negatives | Compare against known incidents not flagged | ≤ 20% |
| Precision | Verified / (Verified + False Positives) | ≥ 85% |
| Recall | Flagged / (Flagged + Missed) | ≥ 80% |
| Verification time | Time from signal creation to field team dispatch | < 30 min |
| Duplicate detection accuracy | Audit sampling of deduplicated observations | ≥ 90% |

### User Metrics

| Metric | How to Measure | Target |
|---|---|---|
| Submission success rate | Successful / attempted submissions | ≥ 95% |
| Avg submission time | Time from app open to confirmation | < 60 seconds |
| Language distribution | Count by language field | EN:HI:MR ≈ 40:35:25 |
| User satisfaction | Post-pilot survey (1–5 scale) | ≥ 3.5 |

## Calibration Process

### Week 1–2: Baseline
- Deploy with default thresholds
- Collect initial observations
- Identify any threshold mismatches

### Week 3: First Calibration
- Review false positive/negative rates
- Adjust spatial/temporal thresholds if needed
- Update evidence weights if needed
- Create new policy version

### Week 4: Final Calibration + Review
- Second calibration pass
- Compile pilot metrics
- Conduct municipal team review
- Document lessons learned

## Policy Calibration Rules

1. **Never change thresholds without recording a new policy version**
2. **Compare precision/recall before and after each change**
3. **If false positives increase after a change, revert within 24 hours**
4. **Document the reason for every threshold adjustment**
5. **Keep all historical policy versions for reproducibility**

## Pilot Review Questions

### For Municipal Operators

1. Did you find the signals useful for prioritizing field teams?
2. Were false positives manageable, or did they waste field team time?
3. Was the explainability sufficient to understand why a signal was flagged?
4. Was the UI intuitive? What was confusing?
5. How long did it take from signal creation to field team dispatch?

### For System Assessment

1. Did the system handle the pilot load without issues?
2. Were provider fallbacks working correctly?
3. Did the correlation engine produce reasonable results?
4. Were there any edge cases not covered by the spec?
5. What thresholds would you recommend for the next ward?

## Expansion Criteria

Only expand to additional wards when:

- [ ] Pilot duration ≥ 4 weeks completed
- [ ] ≥ 80 observations collected
- [ ] False positive rate ≤ 15%
- [ ] Municipal operators rate usefulness ≥ 3.5/5
- [ ] No critical bugs in last 2 weeks
- [ ] Policy calibrated and versioned
- [ ] Runbook tested by on-call engineer
