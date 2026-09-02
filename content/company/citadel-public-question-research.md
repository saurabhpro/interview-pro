# Citadel: public question research

This page separates official format guidance from anonymous public reports. The reports are anecdotal drill seeds, not leaked material, confirmed questions, or predictions.

## What official guidance supports

Citadel Securities' [engineering interview guide](https://www.citadelsecurities.com/careers/career-perspectives/our-engineering-interview-process/) describes programming, data structures and algorithms, problem-solving, and behavioural discussion. It recommends assessing the problem before coding, asking clarifying questions, narrating the approach, discussing trade-offs, and asking for help when blocked.

A useful role-neutral practice set therefore includes:

1. A graph problem with underspecified edge cases.
2. A one-pass array or greedy problem with a business follow-up.
3. A production-style component involving buffering, time, and concurrency.
4. A streaming parser that preserves state across calls.
5. A generic order-event parser with explicit input and state invariants.

## Evidence grading

- **Official:** first-party statements from the company.
- **Medium-high:** a detailed first-person public account with enough context to identify the skill.
- **Medium:** an apparently first-person and specific public account with incomplete metadata.
- **Low-medium:** an account with material ambiguity; useful only to broaden practice.

Confidence describes traceability and practice value, not the probability of repetition.

## Publicly reported question signals

| Public report | Paraphrased drill | Pattern to practise | Confidence and use |
|---|---|---|---|
| [Candidate account A](https://leetcode.com/discuss/post/5565531/Citadel-or-Senior-Software-Engineer-or-Reject/) | Given directed currency relationships and rates, find the best conversion between two currencies. Include self-loops and disconnected nodes. | Weighted graphs, multiplicative weights, path search, and clarification of cycles or arbitrage. | **Medium.** Anecdotal practice only. |
| [Candidate account A](https://leetcode.com/discuss/post/5565531/Citadel-or-Senior-Software-Engineer-or-Reject/) | Find all shortest transformations between words when shortest-path semantics are initially implicit. | BFS levels, parent reconstruction, and distinguishing any path from all shortest paths. | **Medium.** Stretch drill from a later stage in the report. |
| [Candidate account B](https://leetcode.com/discuss/post/1792523/citadel-screening-round-senior-software-engineer/) | Return every profitable buy/sell interval, then compound fixed capital using whole-share purchases. | One-pass greedy scan, integer arithmetic, leftover cash, fees, and overflow. | **Medium-high.** Older anecdotal report. |
| [Candidate account C](https://leetcode.com/discuss/post/619324/citadel-software-engineer-nyc-feb-2020/) | Buffer messages for a network endpoint while enforcing maximum count and age. | Bounded queues, size/time flush triggers, backpressure, timer races, retries, and a testable clock. | **Medium-high.** Strong production-style drill. |
| [Candidate account C](https://leetcode.com/discuss/post/619324/citadel-software-engineer-nyc-feb-2020/) | Parse length-prefixed messages across arbitrary input chunks. | Incremental parsing, state machines, incomplete frames, bounds, and malformed-input policy. | **Medium-high.** Useful streaming follow-up. |
| [Candidate account D](https://www.glassdoor.it/Colloquio/Citadel-Securities-Domande-di-colloquio-E1443495.htm) | Parse a generic order-event string. The public account is too sparse to reconstruct a full prompt. | Input grammar, maps, order invariants, and malformed or duplicate events. | **Medium.** Use only to motivate a fresh generic exercise. |
| [Candidate account E](https://www.glassdoor.co.uk/Interview/-Phone-screen-Bunch-of-C-trivia-questions-seemingly-meant-to-gauge-what-coding-question-you-might-stand-a-chance-of-ans-QTN_7276182.htm) | Implement a hash map, then a bounded thread pool that sends messages. | Collision handling, resizing, equality, executors, shutdown, ordering, and backpressure. | **Low-medium.** Breadth drill only. |
| [Candidate account F](https://leetcode.com/discuss/post/5430576/Citadel-OA-Questions/) | Count ranges where endpoint values equal the sum of interior values. | Prefix sums, algebraic reformulation, frequency maps, and overflow. | **Medium-high** account detail, but assessment evidence only. |
| [Candidate account F](https://leetcode.com/discuss/post/5430576/Citadel-OA-Questions/) | Repeatedly apply one decrement to a selected element and another to all remaining elements; minimise operations. | Binary search on the answer, monotone feasibility, rounding, and impossible cases. | **Medium-high** account detail, but assessment evidence only. |
| [Candidate account G](https://leetcode.com/discuss/post/5456743/Citadel-2024-OA/) | Recommend each user's non-friend with the most mutual friends, breaking ties by smallest ID. | Adjacency sets, two-hop enumeration, counting, and tie-breaking. | **Medium.** Online-assessment pattern only. |

## High-priority drills

### Best currency conversion path

Clarify directed versus reciprocal edges, disconnected currencies, repeated quotes, self-loops, and profitable cycles before selecting an algorithm.

### Profitable transaction intervals

Return intervals first, then extend to capital compounding with whole shares, leftover cash, fees, and overflow-safe arithmetic.

### Bounded timed message producer

Define policy before code: flush triggers, producer blocking or rejection, retries, ordering, shutdown, clock injection, and concurrency scope.

### Incremental length-prefixed decoder

Accept arbitrary chunks, emit zero or more complete frames, retain only incomplete state, and test every split point.

### Order-event parser

Create a fresh practice problem around public order-event concepts. Do not claim to reconstruct the underspecified source report.

## Execution rubric

- Restate the problem and identify missing requirements.
- Work a concrete example, including a hostile edge case, before coding.
- State the data structure and invariant.
- Explain one rejected alternative and its trade-off.
- Test normal, boundary, empty, duplicate or cycle, and overflow cases as relevant.
- State time and space complexity without prompting.

The official [engineering candidate FAQ](https://www.citadelsecurities.com/careers/career-perspectives/candidate-faqs-engineering/) additionally highlights commercial judgement, comfort with ambiguity, ownership, programming and design skill, and effective technical communication.

## Guardrails

- Do not label any anecdote “confirmed,” “frequent,” or “likely to repeat.”
- Do not merge Citadel with Citadel Securities when a report does not identify the firm.
- Do not use online-assessment difficulty to predict a live interview.
- Do not reproduce long source wording; the drills above are paraphrases for legitimate preparation.
- Follow the current assessment's own language, platform, timing, and integrity rules.
