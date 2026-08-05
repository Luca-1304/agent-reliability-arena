# Desktop full-width titles

## Goal
Make the portfolio's primary page and section titles use the full desktop content width rather than remaining constrained to narrow columns or card-like areas.

## Scope
- Desktop only, starting at 900px.
- Keep the current mobile layout unchanged.
- Preserve the existing typography, colours, content, navigation, and interactions.
- Expand the homepage hero title, Evidence and Interests opening titles, split section headings, and the flagship evidence heading.
- Keep content cards, metrics, and supporting copy structurally intact.

## Implementation
Add a separate `desktop-headings.css` override loaded after `portfolio.css` on all three public pages. This isolates the change from the base responsive system and makes rollback straightforward.

## Verification
- Confirm all three pages load the override stylesheet.
- Confirm the override is contained inside a desktop media query.
- Run repository tests, CodeQL, Vercel previews, and public-route checks.
- Verify mobile markup and base CSS are unchanged.
