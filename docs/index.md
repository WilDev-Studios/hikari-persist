<p align="center">
    <img src="https://raw.githubusercontent.com/WilDev-Studios/hikari-persist/main/assets/banner.png" width=750/><br/>
    <b>A lightweight and modular persistent cache library for hikari-based Discord bots</b><br/><br/>
    <img src="https://img.shields.io/pypi/pyversions/hikari-persist?style=for-the-badge&color=007EC6"/>
    <img src="https://img.shields.io/pypi/v/hikari-persist?style=for-the-badge&color=007EC6"/>
    <img src="https://img.shields.io/pypi/dm/hikari-persist?style=for-the-badge&color=007EC6"/><br/>
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json&style=for-the-badge&color=002F4B"/>
    <img src="https://img.shields.io/readthedocs/hikari-persist?style=for-the-badge&color=002F4B"/>
    <img src="https://img.shields.io/github/actions/workflow/status/WilDev-Studios/hikari-persist/build.yml?branch=main&style=for-the-badge&label=Build/Tests&color=002F4B">
    <img src="https://img.shields.io/pypi/status/hikari-persist?style=for-the-badge&color=002F4B"/>
</p>

## Overview

`hikari-persist` is a persistent caching library for [`hikari`](https://github.com/hikari-py/hikari) that provides a familiar API with local data.

It is designed to be:

- **Simple to use**
- **Fully asynchronous**
- **Similar to `hikari`'s REST functionality**

## Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Help/Contact](#help-and-contact)
- [Versioning/Stability Policy](#versioning-stability-policy)

## Features

- Async-first, awaitable API
- Strong typing and documentation throughout (Pylance/MyPy friendly)
- Designed specifically for `hikari`'s async model
- Minimal overhead and predictable behavior
- Fully modular with custom database backends
- Automatic database migration
- Rulesets to control what data is cached

## Purpose

Unlike `hikari`'s built-in, in-memory cache, `hikari-persist`:

- Survives restarts and crashes
- Scales across large guild counts
- Allows database-level inspection and analytics
- Supports pluggable storage backends

## Installation

```bash
pip install hikari-persist
```

## Quick Start

Create a basic cache bot:

```python
import hikari
import hikaripersist as persist

bot = hikari.GatewayBot("TOKEN")
cache = persist.Cache(bot, persist.SQLiteBackend("cache.db"))

bot.run()
```

To ensure that the cache sees all event data before being handled, the cache acts as a middle-man in event dispatching.
Instead of using `@bot.listen()`, use `@cache.listen()` and the cache will dispatch each event normally after it's complete.

```python
@cache.listen() # <- note `cache` not `bot`
async def event_listener(event: hikari.Event):
    ...
```

This approach works well for most operations, however, due to the nature of asynchronous, batched databases, the cache is not guaranteed to have the changes complete by the time the event is dispatched. To ensure the cache is properly changed before you see the event, pass `confirm=True` into the decorator.

```python
@cache.listen(confirm=True) # <- confirm=True
async def event_listener(event: hikari.Event):
    ...
```

The difference between the two is this:

```python
@cache.listen()
async def event_listener_1(event: hikari.GuildMessageCreateEvent):
    message = await cache.get_message(event.message_id, event.channel_id)

    print(message)

@cache.listen(confirm=True)
async def event_listener_2(event: hikari.GuildMessageCreateEvent):
    message = await cache.get_message(event.message_id, event.channel_id)

    print(message)
```

```bash
>>> None (or sometimes `persist.CachedMessage`)
>>> `persist.CachedMessage`
```

The `confirm=True` ensures the cache is up to date before dispatching the event. Otherwise, it's not guaranteed.

Most implementations will not need to worry about this, but it's here just in case it's necessary.
The confirmation logic does introduce slight latency to the event dispatch, but it's negligible unless you worry about real-time performance.

TL;DR:
- `confirm=False` (or omitted): Fire-and-forget (default, very fast)
- `confirm-True`: Waits for database write to complete (slight latency)

## Cache/Database Stability

Before `1.0.0`, the database schema may change between versions.
If this occurs, delete your cache database and allow it to rebuild.

Database migration is implemented, but early development is cumbersome when getting the API stabilized.

## Implemented Features

- [X] Basic objects (messages, channels, guilds, members, etc.)
- [X] Advanced lookups (filter, map, limit, etc.)
- [X] Advanced object metadata
- [ ] Opt-in hydration (cache fail -> REST fetch)
- Database backends:
    - [X] SQLite
    - [ ] MySQL
    - [ ] PostgreSQL
    - [ ] Redis
    - [ ] JSON

## Library Lifecycle

See https://hikari-persist.wildevstudios.net/en/latest/pages/lifecycle for the full list of deprecated and experimental features.

## Help and Contact

Feel free to join the [hikari](https://discord.gg/hikari) Discord server under the `#persist` channel for assistance.

## Versioning & Stability Policy

`hikari-persist` follows **Semantic Versioning** with a clear and practical stability model designed to balance rapid development with reliability.

### Version Format

`MAJOR.MINOR.PATCH`

### Patch Releases (`x.y.Z`)

- Bug fixes and internal improvements only
- No breaking changes
- Always considered **stable**
- No alpha (`a`) or beta (`b`) suffixes

Patch releases are safe to upgrade to without code changes.

### Minor Releases (`x.Y.0`)

- Introduce new features, subsystems, or configuration options
- Existing public APIs generally preserved, but behavior may expand
- May include **short-lived alpha/beta pre-releases** before stabilization

Example releases flow:
`1.0.0a1 -> 1.0.0b1 -> 1.0.0 -> 1.0.1`
Pre-releases exist to gather feedback and catch issues early. Once stabilized, the same version is released as a stable minor.

### Pre-Releases (`a`/`b`)

- Used only for **new minor/major versions**
- Intended for developers who want early access to new features/versions
- Not recommended for production unless you are testing upcoming functionality
