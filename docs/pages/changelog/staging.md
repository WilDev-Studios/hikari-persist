# PENDING_VERSION

Released `UNRELEASED`

## Changes

- Refactor of `SQLiteBackend` logic - modular internal logic for future backends.
- Additional testing suite for all added internal systems and logic.
- Reorganized module folders based on their purpose and scope within the library.

## Fixes

- `...Rule` object initialization failures based on `set` adding from other sets rather than updating from them.
- `SQLiteBackend` writer logic would silently swallow exceptions through unset confirmation futures.
- Ratelimits on startup due to outdated/inefficient guild lookup.
