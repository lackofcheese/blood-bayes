# Data handling and provenance

The NAF export and all extracted or derived row-level data are local analytical
inputs. They are intentionally excluded from Git because the source contains coach
names, tournament contact details, email addresses, and precise locations.

## Current source

- Local filename: `nafstat-tmp-name.zip`
- Export directory in archive: `naf-stat-dump-2026-07-11-0914/`
- Dump timestamp represented by source name: 2026-07-11 09:14
- SHA-256: `afcc9a3d72d0c8ae9ac83a98af6f8abccc18486c0b61fc9794013cb876c735de`

The ingestion pipeline records a checksum and source-member metadata at run time; the
archive itself must not be committed.

## Privacy boundary

- Derived match, entry, and coach tables use opaque NAF coach IDs.
- Coach names, tournament contacts, email addresses, street addresses, postcodes, and
  exact coordinates must not appear in derived tables or generated reports.
- Country and city may be retained at event level for regional diagnostics. Published
  reports should aggregate cells that could identify individuals.
- Raw source fields may be read only inside source adapters and integrity checks.

## Source responsibilities

NAF is authoritative for recorded tournament matches, participants, race selections,
and tournament metadata. It is not assumed to contain an authoritative structured
tournament pack. NAF descriptions, URLs, and ruleset-file references are discovery
evidence for a separate pack registry.

Tourplay, pack PDFs, and organiser pages will be assessed as pack sources. Links to
those sources must be stored with match method, confidence, review status, and quoted
or structured evidence; fuzzy event-name matches are never silently accepted.
