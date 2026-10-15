# Related work notes

Checked 2026-10-06 in a time-boxed web search. Each entry below was verified by opening its
arXiv abstract page. The summaries are ours, based on the abstract only; we have not read the
full papers. **This is not an exhaustive survey, so we make no novelty claim.**

## Verified

1. R. Sevlian, Y. Zhao, A. Goldsmith, R. Rajagopal, H. V. Poor. *Distribution System Outage
   Detection using Consumer Load and Line Flow Measurements.* arXiv:1503.08244 (2015, revised
   2016). https://arxiv.org/abs/1503.08244
   — Combines line-flow measurements with load forecasts at nodes in a maximum a posteriori
   outage detector on tree networks, and studies sensor placement. **Closest in spirit to our
   balance test:** measured flow against forecast load. It addresses outage detection and location,
   not the comms-versus-outage question for silent meters.
2. Y. Yuan, K. Dehghanpour, F. Bu, Z. Wang. *Outage Detection in Partially Observable Distribution
   Systems using Smart Meters and Generative Adversarial Networks.* arXiv:1912.04992 (2019).
   https://arxiv.org/abs/1912.04992
   — Unsupervised detection of changes in smart-meter data distributions, with zone coordination
   for location.
3. Y. Yuan, K. Dehghanpour, Z. Wang, F. Bu. *Multi-Source Data Fusion Outage Location in
   Distribution Systems via Probabilistic Graph Models.* arXiv:2012.02877 (2020, revised 2021).
   https://arxiv.org/abs/2012.02877
   — Bayesian network fusing smart-meter last-gasp signals, trouble calls, social media, weather
   and vegetation data. It relies on last-gasp messages, which our headline results deliberately
   do not use.
4. Z. Soltani, S. Ma, M. Khorsand, V. Vittal. *Simultaneous Robust State Estimation, Topology
   Error Processing, and Outage Detection for Unbalanced Distribution Systems.* arXiv:2105.10111
   (2021). https://arxiv.org/abs/2105.10111
   — Mixed-integer state estimation that tolerates missing and bad data and detects outages through
   analytic constraints.
5. B. R. J. Arka, M. Z. Islam, Y. Lin, V. M. Vokkarane, J. Zhao. *Communication Network-Aware
   Missing Data Recovery for Enhanced Distribution Grid Visibility.* arXiv:2603.07049 (2026),
   listed for IEEE PES General Meeting 2026. https://arxiv.org/abs/2603.07049
   — Treats data loss as structured by shared communication paths. Related to our concentrator
   model.
6. Y. Wang, Q. Chen, T. Hong, C. Kang. *Review of Smart Meter Data Analytics: Applications,
   Methodologies, and Challenges.* IEEE Transactions on Smart Grid (2018).
   doi:10.1109/TSG.2018.2818167, arXiv:1802.04117.

## How SHAHID relates (no novelty claim)
SHAHID uses the transformer-versus-meters energy balance for one narrow question: whether a silent meter group
lost power or only data. It does so without last-gasp messages, with decision-time semantics,
explicit abstention, and simulation-based detectability curves. Whether this combination is new
would require a proper literature review.
