# Literature review: positioning by comparison (protocol 10)

Sources and quotes: `REFERENCES.md` (all fetched 14 October 2026). Positioning rule: comparisons only;
no "first", "novel" or "state of the art" claim. What we did not find is a gap in our search, not in
the field.

## 1. Outages from AMI: messages and pings
In utility practice, meters with outage notification send a "last gasp" message when power is lost, and
utilities can "ping" meters to bound an outage and verify restoration [L5, p. 25]; pinging through the
AMI network is also used to monitor grid-edge devices [L6]. Gandluru, Poudel and Dubey treat pings as
measurements, together with line flows and forecast load, to estimate topology and outages jointly [L2].
**Comparison.** SHAHID uses no message and no ping in its headline results: last-gasp messages are an
optional simulator feature, off by default, and the decision rests on interval energy alone. A utility
that has last gasp or pings has a more direct signal than ours; SHAHID addresses the case where only
interval readings and a transformer meter arrive.

## 2. Outage detection from flows and forecasts
Sevlian et al. detect outages in a distribution tree by "combining the use of real-time power flow
measurements on edges of the tree with load forecasts at the nodes of the tree" [L1]. Wang et al.
detect outages by learning the normal distribution of smart-meter data per region with a generative
model [L4]; the review by Wang, Chen, Hong and Kang surveys smart-meter analytics applications [L3].
**Comparison.** The principle of comparing a measured upstream flow with a forecast of downstream
consumption is shared with L1. SHAHID applies it to a narrower question - which cause explains a group
of meters that stopped reporting - using the transformer's LV energy, the arrival pattern of readings,
and a likelihood ratio between the two causes. Unlike L4, SHAHID trains no model of normal data
beyond fitted noise parameters.

## 3. Deciding with a reject option
Chow characterised a recognition system by its "error and reject tradeoff" [L7]. Selective
classification trades "classifier coverage for higher accuracy" [L8]; Geifman and El-Yaniv reject
instances "to grant the desired risk (with high probability)" [L9]; Franc, Prusa and Voracek show that
cost-based, bounded-improvement and bounded-abstention formulations "lead to the same prediction
strategy" [L10]. **Comparison.** SHAHID's rule v3 is a constrained selection of the same kind: it
bounds missed outages, false outages and fault-free false outages, then maximises coverage, choosing a
band around a likelihood-ratio posterior. Unlike L9, the guarantee is empirical (simulation), not a
high-probability bound; Phase 2 finding: mid-range posteriors are not calibrated frequencies over all
silent groups (protocol 07a).

## 4. Trust in automation
Records verified, quotes not yet fetched: Parasuraman and Riley [L12] and Lee and See [L11]. No claim in
any SHAHID document rests on them.

## What remains
- Fetch quotable pages for L11 and L12 (open repositories or the publisher with access).
- Search for work on separating outages from communication failures with energy balances (none found
  in this pass), and for non-technical-loss balance methods with a fetchable page (the MDPI review
  returned 403).
