# Interview Prep Library site

This directory contains the static-site builder for the standalone `interview-pro` study hub. It publishes reusable preparation decks and code solutions while keeping recruiter correspondence, calendar details and meeting transcripts out of the catalogue.

From the repository root, build the site with:

```bash
python3 interview-prep/site/build.py
```

The generated files are written to `_site/`. Validate their local links with:

```bash
python3 scripts/check-links.py _site
```

To add material, add an entry to `catalog.json` with a stable `id`, a path relative to the repository root, a `section`, a short `description`, and searchable `tags`.
