# Staff-Level System Design Deck — 12 Classic Problems

**How to use this deck:** Each entry is a cold-start prompt exactly as an interviewer would drop it, followed by a full model solution. Don't read the solution first — set a timer, run the requirements-and-numbers phase out loud against yourself, sketch the architecture, then compare. The value is in the *failure-mode* and *trade-off* sections — that's where staff bar is actually decided, not in the box diagram.

Every solution follows the same skeleton, matching the notification-system script: **Clarify → Numbers → Architecture → Deep dives (the parts that actually get grilled) → Common mistakes → If they push further**.

---

## Index

1. [URL Shortener](#1-url-shortener)
2. [Rate Limiter](#2-rate-limiter)
3. [Distributed Chat / Messaging (WhatsApp-class)](#3-distributed-chat--messaging)
4. [Ticket Booking System (Ticketmaster-class)](#4-ticket-booking-system)
5. [Web Crawler](#5-web-crawler)
6. [Ad Click Aggregation / Counting Pipeline](#6-ad-click-aggregation--counting-pipeline)
7. [News Feed Generation (Twitter/Instagram-class)](#7-news-feed-generation)
8. [Distributed Key-Value Store (Dynamo-class)](#8-distributed-key-value-store)
9. [Video Streaming Platform (YouTube/Netflix-class)](#9-video-streaming-platform)
10. [Search Autocomplete / Typeahead](#10-search-autocomplete--typeahead)
11. [Distributed Job Scheduler](#11-distributed-job-scheduler)
12. [Payment Processing System](#12-payment-processing-system)

---

## 1. URL Shortener

**Cold prompt:** "Design a URL shortening service like TinyURL or bit.ly."

**Why it's asked:** It looks trivial, which is the point — it's a filter for whether you'll do the numbers and the correctness work when nothing forces you to.

### Clarify
- Custom aliases allowed, or only generated codes?
- Expiry — do links live forever or TTL?
- Redirect type — 301 (cacheable, browser remembers, can't track re-clicks) or 302 (hits your server every time, enables analytics)? This single answer reshapes your read-scaling story.
- Do we need click analytics?
- Read:write ratio — assume heavy read skew (100:1) unless told otherwise; confirm it.

### Numbers
- Assume 500M new URLs/month → ~200 writes/sec average.
- 100:1 read skew → ~20K reads/sec average, 3-5× at peak.
- 7-char base62 code space = 62^7 ≈ 3.5 trillion — comfortably covers years of writes; don't over-engineer the code length.
- Storage: 500M/month × 500 bytes (long URL + metadata) × 5 years ≈ 15TB. Trivial; this is a compute/caching problem, not a storage problem.

### Architecture
- Write path: API → key-generation service → key-value store (long_url keyed by short_code).
- **Key generation is the actual design decision**, not the database. Two real options: (a) pre-generated pool of unique keys handed out from a range-partitioned counter (e.g., Zookeeper/DB-backed range allocator per app server, avoiding contention), or (b) hash(long_url) truncated + collision check + re-salt on collision. Counter-based avoids collision handling entirely at the cost of a coordination service; hash-based is simpler but needs a collision-retry loop and can produce different codes for the same URL submitted twice (fine, usually not a requirement to dedupe).
- Read path: cache (Redis) in front of the KV store — with 100:1 skew, cache hit rate should be 90%+ and this is where most of your QPS budget actually goes.
- Redirect service is stateless, horizontally scaled behind a load balancer.

#### Whiteboard sketch

```text
WRITE (~200/sec)
client ─▶ API ─▶ key-gen service ─▶ KV store: short_code → long_url
                 (pre-allocated ranges per server:
                  A gets 1M–2M, B gets 2M–3M —
                  no per-write coordination)

READ (~20K/sec avg, 100:1 skew — THE hot path)
client ─▶ LB ─▶ redirect svc ×N ─▶ Redis cache ─▶ KV store
                (stateless)         (90%+ hit)     (miss only)
                                    hot key? replicate across
                                    cache nodes / in-process L1
```

### Deep dives
- **Collision handling under concurrent writes:** two servers hash the same long URL simultaneously with the counter offline — how do you guarantee uniqueness without a global lock? Answer: pre-allocate key *ranges* per server (e.g., server A gets keys 1M–2M), so no cross-server coordination is needed per write, only occasionally when a range is exhausted.
- **Custom alias race:** two users request the same custom alias simultaneously. This is a uniqueness-constraint problem, not a hashing problem — enforce it with a DB unique index and handle the constraint-violation error path explicitly, don't pre-check-then-write (TOCTOU race).
- **Cache invalidation on delete/expiry:** if a link is deleted or expires, is the cache entry evicted immediately or does it serve stale for a bounded window? State your choice — for a redirect service, briefly serving a dead link is usually an acceptable trade for not adding synchronous cache invalidation traffic.
- **Hot key:** a URL goes viral — one code getting 50K reads/sec. A single Redis key becomes a hot shard. Mitigation: replicate hot keys across multiple cache nodes with client-side random selection, or a local (in-process) cache layer in front of Redis for the top-N hottest keys.

### Common mistakes
- Spending 20 minutes on the hashing algorithm and none on cache architecture, when cache is where the actual QPS lives.
- Not asking about redirect type — it changes whether you need analytics infrastructure at all.
- Treating storage as a hard problem when at these numbers it isn't — burning time there is a signal you don't know what's actually hard here.

### If they push further
Add analytics (click counts by geography/referrer/time) — this becomes the ad-click-aggregation problem (#6) bolted onto the redirect path: don't do synchronous counter increments on the hot read path; emit an async event and aggregate downstream.

---

## 2. Rate Limiter

**Cold prompt:** "Design a rate limiter for a global API platform."

**Why it's asked:** Tests whether you understand that "rate limiter" is actually a distributed-counter-consistency problem wearing a simple mask.

### Clarify
- Rate limit scope — per-user, per-IP, per-API-key, per-endpoint, or combinations?
- Is this a single service's limiter, or a shared platform used by many services (i.e., is it a library, a sidecar, or a centralized service)?
- What happens on limit breach — hard reject (429), or queue/delay?
- Do limits need to be exact, or is approximate enforcement (occasional slight overshoot) acceptable for throughput?

### Numbers
- Global API platform: assume 1M requests/sec platform-wide, distributed across thousands of rate-limit keys (users/IPs).
- Each check needs to be sub-millisecond — it sits on the critical path of every request.
- If centralized: 1M checks/sec against a shared store is the core scaling problem.

### Architecture
- **Algorithm choice, stated and defended:** token bucket (allows bursts up to bucket size, smooths over time — usually the right default for APIs) vs. sliding window log (exact but memory-heavy — stores every timestamp) vs. sliding window counter (approximate, cheap, good compromise). Fixed window is the wrong answer here — it allows 2× burst at window boundaries, and if you propose it, expect to be asked why immediately.
- Distributed counter store: Redis, using atomic `INCR`+`EXPIRE` or a Lua script per check to make the read-check-write atomic (critical — without atomicity you get race conditions that let requests through over the limit).
- Deployment shape: a **sidecar or local in-memory cache with periodic sync** to the central store, rather than a network round-trip to Redis on every single request — this is the actual scaling lever. Local counters with approximate sync (e.g., every 100ms or every N requests) trade a small amount of over-limit slop for removing the network hop from the hot path.

#### Whiteboard sketch

```text
request ─▶ app server ×N ─── allow ──▶ upstream API
           │ local token bucket
           │ (hot path: no network hop) ── deny ──▶ 429 + Retry-After
           │
           │ periodic async sync (~100ms or every N requests)
           ▼
     Redis shards (by limit key)
     Lua script = atomic check + incr  ← kills the read-then-write race
     store down? ─▶ fail-open (internal platform)
                    vs fail-closed (abuse-facing paths)
```

### Deep dives
- **The atomicity problem, made concrete:** two requests from the same user arrive at two different app servers simultaneously, both read count=99 (limit 100), both increment, both pass — you've let 101 through. Fix: atomic Redis operations (Lua script combining check+increment) or a local single-threaded counter per shard if requests for a key are consistently routed to the same node.
- **Distributed synchronization cost vs. accuracy:** if you go local-cache-with-periodic-sync, quantify the overshoot — with 1000 app servers each allowing a local burst before syncing, you can overshoot the global limit by up to (per-node allowance × node count) in the worst case. Say the number, and say whether it's acceptable for this use case (usually yes, rate limiting is a protective measure, not a billing-accuracy measure — contrast explicitly with payment processing, #12, where it isn't).
- **Fail-open vs. fail-closed:** the Redis cluster backing the limiter goes down. Do you reject all traffic (fail-closed — safe but takes down the platform on an infra blip) or allow all traffic (fail-open — available but you lose protection exactly when you might need it, e.g., during an attack)? State the choice and tie it to context: internal platform → fail-open with alerting; public-facing anti-abuse limiter → fail-closed on suspicious paths only.
- **Clock skew across nodes** breaks any window-based algorithm that relies on wall-clock boundaries — mitigate with a monotonic logical window computed from a shared time source, or accept it as bounded slop.

### Common mistakes
- Proposing fixed window without being asked and not noticing the boundary-burst flaw yourself.
- Treating this as a single-node problem and never addressing what happens when the limiter itself is distributed across machines.
- No answer for what happens when the counter store is unavailable.

### If they push further
Multi-tier limits (per-second AND per-day quotas simultaneously) — requires either two independent counters checked in sequence, or a more complex structure like a leaky-bucket hierarchy; state the check order (cheapest/most-restrictive first) to fail fast without wasted work.

---

## 3. Distributed Chat / Messaging

**Cold prompt:** "Design a one-on-one and group messaging system like WhatsApp."

**Why it's asked:** Ordering, delivery guarantees, and offline fan-out are all correctness-under-failure problems — this is the deep-dive-friendliest prompt on the list.

### Clarify
- 1:1 only, or also group chats? (Group chat is a fan-out problem; 1:1 mostly isn't.)
- Delivery guarantees needed — at-least-once with client dedup, or do we need to guarantee ordering per conversation?
- Read receipts / delivery receipts / typing indicators in scope?
- Media (images/video) or text-only?
- Online/offline — do offline users need push notification integration, and how long do undelivered messages persist?

### Numbers
- Assume 500M DAU, avg 40 messages/day sent → 20B messages/day, ~230K messages/sec average, 3× peak ~700K/sec.
- Group chats: assume 20% of messages go to groups averaging 50 members → fan-out multiplies effective delivery volume roughly 10×.
- Message storage: 20B/day × 200 bytes ≈ 4TB/day raw; history retention policy matters a lot here (unlike notifications, chat history is often kept indefinitely, so ask).

### Architecture
- Client ↔ **connection/gateway layer** holding persistent WebSocket/long-poll connections, mapping user_id → server instance (a presence/session registry, typically in Redis).
- Sender's message → message service → **per-conversation ordered log** (partitioned by conversation_id, not user_id, so ordering within a conversation is preserved) → fan-out to recipients' connection servers if online, or to a push-notification path if offline.
- Message store: partitioned by conversation, time-ordered, is the source of truth; the connection layer is purely transport.
- Group fan-out: **fan-out-on-write** for normal-sized groups (write the message once per recipient's inbox/read-cursor) vs. **fan-out-on-read** for huge groups/broadcast channels (store once, compute per-user unread state on read) — state which threshold you'd switch at and why (fan-out-on-write gets expensive fast for 100K-member channels).

#### Whiteboard sketch

```text
sender ─▶ gateway ×N ─▶ message svc ─▶ per-conversation log
          (WebSocket)                   partition: conversation_id
                                        seq# assigned HERE (ordering)
                                              │
                            ┌─────────────────┴────────┐
                            ▼                          ▼
                      message store             presence registry
                      (source of truth;         user → gateway node
                       read cursor per user)          │
                                            online?  ─▶ recipient gateway
                                            offline? ─▶ push notification

reconnect: client sends last acked cursor ─▶ fetch everything after it
           (self-heals gaps; duplicates dropped client-side by seq#)
```

### Deep dives
- **Ordering guarantee:** two messages sent by the same user in the same conversation must arrive in order even if they hit different servers or get retried. Fix: a monotonically increasing sequence number *per conversation*, assigned at the point the log accepts the write, with clients rendering strictly by sequence number rather than arrival order or client timestamp (client clocks aren't trustworthy).
- **Exactly-once delivery, the honest version:** you can't get exactly-once transport, only at-least-once transport plus idempotent rendering. Client attaches a client-generated message ID; server dedupes on that ID at the log-write layer (same idempotent-upsert pattern as the notification store); recipient UI drops duplicates by ID. State this explicitly rather than claiming "exactly-once delivery" as a transport property.
- **Offline delivery and the gap-vs-duplicate question:** recipient's connection server crashes mid-delivery. Undelivered messages must not be lost (gap) — solved by recipient having a durable per-conversation read cursor in the message store; on reconnect, client fetches everything after its last acked cursor, which naturally self-heals gaps and tolerates duplicate delivery (idempotent by sequence number) rather than needing the transport layer to be perfect.
- **Multi-device consistency:** same account on phone and laptop — a message read on one device should show as read on the other. This is the same "consistency mechanism" question as the notification center: the read-cursor is server-side and shared, and each device syncs against it rather than maintaining independent local state as the source of truth.

### Common mistakes
- Ordering messages by arrival timestamp at the server instead of a conversation-scoped sequence number — breaks under retries and multi-server fan-out.
- Claiming "exactly-once" without naming the idempotency mechanism that actually delivers it.
- Fan-out-on-write for every group regardless of size, without noticing it collapses at large group/channel scale.

### If they push further
End-to-end encryption: message content becomes opaque to the server, which breaks server-side search and content moderation — you'd need to explicitly trade those features away or push them client-side, and say so rather than glossing over it.

---

## 4. Ticket Booking System

**Cold prompt:** "Design a ticket booking system like Ticketmaster for concerts and events."

**Why it's asked:** The overselling problem is a pure concurrency-correctness test with zero room to hand-wave — money and legal exposure are on the line if you get it wrong.

### Clarify
- Do we support seat-level selection (specific seat) or general-admission (just a quantity)?
- Reservation hold — when a user starts checkout, how long is a seat held before release if they don't complete payment?
- Is this single-region or does inventory need to be globally consistent across regions (i.e., can the same seat be bought from two data centers)?
- Waitlist / queue for high-demand on-sales in scope?

### Numbers
- A hot on-sale: 1M users hitting "buy" for a 20K-seat venue within the first 60 seconds — that's the number that matters, not steady-state traffic. Steady-state booking volume is almost irrelevant to the hard part of this design.
- Design explicitly for the spike, not the average — say this out loud, because it reframes the whole prompt away from generic CRUD scaling and toward contention management.

### Architecture
- **Virtual waiting room / queue in front of the booking service** — admits users at a controlled rate so the booking system itself never sees the full 1M-at-once spike; this is the single most important component and is frequently the thing candidates skip straight past.
- Seat inventory as a **finite state machine per seat**: available → held → sold, with a TTL on "held" (e.g., 10 minutes) enforced by an expiry job or TTL-based store entry.
- Reservation service: attempts an atomic conditional transition (available → held) — implemented as a DB row with optimistic locking (version column, `UPDATE ... WHERE status='available' AND version=X`) or a distributed lock keyed by seat_id, not a check-then-write from application code.
- Payment happens *after* the hold succeeds, against a held seat with a TTL — decoupling "reserve" from "pay" is what prevents a slow payment provider from holding up inventory contention.

#### Whiteboard sketch

```text
1M users ─▶ virtual waiting room ─▶ booking svc ─▶ seat rows (SQL)
            admits ~N/sec; queue                   per-seat state machine:
            position randomized at                 available → held → sold
            sale start (NOT                            ▲          │
            first-click-wins)                          └─ TTL 10m ┘
                                                        expiry sweep

atomic claim:  UPDATE seats SET status='held'
               WHERE seat_id=? AND status='available'
               → 1 row: you got it    → 0 rows: pick another seat

payment svc ◀── runs AFTER hold succeeds
                (slow payment provider can't block inventory)
```

### Deep dives
- **The overselling race, named precisely:** two users click the same seat within milliseconds. Whoever's conditional update actually commits first wins; the loser's update affects zero rows and is told immediately to pick another seat. This must be enforced at the data layer with a real atomic operation — never "read seat status in app code, then decide, then write," which has a race window no amount of speed closes.
- **Held-but-abandoned seats:** user gets a hold, closes the tab. A TTL-based expiry (background sweep, or TTL-native store like Redis with an event-driven listener) transitions held → available automatically. State the TTL trade-off: too short frustrates slow payers, too long lets scalpers/bots tie up inventory without buying.
- **Double-spend across regions:** if inventory is replicated across regions for read availability, a *write* to reserve a seat must go through a single authoritative source for that seat (leader-based, sharded by venue/event) — you cannot resolve a seat-reservation conflict with eventual consistency; this is one of the rare sub-systems in a large platform that must be strongly consistent, and you should say explicitly why availability is being sacrificed for correctness here, unlike the notification system's aggregation layer.
- **The queue-fairness problem:** does the waiting room admit strictly FIFO, or can bots/scripts jump ahead by hammering refresh? Address it as a policy (e.g., randomized queue position assigned at fixed sale-start time, not first-request-wins) rather than leaving it implicit.

### Common mistakes
- Defaulting to "just use a message queue for booking requests" without addressing that the underlying seat-state transition still needs to be atomic regardless of how requests arrive.
- Missing the TTL/hold-expiry mechanism entirely, leaving seats permanently stuck once a user abandons checkout.
- Not distinguishing this system's strong-consistency requirement from the eventually-consistent patterns that work fine elsewhere — a candidate who reflexively reaches for "eventual consistency, add a queue" everywhere gets flagged here specifically.

### If they push further
Dynamic pricing / resale marketplace: now inventory state has more transitions (sold → listed for resale → sold again), and you need an audit-safe ledger of ownership transfers — point at the payment-ledger pattern in #12 as the right building block.

---

## 5. Web Crawler

**Cold prompt:** "Design a web crawler that indexes a significant fraction of the internet."

**Why it's asked:** Politeness constraints and duplicate/near-duplicate detection at scale are the real tests; "fetch pages and follow links" is the 10% everyone gets right immediately.

### Clarify
- Scale target — a general-purpose crawler (billions of pages) or a focused crawler (a specific domain/vertical)?
- Freshness requirement — how often must previously-crawled pages be re-crawled?
- Politeness — must we respect robots.txt and per-domain rate limits? (Assume yes.)
- Do we need to extract and index content, or just discover and fetch (indexing is a separate downstream system)?

### Numbers
- Target: 10B pages, re-crawled on average every ~30 days → ~330M fetches/day → ~4K fetches/sec average, higher at peak.
- Average page ~500KB with assets, ~100KB for HTML-only if you're not fetching embedded resources — clarify scope; assume HTML-only for the core crawl.
- URL frontier (the queue of URLs to crawl) at this scale holds billions of entries — this itself is a distributed-queue design problem, not an afterthought.

### Architecture
- **URL frontier**, partitioned by domain (critical — see politeness deep dive), holding pending URLs with priority (based on estimated page importance/PageRank-like signal and staleness).
- **Fetcher workers**, pulling from the frontier, respecting per-domain rate limits and robots.txt (cached per domain, refreshed periodically).
- **Dedup layer**: URL-seen filter (a Bloom filter or similar probabilistic structure, given the cardinality) to avoid re-queuing already-crawled/queued URLs; separately, a **content-hash dedup** to catch near-identical content reachable via different URLs (mirrors, tracking-parameter variants).
- Extracted links feed back into the frontier after normalization (stripping session IDs/tracking params, resolving relative URLs) — normalization is what makes the dedup filter effective at all.
- Fetched content → storage (blob store) → downstream indexing pipeline (out of scope, but say so explicitly rather than trying to design search ranking in the same 45 minutes).

#### Whiteboard sketch

```text
seed URLs ─▶ URL frontier ── sharded BY DOMAIN ← politeness lives here
                 │           priority = importance × staleness
                 ▼
           fetcher workers ×N ◀─▶ robots.txt cache (per domain)
                 │
                 ▼
           content store (blobs) ─▶ downstream indexing (scoped out)
                 │
                 ▼
           link extractor ─▶ URL normalizer ─▶ seen? ──no──▶ frontier
                             (strip tracking    Bloom filter:
                              params, resolve   FP ⇒ page skipped forever —
                              relative URLs)    sized (~0.1%) and accepted
```

### Deep dives
- **Politeness at scale, precisely:** the frontier must guarantee that no single domain gets hammered even though fetcher workers are massively parallel and don't share memory. Fix: partition the frontier *by domain* across queue shards, so all URLs for a given domain are only ever pulled by workers respecting that domain's specific rate limit — this is the same "hot key" containment idea as the celebrity-like problem in aggregation systems, applied to domains instead of users.
- **The URL-seen Bloom filter's false-positive cost:** a Bloom filter can say "already seen" for a URL that wasn't — meaning you silently skip a page forever. Quantify: at 10B entries and a chosen false-positive rate (e.g., 0.1%), that's up to 10M pages silently never crawled. State whether that's acceptable (usually yes, for a system whose value is statistical coverage, not completeness) versus needing an exact set (much more expensive) — this is a designed, named trade-off, not an oversight.
- **Crawler traps:** a site generates infinite unique URLs (e.g., calendar pages linking to "next month" forever). Fix: cap crawl depth per domain, cap total pages per domain per time window, and flag domains whose URL-growth-rate looks anomalous for human review — without this, a single misbehaving site can consume unbounded frontier capacity.
- **Freshness vs. coverage trade-off:** re-crawling everything every 30 days uniformly wastes budget on pages that never change (a static "About Us" page) while under-serving fast-changing pages (a news homepage). Fix: adaptive re-crawl frequency based on observed historical change rate per URL — this is the kind of second-order refinement that separates a "mid" answer from a staff one, and it's worth naming even if you don't have time to fully design it.

### Common mistakes
- Designing dedup with an exact set (e.g., a hash set in a single database) without addressing what that costs at 10B+ URLs, when a probabilistic structure with a stated, defended error rate is the expected answer.
- No domain-based partitioning — proposing a single global frontier queue that can't enforce per-domain politeness at all.
- Trying to also design ranking/search relevance in the same session instead of scoping it out explicitly.

### If they push further
JavaScript-rendered (SPA) sites requiring a headless-browser render step — this is far more expensive per page (seconds vs. milliseconds), so you'd tier the crawl: cheap HTTP fetch first, escalate to rendering only for domains/pages that need it, and say how you'd detect that need (e.g., near-empty HTML body on first fetch).

---

## 6. Ad Click Aggregation / Counting Pipeline

**Cold prompt:** "Design a system to count ad clicks and impressions for a billing and analytics dashboard."

**Why it's asked:** This is the purest test of the exactly-once-counting problem — billing is on the line, so "eventually consistent, roughly right" isn't a free pass here the way it is in social engagement counts.

### Clarify
- What's counted precisely — clicks only, or clicks + impressions + conversions?
- **Is this feeding billing (advertisers pay per click) or just a dashboard?** This single answer determines whether approximate counting is acceptable at all — say explicitly that you're asking because it changes your entire consistency model.
- Real-time dashboard requirement, or is next-day batch reporting acceptable?
- Fraud/bot-click filtering in scope?

### Numbers
- Assume 1M ad clicks/sec platform-wide at peak (large ad network scale) — this is a genuinely enormous ingest rate; state it plainly and let it drive every downstream decision.
- Aggregation granularity: per (ad_id, hour) or finer — the storage/compute cost scales with how granular the aggregation key is, so pick a level and defend it (e.g., per-ad-per-minute for near-real-time dashboards, rolled up to hourly/daily for billing).

### Architecture
- Click events → **append-only log** (Kafka-class), partitioned by ad_id for locality of aggregation.
- **Stream aggregation layer** (e.g., a windowed stream processor) computing counts per (ad_id, time-bucket), with **watermarking** to handle late-arriving events (clicks that arrive after their bucket "closed" due to network delay) rather than silently dropping them.
- Aggregated counts written to a time-series store for the dashboard (approximate-tolerant path) *and*, separately, to a durable, reconciled ledger for billing (exact-required path) — **these are two different consistency tiers off the same stream**, exactly like the notification system's realtime/coalescable split, and naming that parallel explicitly is a strong signal.
- Billing path additionally needs **idempotent, exactly-once-effect processing**: each raw click event has a unique event ID; the billing aggregator checkpoints processed offsets and upserts counts keyed to avoid double-counting on reprocessing/replay.

#### Whiteboard sketch

```text
clicks (1M/sec peak) ─▶ append-only log (partition: ad_id)
                              │
            ┌─────────────────┴──────────────────┐
            ▼ FAST / APPROXIMATE                 ▼ SLOW / EXACT
     stream aggregator                    billing aggregator
     windowed counts,                     checkpointed offsets +
     watermarks for late events           idempotent upsert per event_id
            │                                    │
            ▼                                    ▼
     time-series store ─▶ dashboard       reconciled ledger ─▶ invoices

     the two answers may disagree briefly —
     designed trade-off (fast-approx vs slow-exact), say it out loud
```

### Deep dives
- **Exactly-once counting, done honestly:** true exactly-once *delivery* doesn't exist across a network, but exactly-once *effect* does — via idempotent upserts on a unique event ID, combined with checkpointed stream-processing offsets so a crash-and-replay re-derives the same aggregate rather than double-counting. This is the load-bearing answer for the billing path and you should state it before being asked, since it's the entire point of the prompt.
- **The dashboard-vs-billing numbers can legitimately disagree, and that's fine if you say why:** the real-time dashboard uses an approximate, low-latency windowed count that may miss late-arriving events; the billing ledger uses a delayed, reconciled batch pass over the full log that is authoritative. State this discrepancy as a designed trade-off (fast-but-approximate vs. slow-but-exact) rather than something to be embarrassed about — pretending the two numbers must always match is the wrong instinct.
- **Click fraud / bot filtering:** a burst of clicks from one IP/device in a short window needs to be flagged before it hits billing, not filtered ad-hoc after the fact — this is itself a rate-limiting/anomaly-detection sub-problem (point back at #2's sliding-window counting) sitting in front of the aggregation pipeline.
- **Late and out-of-order events:** mobile clients can buffer clicks offline and send them hours later. A windowed aggregator needs an explicit **allowed lateness** bound — events older than that get routed to a separate reconciliation/correction path rather than silently reopening closed windows indefinitely, which would make "closed" meaningless.

### Common mistakes
- Applying the same approximate-counting tolerance to the billing path as to the dashboard path — the single biggest miss on this prompt, and the one an interviewer is specifically listening for given the word "billing" in the prompt.
- No mechanism for late/out-of-order events — treating the stream as if it arrives in perfect order, which real click traffic never does.
- Not distinguishing "click" from "billable click" (i.e., ignoring fraud filtering as a precursor step to counting at all).

### If they push further
Multi-currency, multi-advertiser billing reconciliation against actual payment records — this is effectively the payment-ledger problem (#12) consuming this pipeline's exact-count output as its input.

---

## 7. News Feed Generation

**Cold prompt:** "Design the news feed for a social network like Twitter or Instagram."

**Why it's asked:** Fan-out-on-write vs. fan-out-on-read is the canonical trade-off test, and the celebrity/hot-user problem forces a hybrid answer — a one-size-fits-all answer is the tell.

### Clarify
- Feed ranking — reverse-chronological, or algorithmically ranked (relevance-scored)? (Assume chronological first to keep scope bounded, note ranking as a follow-on.)
- Follower model — is it symmetric (friends, bounded ~a few hundred) or asymmetric (followers, unbounded, celebrities have tens of millions)? This is the single most important clarifying question on this prompt.
- Read frequency — how often does a user check their feed relative to how often people they follow post?

### Numbers
- 500M DAU, average posts/user/day = 2 → 1B posts/day, ~12K posts/sec average.
- Average follower count ~200, but distribution is extremely skewed — some accounts have 100M+ followers. This skew, not the average, is what makes the design non-trivial.
- Feed reads: users check their feed ~10×/day → ~5B feed reads/day, far exceeding post-writes — this is a read-heavy system with a write-amplification trap hiding inside it.

### Architecture
- **Fan-out-on-write (push model)** for normal users: when a post is created, immediately write it into every follower's precomputed feed (a per-user feed cache/inbox, e.g., a list of post IDs in Redis or a wide-column store). Feed reads become a cheap single lookup.
- **Fan-out-on-read (pull model)** for celebrity/high-follower accounts: don't write to 100M followers' feeds on every post (that's 100M writes for one tweet); instead, merge celebrity posts into a follower's feed *at read time*, querying celebrity-authored posts directly and interleaving with the precomputed feed.
- **Hybrid, stated explicitly:** the follower-count threshold that decides push vs. pull is a designed knob (e.g., accounts above ~10K–100K followers switch to pull), and this hybrid — not either pure model — is the expected staff-level answer.

#### Whiteboard sketch

```text
post created ─▶ author follower count?
                 │
    ≤ threshold  │  PUSH               > threshold │  PULL (celebrity)
                 ▼                                 ▼
    write post_id into each            store once in author timeline
    follower's feed cache              (zero fan-out writes;
    (~200 cheap writes,                 100M-follower post = 1 write)
     driven off a durable log
     → resumable on crash)

read path:  precomputed feed cache
              ⊕ live query: posts from followed celebrities (cached)
              ─▶ merge by time/rank ─▶ render
```

### Deep dives
- **The celebrity fan-out cost, quantified:** a normal user posting to 200 followers costs 200 writes; a celebrity with 100M followers posting the same way costs 100M writes for one action — an unacceptable amplification, and the reason a pure push model doesn't survive contact with real follower distributions. State the number, not just "it doesn't scale."
- **Feed staleness / gap on fan-out failure:** a fan-out-on-write worker crashes partway through writing to 200 followers' feeds — some followers get the post, some don't (a gap). Since this is engagement content, not security-critical, bounded eventual delivery is acceptable — but say so as a decision (tie back to the same gap-vs-duplicate framework used in the notification and chat prompts), and note the fix: the fan-out job is driven off a durable log with resumable offsets, so a retry picks up where it left off rather than needing to be perfect on the first try.
- **Feed read-time merge cost:** for the pull-model (celebrity) side, merging "precomputed feed" + "live query of celebrities you follow" at read time adds latency to every feed load — quantify it (an extra query per followed celebrity, capped by only querying the handful of celebrities a typical user follows) and state the caching strategy for that live query (cache celebrity posts briefly, since read volume vastly exceeds their post volume).
- **New follow / unfollow edge case:** user follows someone new — do they see that account's back-catalog in their feed immediately, or only future posts? This is a product decision with a real infra cost difference (backfilling precomputed feed vs. not) and naming it shows you're thinking about the full lifecycle, not just steady-state.

### Common mistakes
- Proposing pure fan-out-on-write and not independently noticing the celebrity problem before being asked — this prompt is specifically designed to surface whether that failure mode is a reflex or something you need prompted into.
- Proposing pure fan-out-on-read for everyone "to be safe," which needlessly makes the common case (normal users, small follower counts) expensive at read time for no benefit.
- No mention of a threshold/hybrid — presenting it as strictly either/or.

### If they push further
Ranked (non-chronological) feed: now feed generation needs a scoring model consuming engagement signals, and the precomputed-feed data structure needs to hold candidates for re-ranking rather than a final ordered list — point at this as a substantially larger problem (recommendation systems) rather than trying to design it live.

---

## 8. Distributed Key-Value Store

**Cold prompt:** "Design a distributed key-value store that can scale horizontally and tolerate node failures."

**Why it's asked:** This is the foundational-infrastructure prompt — it directly tests CAP-theorem fluency and whether you can reason about consistency levels as a *spectrum* rather than a binary.

### Clarify
- Read/write ratio expected from clients of this store?
- Value size — small (config-style, KB) or large (blob-style, MB+)? Changes replication/storage strategy significantly.
- Consistency requirement from callers — do they need read-your-writes, or is eventual consistency acceptable? (This is the single question that determines the whole design; ask it first.)
- Single-datacenter or multi-region?

### Numbers
- Target: millions of keys, sustained 100K+ ops/sec, sub-10ms p99 latency per operation.
- Assume value sizes in the KB range (config/session/small-object store) unless told otherwise — large blobs push toward object storage, not this pattern.

### Architecture
- **Consistent hashing** for key-to-node placement — chosen specifically because it minimizes data movement when nodes are added/removed (only the keys in the affected hash range move, not the whole keyspace), unlike naive `hash(key) % N`, which reshuffles nearly everything on every membership change.
- **Replication factor N** (typically 3) — each key's data lives on N consecutive nodes on the hash ring.
- **Tunable quorum consistency**: writes require W acknowledgments, reads require R acknowledgments, with W + R > N guaranteeing read-your-writes overlap. State concrete numbers (N=3, W=2, R=2 is the standard balanced choice) and what each extreme means: W=1 is fast-but-risky writes, W=N is slow-but-safe.
- **Conflict resolution:** concurrent writes to the same key from different clients during a partition create conflicting versions. Options: last-write-wins (simple, silently loses data — state this cost plainly) or vector clocks (preserves causality information, pushes conflict resolution to the client/application, more correct but more complex) — name both and pick one with a reason tied to the use case.
- **Failure detection and hinted handoff:** if a node is temporarily down during a write, another node accepts the write on its behalf and hands it off once the original node recovers, so writes aren't blocked by transient node failure.

#### Whiteboard sketch

```text
client ─▶ coordinator (any node)
              │  consistent-hash ring: key → N=3 consecutive nodes
     ┌────────┼────────┐
     ▼        ▼        ▼
   node A   node B   node C
     └── W=2 acks ─────┘  write OK       W+R>N ⇒ read-your-writes
          R=2 on read                    (N=3, W=2, R=2 default)

node down during write ─▶ hinted handoff (neighbor holds, replays later)
replica divergence     ─▶ read repair (on read) + Merkle anti-entropy (bg)
conflict on partition  ─▶ LWW (simple, silently lossy) vs vector clocks
                          (client resolves) — pick one, name the cost
```

### Deep dives
- **CAP, made concrete instead of recited:** during a network partition, do you serve possibly-stale reads (favor availability) or reject requests until partition heals (favor consistency)? Tie the answer to the earlier clarifying question — a session store favors availability with eventual consistency (a stale session read is annoying, not catastrophic); a store backing financial balances favors consistency (see #12). Don't recite "CAP theorem says pick two" as if that's an answer — apply it to *this* system's actual cost of being wrong.
- **Read repair and anti-entropy:** how do replicas that missed a write (e.g., a node was down) catch up? Two mechanisms: read repair (a read that notices a stale replica quietly fixes it during that read) and background anti-entropy processes (e.g., Merkle-tree comparison between replicas to find and reconcile divergence without waiting for a read to trigger it). Name both — read repair alone means rarely-read keys can stay divergent indefinitely.
- **Rebalancing cost when adding a node:** even with consistent hashing, the joining node needs to receive its share of existing data before serving reads correctly — describe this as a bounded, throttled data-transfer process (to avoid saturating network/disk on the cluster) rather than an instantaneous event, and note that reads for keys mid-transfer need a defined behavior (serve from old owner until handoff confirms, not from whichever node answers first).
- **Split-brain on the coordination layer itself:** if you're using a separate service (e.g., Zookeeper-style) for cluster membership, what happens if *it* partitions? This is worth naming even briefly — it shows awareness that "the thing that manages my consistency" also needs a consistency story.

### Common mistakes
- Reciting "CAP theorem, pick two" as a complete answer instead of picking an actual point on the spectrum for this specific use case and defending it with W/R numbers.
- Using naive modulo hashing without addressing the full-reshuffle problem it causes on scale-out/in.
- No conflict-resolution story at all — assuming concurrent writes to the same key just don't happen.

### If they push further
Multi-region replication: now you have cross-region latency in the write path if you want strong consistency, forcing an explicit choice between synchronous cross-region replication (slow, consistent) and asynchronous (fast, eventually consistent, with a defined conflict-resolution and lag-monitoring story) — same fundamental trade-off as the single-region case, one level up.

---

## 9. Video Streaming Platform

**Cold prompt:** "Design a video streaming platform like YouTube."

**Why it's asked:** Splits into two genuinely different sub-problems — ingest/transcoding and playback/delivery — and tests whether you notice that split instead of designing one generic pipeline.

### Clarify
- Live streaming in scope, or video-on-demand (upload-then-watch) only? (Assume VOD unless told otherwise — live is a materially different latency regime.)
- Upload volume vs. watch volume — confirm the expected read:write skew (almost certainly extreme, watches vastly exceed uploads).
- Multiple resolutions/adaptive bitrate required?
- Global audience, implying CDN necessity?

### Numbers
- Assume 500 hours of video uploaded per minute (YouTube-scale reference point), and watch traffic orders of magnitude higher than upload — state the skew explicitly, since it justifies architecting upload and playback as separate systems with separate scaling stories.
- Storage: raw + multiple transcoded resolutions per video roughly doubles-to-triples total storage vs. source alone — worth a rough number, not precision.

### Architecture
- **Upload path:** client uploads raw video (often chunked, resumable) → object storage (blob store) for the raw file → **async transcoding pipeline** (a job queue triggers workers that produce multiple resolutions/bitrates + thumbnail extraction) → transcoded outputs pushed to CDN origin storage.
- **Playback path:** client requests video → metadata service resolves available renditions → **CDN edge delivery** of video segments (this is the actual scaling answer for playback — the origin infrastructure never serves the bulk of watch traffic directly).
- **Adaptive bitrate streaming** (HLS/DASH-style): video is chunked into small segments per resolution; the client player monitors its own network throughput and switches resolution segment-by-segment — this decision genuinely lives at the client, not the server, and saying so avoids over-designing server-side "quality selection" logic that doesn't need to exist.
- Metadata (title, description, view counts, comments) lives in a separate, much smaller-scale service from the video bytes themselves — don't conflate the two into one data store.

#### Whiteboard sketch

```text
UPLOAD (rare, heavy)
creator ─▶ chunked resumable upload ─▶ raw blob store
           (durable per-chunk               │ job queue
            progress record)                ▼
                                  transcode workers ×N
                                  (multi-res + thumbnails,
                                   retryable / checkpointed)
                                            │
                                            ▼
                                     CDN origin storage

PLAYBACK (massive, read)
viewer ─▶ metadata svc ─▶ CDN edge serves segments
          (renditions)     client picks bitrate per segment (ABR =
                           client-side decision, not server logic)
                           viral cold video ─▶ request coalescing at
                           edge (1 origin fetch per missing segment)
```

### Deep dives
- **Upload durability under network failure:** a multi-GB upload from a mobile connection will drop mid-transfer. Fix: **resumable/chunked upload** — client and server track which chunks have landed, and a resume picks up from the last confirmed chunk rather than restarting; this needs a durable per-upload progress record, not just client-side retry logic.
- **Transcoding as an async, failure-tolerant pipeline:** transcoding a long video can take minutes; don't make the user's upload request block on it. The upload triggers a job onto a queue; a worker pool consumes it; if a worker crashes mid-transcode, the job must be resumable/retryable from a checkpoint (or cheaply restartable) rather than silently lost — same at-least-once-plus-idempotent-completion pattern as everywhere else in this deck, applied to compute jobs instead of writes.
- **The "view count" is a counting problem, not a video problem:** high-volume view/like counters on hot videos hit the exact same hot-key and approximate-vs-exact tension as the ad-click-aggregation prompt (#6) — say so explicitly rather than re-deriving it from scratch, and note view counts tolerate approximation (unlike ad billing) since nothing is charged against them.
- **CDN cache-miss storm on a new viral video:** a brand-new video suddenly goes viral before it's warmed across CDN edge nodes — many edges simultaneously miss and hit origin at once (a thundering herd). Mitigate with request coalescing at the edge (only one origin fetch per missing segment even under concurrent requester load) and pre-warming popular new uploads proactively based on early velocity signals.

### Common mistakes
- Designing one monolithic pipeline for both upload and playback instead of recognizing they have entirely different scaling profiles and failure modes.
- Trying to solve adaptive bitrate switching as a server-side decision instead of correctly placing it at the client.
- No story for transcoding failure/retry — treating it as an instant, always-succeeds step.

### If they push further
Live streaming: now latency requirements invert everything — you can't pre-transcode into multiple resolutions ahead of time, chunking must happen in near-real-time, and CDN delivery needs low-latency variants (e.g., smaller segment windows) — flag this as a different design, not a small delta on VOD.

---

## 10. Search Autocomplete / Typeahead

**Cold prompt:** "Design the search-autocomplete feature for a search engine — suggestions as the user types."

**Why it's asked:** Tests latency-budget discipline (this sits on every keystroke) and the trade-off between freshness of suggestions and serving speed.

### Clarify
- Personalized suggestions (based on user history) or global/trending-based only? (Assume global first, note personalization as a follow-on.)
- Latency budget — this is a per-keystroke UI feature, so confirm the target is very tight (tens of milliseconds), since it drives every downstream choice.
- How fresh must trending suggestions be — real-time, or is an hourly/daily-refreshed model acceptable?

### Numbers
- Assume the platform handles ~5B searches/day → autocomplete is queried on *every keystroke*, not every search — for an average 20-character query, that's up to 20× the search volume, so ~100B+ autocomplete requests/day, ~1.2M/sec average.
- This number alone should tell you the serving path must be extremely cheap per request — nothing resembling a full-text search or a database join can sit on this path.

### Architecture
- **Precomputed trie (or trie-like prefix index)** mapping prefixes to their top-K most likely completions, built offline/periodically from a query-log frequency analysis, and served from an **in-memory** structure — the entire point of this design is moving all the expensive computation to an offline batch job so the online path is a cheap prefix lookup.
- Query-log aggregation pipeline (offline, batch or periodic): counts query frequency, ranks completions per prefix, rebuilds the trie/index on a cadence (e.g., every few hours), and pushes the new version out to serving nodes.
- Serving layer: trie sharded by prefix range across multiple in-memory nodes if the full structure doesn't fit one machine's memory, fronted by the standard load-balanced stateless-service pattern.

#### Whiteboard sketch

```text
OFFLINE (rebuild every few hours)     ONLINE (every keystroke, <50ms)
query logs ─▶ frequency ─▶ trie:      keystroke ─▶ LB ─▶ in-memory trie
              analysis     prefix →                     shard (by prefix
                 │         top-K                        range)
                 ▼                                         │
          versioned index push ───────────────────────────┘
          + tiny "trending now" overlay
            (minutes-fresh, checked first)

RULE: the online path is a lookup and nothing else —
      no DB query, no ranking call, no network hop to a scorer
```

### Deep dives
- **Latency budget forces the "no live computation" decision, stated explicitly:** at a sub-50ms budget with 1M+ QPS, there is no room for a database query, a ranking model inference call, or a network hop to a separate scoring service on the hot path — everything expensive must have already happened in the offline pipeline, and the online path is *purely* a lookup. Say this as the organizing principle before describing the trie, not after.
- **Freshness vs. serving-cost trade-off:** a fully real-time-updated trie (reflecting a breaking-news term trending in the last minute) is expensive to maintain continuously; a periodically-rebuilt trie (hourly) is cheap but stale for fast-moving trends. Real systems often split this: a slow-refreshing base trie plus a small, separately-maintained "trending now" overlay checked first for a narrow set of currently-spiking terms — name this hybrid rather than picking one extreme.
- **Trie size at scale:** storing top-K completions at *every prefix node* (not just leaf/full-query nodes) multiplies memory substantially — quantify roughly (if the trie has tens of millions of nodes and each stores even a handful of ranked completions with metadata, that's real gigabytes) and note the standard mitigation: cap K aggressively (e.g., top 5-10 per prefix) since users never scroll past the first handful of suggestions anyway — the product requirement (a UI list showing 5-10 items) directly bounds the storage cost, which is worth pointing out as a case where the product constraint *is* the scaling solution.
- **Handling the long tail / rare prefixes:** most prefixes are queried rarely, and precomputing rich suggestions for every possible prefix combinatorially explodes. Fix: only materialize prefixes observed in actual query logs above some frequency floor, falling back to a cheap generic mechanism (or no suggestions) for prefixes never seen before — don't try to precompute for the full combinatorial space of all possible character sequences.

### Common mistakes
- Proposing a live database query or live ranking computation per keystroke without confronting the latency-budget math that rules it out.
- Storing full ranked lists at every trie node without noticing the memory cost, or without capping K.
- No refresh/freshness story — treating the index as either fully static or magically always up to date with no mechanism named.

### If they push further
Personalization (blend global trending with the individual user's own search history) — this adds a per-user signal that must be merged with the global result *within the same latency budget*, meaning the personalization data itself also needs to be precomputed/cached per user rather than computed live, for the same reason the base trie is precomputed.

---

## 11. Distributed Job Scheduler

**Cold prompt:** "Design a distributed job scheduler that runs millions of scheduled and recurring tasks reliably — like a distributed cron."

**Why it's asked:** Forces you to confront exactly-once *execution* (not just delivery) under leader failure — genuinely one of the hardest correctness problems on this list.

### Clarify
- One-time scheduled jobs, recurring (cron-style), or both?
- What does "reliably" mean here — at-least-once execution (job might run twice, must be safe to retry) or does the caller need a guarantee it runs exactly once no matter what?
- Job execution duration — short tasks (seconds) or long-running (hours)? Changes the failure-detection and retry story substantially.
- Scale — how many distinct scheduled jobs, and how many need to fire concurrently at a busy moment (e.g., everything scheduled for midnight UTC)?

### Numbers
- Assume 10M distinct scheduled jobs, with a typical peak (e.g., top-of-hour, midnight) causing a spike where a large fraction fire within the same minute — the *peak concurrent trigger rate*, not the average job count, is the number that actually stresses the system, similar in spirit to the ticket-booking on-sale spike.
- Assume most jobs are short (seconds) but a non-trivial tail runs for hours — design for both.

### Architecture
- **Job store**: durable database of job definitions (schedule, next-run-time, payload/target, retry policy), partitioned/sharded by a scheduling key (e.g., time-bucket or job-ID hash) so no single node owns the whole job space.
- **Scheduler/dispatcher nodes**: poll for jobs whose next-run-time has arrived, claiming them via an atomic conditional update (same optimistic-locking pattern as the ticket-booking seat-hold: `UPDATE jobs SET status='claimed', owner=X WHERE id=Y AND status='pending'`) — this atomic claim is what prevents two scheduler nodes from double-triggering the same job.
- **Worker pool**: executes claimed jobs, reports success/failure back to the job store, which updates next-run-time for recurring jobs or marks one-time jobs complete.
- **Lease/heartbeat mechanism**: a claimed-but-not-completed job holds a time-bound lease; if the worker dies mid-execution and the lease expires without a completion report, the job is released back to pending for another worker to claim — this is the mechanism that turns "at-least-once" into a recoverable guarantee rather than a job silently vanishing on worker death.

#### Whiteboard sketch

```text
job store (sharded by time-bucket / job-id hash)
  rows: schedule, next_run, payload, status, retry policy
        │ poll due jobs
        ▼
dispatchers ×N ── atomic claim ─▶ UPDATE ... SET status='claimed'
        │                         WHERE id=? AND status='pending'
        │                         (0 rows ⇒ another dispatcher won)
        ▼
workers ×N ── heartbeat: renew lease while running ─▶ lease store
   │                          │
   │ success                  │ lease expires (worker died mid-job)
   ▼                          ▼
mark done /              job → 'pending' again ─▶ re-claimed
set next_run             ⇒ at-least-once ⇒ jobs MUST be idempotent

midnight spike: jitter non-exact jobs + shard so no hot partition
```

### Deep dives
- **Exactly-once execution is the crux, and the honest answer is "we get at-least-once execution plus idempotent jobs":** true exactly-once execution across a distributed system with worker crashes is not achievable in general — a worker can complete a job and crash *before* reporting success, causing the lease to expire and the job to be re-claimed and re-run. The correct staff-level answer is: guarantee at-least-once triggering via the lease mechanism, and push the exactly-once *effect* requirement onto the job itself being idempotent (e.g., a job that "charges a customer" must use an idempotency key downstream, same pattern as #12) — state this trade-off before being asked, since it's the entire point of the prompt.
- **The thundering-herd trigger spike:** 500K jobs all scheduled for exactly midnight UTC. If dispatcher nodes all poll and try to claim jobs at once, you get contention on the job store itself. Mitigate with jittered scheduling where reasonable (spread jobs that don't have a hard-exact-time requirement across a small window) and by partitioning the job store so the midnight spike is distributed across many shards rather than hitting one hot partition — tie this explicitly back to the same hot-partition containment idea used in the notification-aggregation and web-crawler prompts.
- **Lease duration trade-off:** too short, and a slow-but-healthy job gets prematurely re-claimed and double-executed while still running (visible if the job wasn't idempotent); too long, and a genuinely dead worker's job sits stuck for a long time before recovery. State the mitigation for long-running jobs specifically: workers periodically **renew** their lease while still actively working, rather than holding one fixed lease for the whole duration — this is the standard fix and worth naming explicitly since "just pick a long timeout" is the common wrong answer.
- **Clock/scheduling drift across a fleet:** dispatcher nodes must agree on "what time is it" closely enough that a job scheduled for 12:00:00 doesn't fire at wildly different times depending on which node polls it — rely on a synchronized time source (NTP) and build in tolerance rather than assuming perfect clock agreement.

### Common mistakes
- Claiming "exactly-once execution" as an achievable guarantee without naming idempotency as the actual mechanism that makes it safe in practice.
- No heartbeat/lease-renewal story for long-running jobs, leaving a single fixed timeout that's wrong for either short or long jobs.
- Missing the midnight/top-of-hour thundering-herd problem entirely — designing only for smoothly distributed job trigger times.

### If they push further
Job dependencies/DAGs (job B only runs after job A succeeds) — this adds a coordination layer tracking partial completion state across a graph, and the interesting failure mode becomes what happens when A succeeds, is marked complete, but the "trigger B" step itself fails — another instance of the same at-least-once-plus-idempotent pattern, one level up in a dependency graph instead of a single job.

---

## 12. Payment Processing System

**Cold prompt:** "Design a payment processing system that handles transactions between users and merchants."

**Why it's asked:** The one system on this list where "approximately correct" is never an acceptable answer for the core ledger — tests whether you know the difference between systems that can be eventually consistent and systems that cannot, and why.

### Clarify
- Scope — are we processing the payment (talking to card networks/banks) or just recording and reconciling transactions on top of a payment processor? (Assume the latter — building a ledger/transaction system on top of an external processor — since building actual card-network integration is out of interview scope; state this assumption explicitly.)
- Currency — single currency or multi-currency with conversion?
- Refunds and disputes in scope?
- Idempotency requirement from calling clients (e.g., a mobile client retries a payment request after a timeout) — assume yes, this is central to the prompt.

### Numbers
- Assume 10M transactions/day → ~115/sec average, spiky around peak shopping periods (state that retail-style peak-to-average ratios can be 5-10×, unlike more uniform traffic patterns).
- Every single transaction must be accounted for — zero tolerance for silent loss or silent duplication, unlike every other system in this deck. Say this explicitly: it's the one place where "acceptable approximation" is the wrong instinct to reach for at all.

### Architecture
- **Idempotency at the API boundary:** every payment request carries a client-generated idempotency key; the server checks a durable idempotency-key store *before* processing — if the key's been seen, return the original result rather than reprocessing, closing the classic "client retried after a timeout, did the charge actually happen?" ambiguity at the source rather than downstream.
- **Double-entry ledger** as the core data model: every transaction is recorded as at least two balanced entries (a debit and a credit) rather than a single mutable "balance" field — this makes the system's correctness auditable and mechanically enforceable (entries must always sum to zero) rather than trusted on faith.
- **State machine per transaction**: initiated → authorized → captured → settled (with failed/refunded branches), persisted durably at each transition, so a transaction's exact status is always recoverable rather than inferred from scattered side effects.
- **Async settlement / reconciliation job**: a separate batch process periodically compares internal ledger state against the external payment processor's records and flags discrepancies — you do not rely solely on the synchronous request path to guarantee correctness; reconciliation is the safety net that catches whatever the synchronous path missed.

#### Whiteboard sketch

```text
client ─ idempotency key ─▶ payment API
                             │ ONE atomic txn: record key +
                             │ state='processing' ← closes retry race
                             ▼
              transaction state machine (durable per step)
              initiated → authorized → captured → settled
                             │              (failed / refunded
                             ▼               are branches, not edits)
                    external processor
                             │
                             ▼
        double-entry ledger (append-only; debits ≡ credits)
                             ▲
   reconciliation job ───────┘  batch-diff vs processor records —
                                catches "money moved, we crashed
                                before recording it"

retry, same key ─▶ key found in 'processing'/'done'
                   ─▶ return original result — NEVER re-charge
```

### Deep dives
- **Idempotency across the actual failure case, made concrete:** client sends a charge request, the server processes it and calls the external payment processor, the processor succeeds, but the response back to your server times out before your server can respond to the client. Client retries with the same idempotency key. Without careful handling, "check idempotency key, not found, process again" double-charges the customer. Fix: the idempotency-key record must be written *atomically together with* (or immediately before, in the same transaction as) the state transition to "processing," and a retry that finds a key already in "processing" or "completed" state must not re-call the external processor — it should either wait/poll for the in-flight result or return the already-completed result. This is the single most important mechanism in the whole design and should be described precisely, not gestured at.
- **Why eventual consistency is the wrong default here, argued rather than assumed:** contrast explicitly with the notification/social systems in this deck — a duplicated "like" notification is a minor annoyance; a duplicated $500 charge is a real-world harm with legal and trust consequences. The core ledger write must be a strongly consistent, ACID transaction (a relational database with real transaction guarantees is usually the right tool here, not a wide-column eventually-consistent store) — this is a case where reaching for the "distributed, eventually consistent, horizontally scaled" toolkit by reflex is actively the wrong instinct, and noticing that is a strong staff-level signal.
- **Partial failure mid-transaction:** payment is captured by the external processor, but your server crashes before recording that success in your own ledger. Now the money moved but your system doesn't know it. Fix: the reconciliation job specifically exists to catch this class of failure — it compares your ledger's "pending/unknown" transactions against the processor's actual record of what settled, and resolves the discrepancy (crediting your ledger to match reality) rather than assuming your own database is always the source of truth for what actually happened with the money.
- **Refunds are not "negative payments," architecturally:** a refund should reference the original transaction and be its own ledger entry (not a mutation of the original), preserving a complete, append-only audit trail — this matters for disputes and regulatory/audit requirements, and stating it shows awareness that financial systems are optimized for auditability, not just correctness-at-a-point-in-time.

### Common mistakes
- Reaching for eventually-consistent, horizontally-scaled infrastructure by default (the pattern used successfully everywhere else in this deck) without recognizing this is the one prompt where that instinct is wrong.
- Idempotency handled as an afterthought ("just check if we've seen this ID before") without describing the atomicity of checking-and-recording as a single operation.
- Modeling account balance as a single mutable field instead of a double-entry ledger, making the system unauditable and prone to race conditions on concurrent balance updates.
- No reconciliation process — assuming the synchronous request/response path is always sufficient to guarantee correctness, with no safety net for partial failures.

### If they push further
Multi-currency with real-time FX conversion: now each ledger entry needs a recorded exchange rate at time of transaction (for audit and dispute purposes, the rate used must be reproducible after the fact, not re-fetched live when someone disputes a charge months later) — another instance of "the ledger must be able to explain itself" as the organizing constraint.

---

## Cross-Cutting Patterns (the actual thing being tested across all 12)

If you strip the domain flavor off every prompt above, the same handful of decisions repeat. Drill *these*, not the twelve systems individually:

| Pattern | Shows up in |
|---|---|
| At-least-once delivery + idempotent effect ≠ exactly-once, and that distinction must be stated explicitly | Notification system, Chat (#3), Ad clicks (#6), Job scheduler (#11), Payments (#12) |
| Atomic conditional write (optimistic lock / compare-and-swap) prevents a specific named race, vs. check-then-write in app code which doesn't | Ticket booking (#4), Job scheduler (#11), URL shortener (#1) |
| Hot-key/hot-partition containment by widening the key or sharding the hot entity | Notification system (celebrity), News feed (#7), Web crawler (#5, per-domain), Job scheduler (#11, midnight spike) |
| Approximate/eventually-consistent is fine *here* but not *there* — and you must say which and why | Ad clicks (#6) dashboard vs. billing; KV store (#8) session vs. financial use; Payments (#12) vs. everything else |
| Push (write-time) vs. pull (read-time) fan-out, with a stated threshold for switching | News feed (#7), Chat (#3, group size), Notification aggregation |
| Two-tier routing: a fast/lossy lane and a slow/exact lane fed by the same source | Ad clicks (#6), Notification realtime-vs-coalescable split, Video view counts (#9) |
| Gap vs. duplicate: for any component that can fail mid-operation, state which failure mode you accept and why | Every single one — this is the universal reflex question |

The fastest way to raise your ceiling isn't more systems — it's running this table's seven rows against five *new* unfamiliar prompts (not on this list) until naming them is automatic before the interviewer has to ask.
