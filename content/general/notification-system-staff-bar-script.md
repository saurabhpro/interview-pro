# Notification system — annotated practice script

**How to use this:** This is *one* strong path through a notification-system prompt, not the only valid design. The choices (Kafka, store-then-push, first-fire-then-coalesce) have defensible alternatives. Drill the **shape** of the answers: question → number → decision → cost → failure mode. Read the YOU lines aloud with a timer; the `[COACH]` notes explain why each move matters.

---

## Pacing map (45-minute interview)

| Time | Phase | Your job |
|---|---|---|
| 0:00–1:00 | Frame the clock | State your time budget out loud |
| 1:00–7:00 | Requirements discovery | ~10 closed-ended questions, assumptions stated-then-offered |
| 7:00–12:00 | Numbers | Envelope math aloud; **derive the aggregation layer from the ingest/delivery gap** |
| 12:00–18:00 | Architecture skeleton | Boxes with one-line responsibilities + the consistency mechanism |
| 18:00–38:00 | Deep dives under fire | Aggregation, delivery semantics, dedup, hot keys, ops reality |
| 38:00–43:00 | Failure modes you raise unprompted | Gap-vs-duplicate, crash mid-operation, "designed vs validated" |
| 43:00–45:00 | Wrap | Past tense, trade-offs chosen, open risks named |

---

## THE SCRIPT

**INTERVIEWER:** Design the notification system for a large consumer app. Board's yours.

**YOU:** Before I touch requirements, here's how I want to spend the time: five minutes on scope and scale, five on math and the data model, twenty on architecture with deep dives wherever you want to push, and I'll hold the last few minutes for failure modes and wrap-up. If I'm burning time somewhere, redirect me.

> **[COACH — 20 seconds, no more.]** This shows ownership of the clock and invites useful steering before time runs out.

**YOU:** First question — what class of app? Social, commerce, media? I'll design for Instagram-class social unless you say otherwise, since that's the hardest general case.

**INTERVIEWER:** Instagram-class. Social graph, feed, DMs, likes, follows.

**YOU:** Channels: am I building push plus an in-app notification center, or do I own email and SMS too?

**INTERVIEWER:** Push and in-app. Email and SMS are another team's problem.

**YOU:** Who publishes into this thing? Is it a platform — every product team sends events through me — or a single product surface?

> **[COACH]** This question surfaces whether the system is a greenfield platform whose customers are product teams.

**INTERVIEWER:** Platform. Today it's point-to-point chaos, every team hitting APNs themselves. You're building the thing that kills that.

**YOU:** That changes my API contract. Do teams send raw *events* and I decide what's notification-worthy, or fully-formed notifications?

**INTERVIEWER:** Raw events, mostly.

**YOU:** Preferences: per-category mute, I assume. Are any categories non-optional — security, legal?

**INTERVIEWER:** Yes. New login, password change. Legal treats delivery as mandatory.

**YOU:** Then I'm carving those into a separate tier right now, with different loss and latency budgets — I'll design to that split. Next: does the in-app center need to be *consistent* with push? If a push arrives, must the item exist in the center when they open the app?

**INTERVIEWER:** Yes. Hard product requirement.

> **[COACH]** Ask about consistency explicitly. When a requirement has a mechanism-shaped hole in it, identify the hole before selecting infrastructure.

**YOU:** Retention on the center?

**INTERVIEWER:** 30 days.

**YOU:** Numbers. What's the DAU, the daily delivery volume, and the peak *event* rate into the system? Those last two are different numbers and I need both.

**INTERVIEWER:** 500M DAU. About 10B deliveries a day. Ingest firehose peaks around 2M events/sec.

> **[COACH]** Ask for scale instead of negotiating it down. Treat ingest and delivery as separate numbers; their difference may reveal a missing aggregation stage.

**YOU:** Last one before math. SLOs — let me propose the SLIs and you correct the targets: p99 under 5 seconds event-to-push for the time-sensitive tier (DMs, security), 99.9%+ eventual delivery for mandatory categories, p99 200ms center reads.

**INTERVIEWER:** Take your proposals.

> **[COACH]** An SLO without an SLI is a decoration. Propose the load-bearing measurements, then let the interviewer adjust the targets. **Requirements phase total: ~6 minutes, ~10 questions, all closed-ended.**

---

### Phase 2 — Numbers (say every number out loud)

**YOU:** Math, out loud. 10B deliveries over 86,400 seconds is roughly 116K per second average. Peak at 3× is call it 350K/sec of *deliveries*. But you told me ingest peaks at 2M events/sec. Those two numbers differ by almost an order of magnitude — and that gap is the most important fact on this board. It means most events do **not** become notifications one-to-one. Something in the middle collapses them: three million likes on a high-fanout post has to become one artifact that says "A recent follower and 2.9M others liked your photo." So aggregation isn't a UX nicety — it's a first-class, load-bearing component, and I'm going to design it as one.

> **[COACH — this is the key design beat.]** Derive the aggregation layer from the numbers before drawing boxes. Drill this explanation until it fits in 60 seconds.

**YOU:** Storage — and I want to price the *artifact*, not the event. If aggregation collapses that firehose into, say, ~2B center items a day at ~1KB each with payload and indexes, that's ~2TB/day, ~60TB for the 30-day window, under 200TB with 3× replication. Very manageable. The raw event log is a separate thing — log retention measured in days, not thirty.

> **[COACH]** Price the stored notification artifact, not every source event. Finding the aggregation boundary changes both the architecture and the capacity estimate.

**YOU:** Reads. 500M opens a day is ~6K/sec average, ~18–20K/sec peak of *full center reads* — but the badge count gets hit on essentially every open and every push receipt, so the true read surface is in the hundreds of thousands of QPS on a tiny query: "unread count for user X." So this system is **read-heavy at the serving layer and write-heavy at ingest**. Two different workloads glued together — I'm not going to pick one database and pretend it serves both.

> **[COACH]** Derive the read/write ratio from user behaviour rather than inventing it. The useful conclusion is a workload split, not a database name.

---

### Phase 3 — Architecture skeleton

**INTERVIEWER:** Fine. Boxes.

**YOU:** Left to right, one line of responsibility each.

One — ingest API in front of a partitioned log, Kafka-class, keyed by recipient so each user's events arrive in order.

Two — classifier and preference filter: assigns category, drops muted events, and splits traffic into two lanes **right here**: a *realtime* lane (DMs, mentions, security — never windowed) and a *coalescable* lane (likes, follows, recommendations). The tier split we agreed on in requirements becomes a physical routing decision at this box.

Three — the aggregation service on the coalescable lane. I'll go deep there in a second.

Four — the notification store, source of truth for the 30-day center. The write is an **idempotent upsert keyed by a deterministic notification ID**. That one sentence is doing enormous work: it makes the store my *authoritative* dedup point, which means everything upstream of it is allowed to be at-least-once. I'll lean on that repeatedly.

Five — dispatch workers reading committed store rows, sending to APNs and FCM, owning token lifecycle — registration, invalidation on feedback, retry policy.

Six — the read path: center API over the store, plus a counter cache for badge counts, reconciled periodically rather than transactionally exact.

And the consistency requirement gets a **mechanism, not a wish: write to the store, commit, then dispatch the push.** The push is always the laggard, so the center can never be behind the push. The cost: a serial hop adds tens of milliseconds to the push path. I pay it happily, because my time-sensitive SLO is seconds, not milliseconds — and I get the product's hard requirement for free.

> **[COACH]** Trade-off articulation in its complete form: *mechanism → cost → why the cost is acceptable against the stated requirement*. "Semi-sync replication with quorum" contains none of those three parts.

**INTERVIEWER:** What's the store? And don't say a brand name and hope.

**YOU:** Honest version: I haven't operated a wide-column store at this scale, so let me reason from access patterns instead of name-dropping. I need: high sustained writes keyed by user, range reads of "user X's last 30 days" in tens of milliseconds, TTL-based expiry, and tolerance for read-heavy mutation — users marking things read. A partitioned row store keyed (user, time-bucket) fits — Cassandra/Scylla-class or heavily sharded Postgres both plausibly work. If I picked Cassandra I'd verify one specific risk before committing: tombstone accumulation on read-and-mark-read partitions, because that's the known failure mode for exactly my access pattern. That's a benchmark I'd run in week one, not a fact I'll assert in this room.

> **[COACH]** When uncertain, name the access pattern, candidate solutions, and the specific risk to verify with a benchmark or failure test.

---

### Phase 4 — Deep dives under fire

**INTERVIEWER:** Aggregation. Key, flush policy. Don't wave at it.

**YOU:** The key is **(recipient, object, event-type)** — likes on post A group separately from likes on post B. Plus a secondary collapse on **(recipient, actor, event-type)**, so one person liking fifty of your photos folds into "A liked 50 of your photos" — one artifact, not fifty pushes.

Flush policy: **first event fires immediately, then coalesce.** A normal user's single like this week shouldn't sit in a window — they get the push instantly. Subsequent events on the same key coalesce into a rolling window, flushing on count-or-time-whichever-first, and digest *updates* are rate-limited per (user, category) — the celebrity gets "and 12K others" a handful of times a day, not at every window boundary. One policy, both extremes served. That's why first-fire-then-coalesce beats a fixed window: a fixed window delays the lonely like for no benefit *and* spams the hot key at every boundary.

> **[COACH]** Defend the flush policy against both a high-fanout account and a low-activity account. A policy answer needs a mechanism, its cost, and behaviour at the extremes.

**INTERVIEWER:** Your aggregation node dies mid-window holding 12,847 pending likes. Gap or duplicate?

**YOU:** Neither reaches the user — and internally, I choose duplicates. Here's the machinery: window state is just a *materialization of the log*. The consumer commits offsets **only after a flush lands in the store**. So a crash mid-window means offsets were never committed — a replacement consumer replays from the last offset, rebuilds the window, flushes again. If the previous flush actually made it before the crash, the idempotent upsert absorbs the second one — same deterministic ID, same row. At-least-once from log to store; exactly-once *effect* at the store.

Could I instead accept bounded sub-window loss for engagement categories? Yes, and I'd argue it if replay were expensive — but it isn't, because the log is the source of truth and window state is disposable cache. So I don't need the concession, and security-tier events never touch this lane anyway.

> **[COACH]** A complete answer must choose the tolerated failure mode and connect it to a recovery mechanism. Drill “gap or duplicate — duplicates, dedup at the store” until it is a reflex stated **before** prompting. Notice the shape: choose a side, name the mechanism, name the fallback considered, and explain why it is unnecessary here.

**INTERVIEWER:** Same push arrives twice, thirty seconds apart. Where was it born and what stops it?

**YOU:** Three birthplaces. One: producer retry into the log. Two: dispatch worker crashes *after* the APNs send but *before* recording it. Three: DLQ replay during an incident.

Births one and three die at the store — same deterministic ID, idempotent upsert, one artifact, one dispatch. Birth two is the nasty one, because it happens *downstream* of my source of truth. For that, the dispatch layer keeps a **send ledger**: notification-ID → sent status, checked before send, written after. Sizing, since numbers are owed: ~2B artifacts/day at ~64 bytes per entry with a 24-hour TTL is on the order of 130GB — a boring sharded KV tier.

The check-then-send race can still lose — worker checks, sends, dies before writing. So worst case, one duplicate push escapes per crash, and the *client* suppresses re-display with a local seen-ID cache. And I want to be precise about that layer's status: **client-side dedup is cosmetic, never authoritative.** The OS doesn't guarantee my code runs on receipt — iOS can display before the extension executes — and the cache is per-device, so a phone and an iPad don't share it. It's a last line that catches the residue, not a place correctness lives.

Now the inverse — the **gap**: ledger says nothing, APNs send silently failed, or the worker died before the send. Commit-after-send ordering means the store row stays in "pending," and a **reconciliation sweep re-drives anything pending past a threshold**. For the mandatory security tier specifically: no TTL discard, ever — escalating retries and a delivery-lag alarm. That tier fails *loudly*, not silently.

> **[COACH]** Cover both duplicates and gaps, each with a birth point, a mechanism, and a named residual risk. At-least-once delivery means duplicates can happen; explain where deduplication lives and what it costs.

**INTERVIEWER:** You keep saying reconciliation. How do you *know* delivery works? Not how it's designed — how do you know?

**YOU:** Those are different questions, so let me answer them separately. Designed: everything I just described. **Known — measured, not asserted:** per-(user, category) sequence numbers on artifacts, so gaps are *detectable* rather than theoretically absent. A dedup-hit-rate metric at the ledger — if it climbs, something upstream is retry-storming and I find out from a graph, not a user. Synthetic canary notifications end-to-end every minute per region, alerting on lag. And before GA, a replay test: push a full day of production traffic through staging and diff artifact counts against expected.

If you ask me "have you tested the crash-mid-window recovery path" — honest answer today: no. It's designed, not validated. The validation is a chaos drill that kills an aggregation shard mid-window and asserts two things: zero user-visible loss, zero duplicate artifacts. That drill runs before launch, not after the first incident.

> **[COACH]** Do not conflate “how it would work” with “it has been verified.” Make the designed-versus-validated distinction explicitly and name the specific test that would supply evidence.

**INTERVIEWER:** Hot partition. The celebrity again.

**YOU:** Keying the log by recipient makes him a hot key at ingest — one partition eats 800 events/sec while its neighbors idle. Mitigations in preference order: the classifier can shard a *hot recipient's* coalescable events across sub-partitions — safe, because aggregation is counting, and counting is commutative; merge at flush. The store write is one artifact regardless of how many sub-windows fed it, and dispatch is one push. So the hot spot is contained to the log and window state, both horizontally scalable, and it never amplifies downstream.

What I'm deliberately *not* doing: per-follower fan-out writes for a high-fanout account — 200M rows for one event. Those notifications are a fan-out-on-read or hybrid decision, and that's a separate deep dive if needed.

> **[COACH]** Ending a deep dive by *naming the adjacent problem you're consciously deferring* shows the map is bigger than the territory you've covered — and hands the interviewer a steering choice instead of an ambush.

---

### Phase 5 — Wrap (60 seconds, past tense)

**INTERVIEWER:** Two minutes. Wrap it.

**YOU:** What I built: a notification *platform* — product teams publish raw events, they don't touch APNs. Two lanes split at classification: realtime and coalescable. The aggregation layer was derived from the numbers — 2M/sec in, 350K/sec out means most events fold into digests — with first-fire-then-coalesce flushing and log-replay recovery. One store as source of truth, doing idempotent upserts — that's the single authoritative dedup point, which lets everything upstream be at-least-once. Store-then-push ordering buys the center/push consistency requirement for tens of milliseconds of push latency.

Trade-offs I chose, with eyes open: duplicates over gaps, deduped at the store. Slight push latency for consistency. Approximate badge counts, reconciled rather than exact. Sub-window replay cost accepted because the log is cheap to re-read.

Open risks, in the order I'd attack them: the send-ledger race under APNs throttling, hot-key behavior at true celebrity scale, and the chaos drill I named — and I want to be clear that none of this is *validated* until that drill passes.

> **[COACH]** The wrap names **unresolved risk, unprompted**. Ending on what's untested reads as strength at this level, not weakness — it's the "what would you attack first" answer before it's asked.

---

## PHRASE BANK — sentence frames to drill until reflexive

- "Let me say the number out loud: ..."
- "Those two numbers differ by an order of magnitude, which tells me ..."
- "I'll state an assumption and you can correct me: ..."
- "The trade-off is X versus Y. I choose X because the requirement weighs Y less. The cost I'm accepting is ..."
- "That gets a mechanism, not a wish: ..."
- "Before you ask — when this node dies mid-operation: ..."
- "Gap or duplicate? I choose duplicates, and dedup lives at [the store], authoritatively."
- "Client-side X is cosmetic, never authoritative, because ..."
- "That's designed, not validated. The test I'd run is ..."
- "I haven't operated X at this scale, so let me reason from the access pattern: ..."
- "What I'm deliberately not doing is ... — that's a separate deep dive if you want it."

## PACING DRILLS

1. **Requirements sprint:** the full 10-question discovery phase, aloud, in under 7 minutes. Closed-ended questions only. If you catch yourself asking "what are the requirements" — restart.
2. **The 60-second derivation:** the "2M in / 350K out → aggregation is load-bearing" monologue, timed. This beat *is* the interview.
3. **Answer length discipline:** every deep-dive answer 45–90 seconds. Set a floor, not just a ceiling: a pressed answer must contain a mechanism **and** a cost **and** a failure mode before you stop talking.
4. **The reflex pair:** for any stateful component you ever name, immediately answer: where does state live → what happens on crash mid-operation → gap or duplicate, which did I choose. Run this on five unfamiliar systems this week: URL shortener, ticket booking, chat fan-out, web crawler, ad-click counting.
5. **Read-back protection:** whenever a requirement is corrected mid-interview (such as the TTL/security rule), *write it in a corner of the board*. Capturing the decision prevents the design from later drifting back to the superseded assumption.
