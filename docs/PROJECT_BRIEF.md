# Promo Sniffer — project brief

This document is the source of truth for product decisions. Unknowns are deliberately left open rather than being turned into assumptions.

## Product purpose

_To be defined._

## Users and primary use cases

_To be defined._

## Promotion sources

- Supported stores / marketplaces: _TBD_
- Collection method (official API, feeds, permitted crawling): _TBD_
- Geographic / currency scope: _TBD_

## Promotion data

- Required fields: _TBD_
- Price history and deduplication rules: _TBD_
- Product identity / matching rules: _TBD_

## Detection and delivery

- What qualifies as a promotion: _TBD_
- Filtering and user preferences: _TBD_
- Notification channels and cadence: _TBD_

## Non-functional requirements

- Expected collection frequency and volume: _TBD_
- Persistence and retention: _TBD_
- Availability and recovery expectations: _TBD_
- Privacy, source terms and rate limits: must be respected.

## Technical decisions

| Decision | Status |
|---|---|
| Language / runtime | Open |
| Framework | Open |
| Database | Open |
| Scheduler / queue | Open |
| Frontend / API | Open |
| Hosting | Hetzner VPS, subject to resource validation |
| Container registry | GitHub Container Registry (planned) |
| Private access | Tailscale (planned) |

## Delivery milestones

1. Confirm scope and data sources.
2. Select architecture and define data model.
3. Implement a small vertical slice with tests.
4. Add Docker packaging and health checks.
5. Add GHCR build and deployment workflow.
6. Deploy to the VPS with persistent storage, backup and rollback.
