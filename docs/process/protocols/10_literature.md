# Protocol 10 — Priority 10: literature review with verified references only

Registered 2026-10-14, before any search. Frame: protocol 00. Integrity rule 7: no citation, DOI,
URL or statistic from memory.

## Questions
1. How do published methods separate a power outage from a meter communication failure using AMI
   data (energy balance, last-gasp messages, voltage, topology)?
2. Which use a transformer or feeder-head energy balance?
3. Selective prediction / classification with a reject option: definitions and how abstention is
   chosen under error constraints.
4. Operator trust in automation: over-trust and under-trust measures used in control rooms.

## Sources and search
- Open, fetchable pages only: publisher abstract pages, arXiv, open-access repositories, standards
  bodies' public pages. Search engines are used to find candidates; nothing is cited from a search
  snippet.
- Search strings are recorded verbatim with their date in `docs/literature/search_log.md`.

## Inclusion and recording
- A source is included only after its page is fetched in this session. Per source:
  title, authors, venue, year and DOI or URL **as printed on the fetched page**, the access date, and
  one quoted sentence supporting what we say it shows.
- A source that cannot be fetched is listed as TODO with the reason; it is not cited.
- `docs/literature/REFERENCES.md` holds the verified list; `docs/literature/REVIEW.md` the synthesis.

## Positioning rule
SHAHID is placed against the verified sources by **comparison only** ("unlike X, which uses Y, we
use Z"). No "first", "novel" or "state of the art" claim, whatever the review finds. A gap in the
review is described as a gap in what we found, not as a gap in the field.

## Effort ESTIMATE
Work time, no compute: about 4–6 hours of searching and fetching.
