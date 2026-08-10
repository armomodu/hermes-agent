# Multi-gateway deployment

Hermes supports multiple gateway processes running concurrently — one per profile
(default, writer, admin, coder, researcher). Each gateway opens its own connection
to platform APIs and delivers messages for its profile's subscribers.

## Single-dispatcher posture

Only one gateway owns the kanban dispatcher. The owning gateway keeps
`kanban.dispatch_in_gateway: true` (the default); every other gateway sets it
to `false`.

**Why this matters:** dispatching is single-owner so multiple gateways do not
race to spawn the same work. Notification delivery is profile-owned instead:
each gateway polls only subscriptions for profiles whose platform adapters it
hosts. The atomic event claim prevents duplicate delivery across watcher
processes.

Mission Control uses Dolores as that sole dispatcher. Bernard, William, and
Librarian remain available as canonical assignees but keep dispatch disabled.
Runtime upgrades are installed side-by-side and must pass Mission Control's
external compatibility gate before LaunchAgents switch. Board recovery stops
all writers, preserves the failed file and sidecars, recovers into a new file,
and requires integrity, foreign-key, schema/index, and active-run reconciliation
before restart. A failed gate leaves the previous runtime active.

## Configuration

On the dispatch-owning gateway (typically the `default` profile), no change is
needed. On every other profile gateway, add to `~/.hermes/config.yaml`:

```yaml
kanban:
  dispatch_in_gateway: false
```

Or set the env var: `HERMES_KANBAN_DISPATCH_IN_GATEWAY=false`

## What each gateway does

| Gateway role | dispatch_in_gateway | Opens subscribed board DBs? | Dispatcher | Notifier |
|---|---|---|---|---|
| default (confirmed dispatch-lock owner) | true (default) | yes | yes | owned profiles + legacy unstamped subscriptions |
| writer, admin, coder, etc. | false | yes, when the profile has subscriptions | no | that gateway's owned profiles |

Non-dispatch gateways still deliver messages for their own platform adapters
(Telegram, Discord, etc.). They do not dispatch tasks, and they skip boards
that have no subscriptions owned by their profiles.

## Provider quota backpressure

Kanban workers that exhaust a provider rate or usage limit exit with the
dedicated temporary-failure code `75`. The dispatch owner returns the card to
`ready`, records a `rate_limited` event, and applies the configured cooldown
without incrementing the worker failure counter.

This applies when the provider reports either a terminal failure or a partial
result carrying authoritative rate-limit evidence. A worker must not be
classified as a clean-exit protocol violation merely because the provider
returned quota text in a partial response. Non-rate-limited partial responses
retain their existing exit behavior.
