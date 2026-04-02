# Changelog

This page provides a high-level overview of changes in each release. For full details, click a specific version.

!!! success "Help us!"
    If you ever come across an issue during our `alpha`/`beta` stage, **please** notify up ASAP. We want to weed out as much issues as possible before our `1.0.0` release.

## 0.1.0 (In Progress)

### 0.1.0a5 (STAGING)

- New query `get` methods with opt-in REST hydration.
- Cache event dispatch exceptions no longer silent when handling.
- Cache events dispatched via tasks rather than gathered coroutines.
- Cache backup and restore system.
- Custom filtering through rule `predicate`.
- `SQLiteBackend` SQL batch size now configurable.
- New cache-related events.
- Miscellaneous bug fixes.

### 0.1.0a4 (March 16th, 2026)

- Replace tagged-tuple pipeline with typed step classes, eliminating per-step cloning in `CacheIterator`, as well as fixing the stop signal being clobbered by later pipeline steps and being lost on early skip break.
- Removal of custom cache objects in favor of `hikari`-native objects.
- Message caching unsupported; may be implemented in the future if necessary.

!!! warning
    This release contains breaking changes.

### 0.1.0a3 (March 8th, 2026)

- `CacheIterator` for lazy, async iteration of cached objects.
- `Cache` accessor properties: `channels`, `guilds`, `members`, `messages`, and `roles`.
- Miscellaneous changes to backend logic flow.
- Startup caching logic.
- `Rule` changes: testing suite; `whitelist`/`blacklist` parameters renamed to `allowlist`/`denylist`.
- New `cache_messages` parameter in `Cache` constructor.

!!! warning
    This release contains breaking changes.

### 0.1.0a2 (March 4th, 2026)

- Listeners now able to dispatch on cache update or event dispatch (cache update opt-in).

### 0.1.0a1 (March 4th, 2026)

- Initial release.
