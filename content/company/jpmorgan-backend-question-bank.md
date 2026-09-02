# JPMorgan: backend question bank

This role-neutral bank groups reusable Java, concurrency, service, database, and system-design drills. It is practice material, not a claim that any question will recur.

---

## 1. Coding in Java

Focus: clean Java, correct DSA, clear reasoning, time/space complexity.

1. Implement an LRU cache supporting `get` and `put` in O(1) using appropriate data structures. Explain complexity and edge cases.
2. Given an integer array and a target `K`, find all subarrays whose sum equals `K`. Discuss brute force vs optimized approach.
3. Detect if an undirected graph has a cycle. Provide DFS and BFS approaches and compare them.
4. Given a binary search tree, implement a function to find the `k`‑th smallest element.
5. Given a string `s` and a pattern `t`, return the minimum window substring of `s` that contains all characters of `t`.
6. Move all zeroes to the end of an array while maintaining the relative order of non‑zero elements.
7. Given an array of prices, compute the maximum profit you can achieve by buying and selling once.
8. Coin change: given coin denominations and an amount, compute the minimum number of coins required (or report impossible).
9. Longest increasing subsequence: given an array, find the length of the LIS.
10. Check if two strings are anagrams. Extend to a list of strings and find all groups of anagrams.
11. Given a list of strings, find all duplicates and report their counts.
12. Given an array of consecutive integers with one missing value, find the missing integer.
13. Given an array, remove all odd numbers, multiply each remaining element by a constant, and return the sum using Java Streams.
14. Reverse‑add palindrome: repeatedly reverse digits and add until the number becomes a palindrome or you detect a loop.

---

## 2. Core Java & JVM

Focus: fundamentals, performance, and JVM behaviour.

1. Explain how Java garbage collection works and how you would tune G1 GC for a low‑latency payment service.
2. Describe memory visibility issues between threads without synchronization and how the Java Memory Model’s happens‑before guarantees address them.
3. You see frequent Full GC pauses causing P99 latency spikes. Walk through your diagnosis and fixes.
4. How does `CompletableFuture` compose async tasks? Where can exceptions be swallowed and how do you avoid that?
5. What are virtual threads (Project Loom), and how would you evaluate migrating a high‑throughput service to use them?
6. Explain the difference between `Comparable` and `Comparator` and when you would use each.
7. What is "try‑with‑resources" and why is it useful in backend services?
8. Discuss checked vs unchecked exceptions and your philosophy for exception handling in service code.
9. Explain the internals and typical use cases of `ConcurrentHashMap`.
10. What is the difference between `Runnable` and `Callable` and how are they used with executors?

---

## 3. Concurrency & Multithreading

Focus: correctness, performance, and stability.

1. Define deadlock, livelock, and starvation. Provide examples and prevention strategies in Java.
2. Explain when you would use `CopyOnWriteArrayList`, and why it can be both useful and dangerous.
3. Explain `ThreadLocal`: how it works internally, typical use cases, and pitfalls such as memory leaks.
4. Compare `ForkJoinPool` with a regular `ThreadPoolExecutor`. When would you choose each?
5. How would you debug a high CPU or memory issue in a JVM‑based microservice?
6. How do you capture and analyze heap dumps and thread dumps in production?
7. How do you design a concurrent data structure or service API to avoid race conditions when processing financial transactions?

---

## 4. Spring Boot & Microservices

Focus: banking‑grade microservices and reliability.

1. How does Spring Boot autoconfiguration pick the correct `DataSource` bean? How would you override and debug it?
2. Explain the purpose of the Spring Boot starter parent and dependency management.
3. How do you debug lazy initialization exceptions in JPA/Hibernate?
4. Explain how `@Transactional` isolation levels work and which you would use in typical banking operations.
5. Describe how you would implement distributed transactions using the saga pattern or outbox pattern in a payment system.
6. How would you implement role‑based access control (RBAC) using Spring Security?
7. How do you configure connection pooling (e.g., HikariCP) for a high‑throughput service? What metrics do you monitor?
8. How do you detect and fix the N+1 query problem in Spring Data JPA?
9. How would you configure rate limiting at an API gateway level for a public‑facing payments API?
10. Explain how circuit breakers (e.g., Resilience4j) protect microservices and how you would tune them.
11. How do you handle graceful shutdown of Spring Boot microservices running on Kubernetes (readiness/liveness probes, draining connections)?

---

## 5. Databases & Data Modeling

Focus: relational design, NoSQL, and consistency.

1. JPMC uses both relational and NoSQL stores. How do you decide which to use for a given bounded context?
2. Explain MVCC, how it handles read‑write conflicts, and how it interacts with transaction isolation levels.
3. You have a transactions table with billions of rows. How do you add a column with zero downtime?
4. How would you model a double‑entry ledger in a relational database? What constraints enforce accounting correctness?
5. Where is eventual consistency acceptable in a banking context, and where must you enforce strong consistency?
6. How do you design database indices for a high‑volume transactions table to support queries without harming write performance?
7. How do you detect duplicate rows or data anomalies in SQL for financial data reconciliation?

---

## 6. System Design Scenarios

Focus: end‑to‑end architecture and trade‑offs.

1. Design an idempotent payment API that handles retries, duplicate submissions, and partial failures gracefully.
2. A payment transaction spans multiple microservices; a network blip causes partial failure (debit happens, credit doesn’t). Redesign to guarantee consistency.
3. Explain the outbox pattern and why it is preferred over dual‑write in financial systems.
4. Choreography vs orchestration in sagas: which would you pick for a payment flow at a bank and why?
5. Design a real‑time fraud detection system that screens tens of thousands of transactions per minute with sub‑100ms response time.
6. Design an audit logging system that is tamper‑evident, queryable, and can handle millions of events per day with multi‑year retention.
7. Design a reconciliation system that compares JPMC’s internal ledger against an external bank’s records at end‑of‑day, including mismatch handling.
8. Design a distributed rate limiter for a public API gateway that remains accurate and resilient to cache/Redis failures.
9. Design a high‑throughput, low‑latency service for processing card transactions in real time, including failure modes and back‑pressure.

---
