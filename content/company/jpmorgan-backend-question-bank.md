# JPMorgan: backend question bank

This role-neutral bank groups reusable Java, concurrency, service, database, and system-design drills. It is practice material, not a claim that any question will recur.

Jump to [Coding](#1-coding-in-java), [Core Java and JVM](#2-core-java-jvm), [Concurrency](#3-concurrency-multithreading), [Spring and microservices](#4-spring-boot-microservices), [Databases](#5-databases-data-modeling), or [System-design questions](#6-system-design-scenarios). The first five sections contain answer guides; system-design answers are deliberately deferred.

---

## 1. Coding in Java

Focus: clean Java, correct DSA, clear reasoning, time/space complexity.

### 1.1 Implement an O(1) LRU cache

**Answer.** Combine a hash map for key lookup with a doubly linked list for recency. The most-recently used entry sits after `head`; the least-recently used sits before `tail`. `get` moves an existing node to the front. `put` updates and moves an existing node, or inserts a new node and evicts the tail node when capacity is exceeded. The invariant is that every map entry has exactly one list node.

```java
final class LruCache<K, V> {
    private final int capacity;
    private final Map<K, Node<K, V>> byKey = new HashMap<>();
    private final Node<K, V> head = new Node<>(null, null);
    private final Node<K, V> tail = new Node<>(null, null);

    LruCache(int capacity) {
        if (capacity <= 0) throw new IllegalArgumentException("capacity");
        this.capacity = capacity;
        head.next = tail;
        tail.prev = head;
    }

    V get(K key) {
        Node<K, V> node = byKey.get(key);
        if (node == null) return null;
        moveToFront(node);
        return node.value;
    }

    void put(K key, V value) {
        Node<K, V> existing = byKey.get(key);
        if (existing != null) {
            existing.value = value;
            moveToFront(existing);
            return;
        }
        Node<K, V> node = new Node<>(key, value);
        byKey.put(key, node);
        addAfterHead(node);
        if (byKey.size() > capacity) {
            Node<K, V> victim = tail.prev;
            unlink(victim);
            byKey.remove(victim.key);
        }
    }

    private void moveToFront(Node<K, V> node) { unlink(node); addAfterHead(node); }
    private void addAfterHead(Node<K, V> node) {
        node.prev = head; node.next = head.next;
        head.next.prev = node; head.next = node;
    }
    private void unlink(Node<K, V> node) {
        node.prev.next = node.next; node.next.prev = node.prev;
    }

    private static final class Node<K, V> {
        final K key; V value; Node<K, V> prev, next;
        Node(K key, V value) { this.key = key; this.value = value; }
    }
}
```

**Complexity.** Expected `O(1)` for `get` and `put`; `O(capacity)` space.

**Tests.** Capacity one; update without growth; `get` changes eviction order; eviction removes map and list state; null-key/value policy; invalid capacity. State explicitly that this implementation is not thread-safe.

**Production shortcut.** If the interviewer asks for idiomatic Java rather than the internals, use `LinkedHashMap` in access-order mode:

```java
final class LruCache<K, V> extends LinkedHashMap<K, V> {
    private final int capacity;

    LruCache(int capacity) {
        super(capacity, 0.75f, true); // accessOrder: get/put moves entry to the tail
        if (capacity <= 0) throw new IllegalArgumentException("capacity");
        this.capacity = capacity;
    }

    @Override
    protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
        return size() > capacity;
    }
}
```

`LinkedHashMap` combines hash lookup with a linked ordering, so expected `get`/`put` cost remains `O(1)` and space is `O(capacity)`. Say explicitly: “I would choose this in production; I would write the manual map-plus-doubly-linked-list version if the exercise is testing the data structure.” It is not thread-safe by itself, and it does not provide TTL, weighted eviction or distributed-cache behaviour.

**Thread safety.** In access-order mode, `get` relinks an entry, so it is a write from a concurrency perspective. Protect both `get` and `put` with one lock (or use `Collections.synchronizedMap` with synchronized iteration):

```java
final class SynchronizedLruCache<K, V> {
    private final int capacity;
    private final LinkedHashMap<K, V> map =
            new LinkedHashMap<>(16, 0.75f, true);

    SynchronizedLruCache(int capacity) {
        if (capacity <= 0) throw new IllegalArgumentException("capacity");
        this.capacity = capacity;
    }

    public synchronized V get(K key) { return map.get(key); }

    public synchronized void put(K key, V value) {
        map.put(key, value);
        if (map.size() > capacity) {
            K eldest = map.keySet().iterator().next();
            map.remove(eldest);
        }
    }
}
```

`ConcurrentHashMap` alone is insufficient because it cannot maintain one global LRU order atomically. A compound “get-or-compute-and-put” operation must also be exposed under the same lock. For higher throughput, shard the cache and accept approximate rather than globally exact LRU ordering.

### 1.2 Find all subarrays whose sum equals K

**Answer.** Use prefix sums. If the current prefix is `p`, every earlier prefix equal to `p - k` begins a valid subarray. Store all indices for each prefix—not only a count—because the question asks for the actual ranges. Seed prefix `0` at index `-1` to support ranges beginning at zero.

```java
record Range(int fromInclusive, int toInclusive) {}

static List<Range> subarraysSummingTo(int[] values, long k) {
    Map<Long, List<Integer>> indicesByPrefix = new HashMap<>();
    indicesByPrefix.put(0L, new ArrayList<>(List.of(-1)));
    List<Range> result = new ArrayList<>();
    long prefix = 0;

    for (int right = 0; right < values.length; right++) {
        prefix += values[right];
        for (int leftPrefix : indicesByPrefix.getOrDefault(prefix - k, List.of())) {
            result.add(new Range(leftPrefix + 1, right));
        }
        indicesByPrefix.computeIfAbsent(prefix, ignored -> new ArrayList<>()).add(right);
    }
    return result;
}
```

**Complexity.** `O(n + z)` time and `O(n + z)` result-inclusive space, where `z` is the number of returned ranges. Counting only would use `O(n)` space. Brute force is `O(n²)` time.

**Tests.** Negative numbers; zeros; ranges starting at index zero; repeated prefix sums; no result; result count larger than `n`. Use `long` for the prefix to avoid integer overflow.

### 1.3 Detect a cycle in an undirected graph

**Answer.** During traversal, seeing a visited neighbour is a cycle only when that neighbour is not the current node’s parent. DFS expresses this recursively; BFS stores `(node, parent)` pairs. Both are correct. Prefer iterative BFS/DFS if graph depth could overflow the call stack, and run traversal from every unvisited node because the graph may be disconnected.

```java
static boolean hasCycleBfs(List<List<Integer>> graph) {
    boolean[] visited = new boolean[graph.size()];
    for (int start = 0; start < graph.size(); start++) {
        if (visited[start]) continue;
        ArrayDeque<int[]> queue = new ArrayDeque<>();
        queue.add(new int[]{start, -1});
        visited[start] = true;

        while (!queue.isEmpty()) {
            int[] current = queue.remove();
            for (int neighbour : graph.get(current[0])) {
                if (!visited[neighbour]) {
                    visited[neighbour] = true;
                    queue.add(new int[]{neighbour, current[0]});
                } else if (neighbour != current[1]) {
                    return true;
                }
            }
        }
    }
    return false;
}

static boolean hasCycleDfs(List<List<Integer>> graph) {
    boolean[] visited = new boolean[graph.size()];
    for (int node = 0; node < graph.size(); node++) {
        if (!visited[node] && dfsFindsCycle(node, -1, graph, visited)) return true;
    }
    return false;
}

private static boolean dfsFindsCycle(
        int node, int parent, List<List<Integer>> graph, boolean[] visited) {
    visited[node] = true;
    for (int neighbour : graph.get(node)) {
        if (!visited[neighbour]) {
            if (dfsFindsCycle(neighbour, node, graph, visited)) return true;
        } else if (neighbour != parent) {
            return true;
        }
    }
    return false;
}
```

**Complexity.** `O(V + E)` time and `O(V)` auxiliary space for either DFS or BFS.

**Tests.** Disconnected graph; single vertex; tree; triangle; self-loop; parallel edges. Clarify whether parallel edges count as a cycle because a plain adjacency-list representation may need edge IDs to distinguish them correctly.

### 1.4 Find the k-th smallest value in a BST

**Answer.** An in-order traversal of a valid BST visits keys in ascending order. Use an explicit stack, decrement `k` whenever a node is popped, and return when it reaches zero. This stops early and avoids materialising the whole traversal.

```java
static int kthSmallest(TreeNode root, int k) {
    if (k <= 0) throw new IllegalArgumentException("k");
    ArrayDeque<TreeNode> stack = new ArrayDeque<>();
    TreeNode current = root;

    while (current != null || !stack.isEmpty()) {
        while (current != null) {
            stack.push(current);
            current = current.left;
        }
        current = stack.pop();
        if (--k == 0) return current.value;
        current = current.right;
    }
    throw new IllegalArgumentException("k exceeds tree size");
}
```

**Complexity.** `O(h + k)` time and `O(h)` space, where `h` is tree height. Worst case is `O(n)` for a skewed tree.

**Tests.** Smallest and largest `k`; balanced and skewed trees; invalid `k`; duplicates under the tree’s declared duplicate-placement policy. If repeated queries are required, augment each node with subtree size for `O(h)` selection.

### 1.5 Minimum window substring

**Answer.** Use a variable sliding window. Count the required multiplicity of every character in `t`. Expand `right`; when all required characters are satisfied, shrink `left` while preserving validity and record the smallest window. Track `formed` against the number of distinct required characters, not the total length of `t`.

```java
static String minWindow(String s, String t) {
    if (t.isEmpty() || s.length() < t.length()) return "";
    Map<Character, Integer> need = new HashMap<>();
    for (char c : t.toCharArray()) need.merge(c, 1, Integer::sum);

    Map<Character, Integer> have = new HashMap<>();
    int formed = 0, left = 0, bestStart = 0, bestLength = Integer.MAX_VALUE;
    for (int right = 0; right < s.length(); right++) {
        char c = s.charAt(right);
        int count = have.merge(c, 1, Integer::sum);
        if (need.containsKey(c) && count == need.get(c)) formed++;

        while (formed == need.size()) {
            if (right - left + 1 < bestLength) {
                bestStart = left;
                bestLength = right - left + 1;
            }
            char removed = s.charAt(left++);
            int remaining = have.merge(removed, -1, Integer::sum);
            if (need.containsKey(removed) && remaining < need.get(removed)) formed--;
        }
    }
    return bestLength == Integer.MAX_VALUE ? "" : s.substring(bestStart, bestStart + bestLength);
}
```

**Complexity.** `O(|s| + |t|)` time because each boundary moves forward once; `O(Σ)` space for the character maps.

**Tests.** Repeated required character (`t = "AABC"`); exact match; no window; empty pattern contract; case sensitivity; Unicode expectations. This code operates on UTF-16 `char`; use code points if supplementary Unicode characters matter.

### 1.6 Move zeroes while preserving order

**Answer.** Maintain `write`, the index for the next non-zero. Scan once and copy non-zero values forward. Fill the suffix with zeroes. This is stable and clearer than repeated swaps; swapping with `write` is also valid and avoids the fill pass.

```java
static void moveZeroes(int[] values) {
    int write = 0;
    for (int value : values) {
        if (value != 0) values[write++] = value;
    }
    while (write < values.length) values[write++] = 0;
}
```

**Complexity.** `O(n)` time and `O(1)` auxiliary space.

**Tests.** All zeroes; no zeroes; leading/trailing zeroes; interleaved zeroes; negative values; empty array. Confirm whether mutation is permitted before coding.

### 1.7 Maximum profit from one buy and one sell

**Answer.** Scan left to right, retaining the cheapest price seen before today. The best sale today is `price - minimumSoFar`; update the global maximum. The ordering invariant prevents selling before buying.

```java
static long maxProfit(int[] prices) {
    if (prices.length < 2) return 0;
    int minimum = prices[0];
    long best = 0;
    for (int i = 1; i < prices.length; i++) {
        best = Math.max(best, (long) prices[i] - minimum);
        minimum = Math.min(minimum, prices[i]);
    }
    return best;
}
```

**Complexity.** `O(n)` time and `O(1)` space.

**Tests.** Increasing, decreasing and flat prices; one/no price; duplicate minimum; very large integer difference. Clarify whether “must trade” permits a negative result; most versions permit no trade and return zero.

### 1.8 Minimum coins for an amount

**Answer.** This is unbounded dynamic programming. Let `dp[a]` be the fewest coins needed for amount `a`. Initialise `dp[0] = 0` and everything else to an unreachable sentinel. For each amount, try every positive coin and extend the best solution for `a - coin`.

```java
static int minCoins(int[] coins, int amount) {
    if (amount < 0) return -1;
    for (int coin : coins) {
        if (coin <= 0) throw new IllegalArgumentException("coins must be positive");
    }
    int[] dp = new int[amount + 1];
    Arrays.fill(dp, amount + 1);
    dp[0] = 0;
    for (int current = 1; current <= amount; current++) {
        for (int coin : coins) {
            if (coin <= current) dp[current] = Math.min(dp[current], dp[current - coin] + 1);
        }
    }
    return dp[amount] > amount ? -1 : dp[amount];
}
```

**Complexity.** `O(amount × numberOfCoins)` time and `O(amount)` space.

**Tests.** Amount zero; impossible amount; coin larger than amount; duplicate coins; non-positive coin rejection; non-greedy case such as coins `[1,3,4]`, amount `6`. If `amount` is enormous, discuss that pseudo-polynomial DP may be infeasible.

### 1.9 Length of the longest increasing subsequence

**Answer.** Maintain `tails[i]`, the smallest possible tail of an increasing subsequence of length `i + 1`. Binary-search the first tail greater than or equal to each value and replace it; append when no such tail exists. `tails` is not necessarily an actual subsequence, but its size is the LIS length.

```java
static int lisLength(int[] values) {
    int[] tails = new int[values.length];
    int size = 0;
    for (int value : values) {
        int low = 0, high = size;
        while (low < high) {
            int mid = (low + high) >>> 1;
            if (tails[mid] < value) low = mid + 1;
            else high = mid;
        }
        tails[low] = value;
        if (low == size) size++;
    }
    return size;
}
```

**Complexity.** `O(n log n)` time and `O(n)` space. The straightforward DP alternative is `O(n²)` time and is often a good first explanation.

**Tests.** Empty, increasing, decreasing and duplicate-only arrays; negative values; mixed sequence. For non-decreasing subsequence, change the binary-search condition to find the first value strictly greater than the input.

### 1.10 Anagrams and groups of anagrams

**Answer.** Two strings are anagrams when they have the same normalised character multiset. For grouping, compute a canonical key per string. Sorting characters is simple and robust; a fixed-size frequency key is faster only when the alphabet is explicitly bounded.

```java
static boolean areAnagrams(String left, String right) {
    return anagramKey(left).equals(anagramKey(right));
}

static List<List<String>> groupAnagrams(List<String> words) {
    Map<String, List<String>> groups = new LinkedHashMap<>();
    for (String word : words) {
        groups.computeIfAbsent(anagramKey(word), ignored -> new ArrayList<>()).add(word);
    }
    return new ArrayList<>(groups.values());
}

private static String anagramKey(String value) {
    int[] points = value.codePoints().sorted().toArray();
    return new String(points, 0, points.length);
}
```

**Complexity.** For total input characters `C` and longest word length `L`, `O(C log L)` time and `O(C)` result/key space. A bounded-alphabet frequency key reduces time to `O(C)`.

**Tests.** Empty strings; repeated letters; case/space/punctuation normalisation policy; Unicode; stable group order. Do not silently lowercase or strip characters—clarify the contract.

### 1.11 Report duplicate strings and counts

**Answer.** Count each value in a map, then retain counts greater than one. `LinkedHashMap` makes output deterministic by first appearance. Return structured data rather than printing from the algorithm.

```java
static Map<String, Long> duplicateCounts(List<String> values) {
    Map<String, Long> counts = new LinkedHashMap<>();
    for (String value : values) counts.merge(value, 1L, Long::sum);
    counts.entrySet().removeIf(entry -> entry.getValue() == 1L);
    return counts;
}
```

**Complexity.** Expected `O(n)` time and `O(u)` space, where `u` is the number of unique strings.

**Tests.** No duplicates; every value duplicated; null policy; case sensitivity; stable order; counts larger than `Integer.MAX_VALUE` if input is streamed. For huge data, discuss partitioned counting or external aggregation.

### 1.12 Find the missing consecutive integer

**Answer.** First clarify the range. If the array contains distinct values from `0..n` with one missing, XOR all expected numbers and all actual numbers; equal values cancel and the missing value remains. XOR avoids arithmetic overflow.

```java
static int missingFromZeroToN(int[] values) {
    int missing = values.length;
    for (int i = 0; i < values.length; i++) missing ^= i ^ values[i];
    return missing;
}
```

**Complexity.** `O(n)` time and `O(1)` space.

**Tests.** Missing zero; missing `n`; middle missing; single-element input. XOR does not validate duplicates or out-of-range values; if input may be corrupt, add validation with a bit set or sort and state the changed complexity.

### 1.13 Filter, multiply and sum with Java Streams

**Answer.** Use an `IntStream` so the pipeline does not box values. The order is filter → transform → reduce. Use `mapToLong` if multiplication or the sum can exceed `int`.

```java
static long transformedEvenSum(int[] values, int multiplier) {
    return Arrays.stream(values)
            .filter(value -> (value & 1) == 0)
            .mapToLong(value -> (long) value * multiplier)
            .sum();
}
```

**Complexity.** `O(n)` time and `O(1)` auxiliary space for the sequential pipeline.

**Tests.** Empty input; all odd/all even; negative values; zero; multiplication overflow avoided by conversion before multiplication. Do not use a parallel stream unless measurement shows a benefit and the data size justifies scheduling overhead.

### 1.14 Reverse-add until a palindrome or loop

**Answer.** Keep a set of visited values, reverse the decimal digits, add, and stop when the value is a palindrome. Use `BigInteger` so repeated additions cannot overflow. A step limit is still required because a sequence can run indefinitely without repeating within practical memory.

```java
static Optional<BigInteger> reverseAddPalindrome(BigInteger start, int maxSteps) {
    if (start.signum() < 0 || maxSteps < 0) throw new IllegalArgumentException();
    Set<BigInteger> seen = new HashSet<>();
    BigInteger current = start;
    for (int step = 0; step <= maxSteps; step++) {
        String digits = current.toString();
        if (digits.contentEquals(new StringBuilder(digits).reverse())) return Optional.of(current);
        if (!seen.add(current) || step == maxSteps) return Optional.empty();
        current = current.add(new BigInteger(new StringBuilder(digits).reverse().toString()));
    }
    throw new AssertionError("unreachable");
}
```

**Complexity.** For `p` steps and at most `d` digits, roughly `O(p × d)` digit work and `O(p × d)` retained set space; big-integer addition cost grows with digit count.

**Tests.** Already-palindromic input; `56 → 121`; zero; negative rejection; step-limit exhaustion; a repeated-state path using an injectable transition if loop detection itself must be unit-tested.

---

## 2. Core Java & JVM

Focus: fundamentals, performance, and JVM behaviour.

### 2.1 How Java GC works and how to tune G1

**Answer.** GC begins from roots—thread stacks, static references, JNI handles—and traces reachable objects. Unreachable objects can be reclaimed. G1 divides the heap into equal regions rather than fixed contiguous young/old spaces. New objects normally enter Eden regions; surviving objects move through survivor regions and eventually become old. Young collections evacuate live objects from selected young regions. Concurrent marking identifies old-region liveness, after which mixed collections evacuate selected young and old regions. Large “humongous” objects receive special region treatment and can create fragmentation pressure.

For a payment service, start with the latency SLO and evidence, not flags. Fix heap size in a container-aware deployment, enable unified GC logs and JFR, then measure allocation rate, pause distribution, promotion, concurrent-cycle headroom, humongous allocations and live-set size. Set a realistic `-XX:MaxGCPauseMillis` target—G1 treats it as a goal, not a guarantee. Give concurrent marking enough headroom, reduce avoidable allocation, size queues/caches, and avoid overly large heaps that lengthen recovery. Change one variable at a time and load-test with production-like traffic.

**Decision rule.** Choose G1 for balanced throughput and predictable moderate pauses across ordinary server heaps. If the hard requirement is extremely small pauses on a very large heap, benchmark ZGC rather than trying to force G1 beyond its design point.

### 2.2 Visibility and happens-before

**Answer.** A data race exists when threads access the same mutable state, at least one access writes, and there is no ordering mechanism. One thread may keep a value in a register/cache, observe writes in a different order, or see a reference before the referenced object’s construction is safely published. “It usually works” is not a Java Memory Model guarantee.

A happens-before edge guarantees visibility and ordering: unlock happens-before a later lock of the same monitor; a volatile write happens-before a later volatile read of that field; actions before `Thread.start()` are visible to the started thread; thread actions happen-before a successful `join()` return; and executor/future APIs add specified hand-offs. Happens-before is transitive.

`volatile` is suitable for independent state publication such as a stop flag, but `count++` is still a read-modify-write race. Use a lock, atomic variable or higher-level concurrent structure for compound invariants. Prefer immutable objects and safe publication so fewer fields require independent reasoning.

**Decision rule.** Name the shared invariant first, then choose the narrowest mechanism that makes the entire invariant atomic and visible.

### 2.3 Diagnose frequent Full GC and P99 spikes

**Answer.** First prove correlation using request-latency telemetry, unified GC logs, JFR and container CPU/memory events. “Full GC” can mean allocation failure, humongous-region pressure, metadata/class unloading pressure, explicit `System.gc()`, evacuation failure, or the process approaching its memory limit. Inspect live-set trend after major collections, allocation/promotion rates, pause causes, old-region occupancy, humongous allocations, metaspace, reference processing and safepoint time.

If the post-GC live set continually grows, take comparable heap histograms/dumps and follow dominator/retained-size paths: suspect unbounded caches, queues, listeners, class loaders or `ThreadLocal` values. If the live set is stable but allocation is extreme, profile allocation sites and remove churn or oversized buffers. If marking starts too late, add heap headroom or adjust G1’s initiating occupancy only after measurement. Remove accidental explicit GC, right-size heap/container limits, cap queues/caches, and fix humongous allocations where possible.

Validate under realistic load and compare P50/P95/P99, throughput, CPU, allocation and recovery—not just average pause. A collector switch can mask but not repair a leak.

**Decision rule.** Classify the problem as leak/live-set, allocation-rate, collector headroom, humongous object, metaspace or infrastructure pressure before changing flags.

### 2.4 CompletableFuture composition and exception handling

**Answer.** `thenApply` transforms a completed value; `thenCompose` flattens a dependent asynchronous operation; `thenCombine` joins independent futures. Non-`Async` continuations may run on the completing thread. `*Async` methods use the common fork-join pool unless an executor is supplied, which is risky for blocking I/O and for isolation between workloads.

Exceptions are retained inside an exceptional future. They appear “swallowed” when nobody observes the terminal stage, when `exceptionally` replaces a failure without telemetry, or when a side branch is created and discarded. `join()` throws unchecked `CompletionException`; `get()` throws checked `ExecutionException`. Use `whenComplete` for observation without changing the outcome, `handle` only when both success and failure intentionally map to a new value, and `exceptionally` for a deliberate fallback. Keep and observe the terminal future, attach context, and centralise timeout/cancellation policy.

Also remember that cancelling a `CompletableFuture` does not reliably interrupt arbitrary underlying work. Bound the executor and downstream calls independently.

**Decision rule.** Use explicit executors per workload, compose rather than block, and make every pipeline end in one observed success/failure boundary.

### 2.5 Virtual threads and migration evaluation

**Answer.** Virtual threads are JVM-managed `Thread` instances designed to make thread-per-request practical for blocking I/O. When a virtual thread blocks in a supported operation, the JVM can unmount it from its carrier platform thread and use that carrier elsewhere. They improve scalability for high-concurrency blocking workloads; they do not make CPU work faster and are not a replacement for admission control.

Audit for pinning and scarce resources. Long blocking operations while holding `synchronized` monitors or entering native/foreign code can pin a carrier. More importantly, creating many virtual threads does not create more database connections, downstream capacity or memory. Keep bounded semaphores/connection pools, deadlines and circuit breakers. Remove thread-pool sizing used purely as a concurrency throttle and replace it with explicit limits.

Evaluate with production-like I/O, comparing throughput, tail latency, CPU, memory, connection-pool waits, downstream saturation and thread dumps. Confirm framework/driver support, observability, cancellation and `ThreadLocal` usage. Prefer structured concurrency only when its preview/stability status fits the chosen JDK and organisational policy.

**Decision rule.** Adopt virtual threads when blocking I/O and thread-management overhead are limiting factors; keep platform pools for CPU-bound bounded parallelism.

### 2.6 Comparable versus Comparator

**Answer.** `Comparable<T>` defines a type’s natural ordering through `compareTo`; `Comparator<T>` defines an external, selectable ordering. A value should have at most one natural order but may have many useful comparators. For example, an `OrderId` may have a natural lexical order while payments can be sorted by creation time, amount or status using comparators.

Ordering must be transitive, antisymmetric and stable with respect to equality expectations. Sorted maps/sets use comparison equality (`compare(...) == 0`) to identify keys, so a comparator inconsistent with `equals` can silently collapse distinct domain objects. Avoid subtraction-based comparisons because of overflow; use `Integer.compare`, `Long.compare` and comparator combinators.

**Decision rule.** Implement `Comparable` only when one ordering is intrinsic and unsurprising. Use named `Comparator`s for business views and make tie-breakers explicit.

### 2.7 Try-with-resources

**Answer.** Try-with-resources closes every `AutoCloseable` resource when the block exits, including exceptional exits. Resources close in reverse declaration order. If both the body and `close()` throw, the body exception is primary and close failures are available through `getSuppressed()`; a manual `finally` often loses or overwrites that information.

Use it for JDBC connections/statements/result sets, streams, files, locks represented by safe wrappers, and client responses whose bodies own sockets. Declare the resource at the narrowest scope. Closing a pooled JDBC connection normally returns it to the pool rather than destroying the physical connection.

**Decision rule.** If an object owns a finite external resource, make ownership visible through `AutoCloseable` and close it structurally, not by convention.

### 2.8 Checked versus unchecked exceptions

**Answer.** Checked exceptions force callers to catch or declare; unchecked exceptions signal failures that the type system does not require callers to handle. The useful distinction is recoverability at a boundary, not “business versus technical.” A caller that can choose a file, retry an interruptible operation, or compensate may benefit from a checked/domain result. Programming errors, violated preconditions and infrastructure failures commonly use unchecked exceptions.

In service code, preserve the cause and attach stable operational context without leaking secrets. Translate exceptions once at boundaries: persistence/vendor errors into domain/infrastructure exceptions, then into API error codes. Do not catch `Exception` merely to log and rethrow, do not use exceptions for ordinary branching, and do not retry without an idempotency and deadline policy. Model expected rejections as explicit result types when they are part of normal domain flow.

**Decision rule.** Ask whether the immediate caller can take a meaningful action. If not, forcing a checked catch usually adds ceremony rather than recovery.

### 2.9 ConcurrentHashMap internals and use cases

**Answer.** Modern `ConcurrentHashMap` uses a volatile table of bins rather than the old fixed segment architecture. Reads are generally non-blocking. Empty-bin insertion can use CAS; updates to a populated bin synchronise on that bin’s head. Heavy-collision bins may become balanced trees. Resizing is cooperative: threads encountering forwarding nodes can help transfer bins to the new table. Counter cells reduce contention when maintaining approximate size.

It rejects null keys and values, removing the ambiguity between “absent” and “mapped to null.” Individual operations are thread-safe, but a sequence such as `if (!map.containsKey(k)) map.put(k, v)` is not atomic. Use `computeIfAbsent`, `compute`, `merge` or `replace` for per-key atomic operations, keeping mapping functions short and side-effect-free. Iterators are weakly consistent rather than snapshot-consistent.

**Decision rule.** Use it for highly concurrent key-based state where per-key atomicity is sufficient. Use locks or another design when an invariant spans keys or external side effects.

### 2.10 Runnable versus Callable

**Answer.** `Runnable.run()` returns no value and cannot declare checked exceptions. `Callable<V>.call()` returns a value and may throw. `Executor.execute` accepts `Runnable` and provides no result handle. `ExecutorService.submit` accepts either and returns a `Future`; submitting a `Runnable` produces a future whose successful result is normally null.

Failures from `execute` reach the worker’s uncaught-exception handling, while failures from `submit` are captured by the `Future` and may be missed if it is ignored. `Future.get()` blocks and wraps task failures in `ExecutionException`; cancellation is cooperative and interruption-aware code must restore or propagate interrupt status rather than swallowing it.

**Decision rule.** Use `Callable` when the task has a meaningful value or declared failure. Whichever interface is used, retain an observable completion path and avoid unbounded executor queues.

---

## 3. Concurrency & Multithreading

Focus: correctness, performance, and stability.

### 3.1 Deadlock, livelock and starvation

**Answer.** Deadlock means threads wait forever in a cycle: thread A owns lock 1 and waits for lock 2 while B owns lock 2 and waits for lock 1. Prevent it with a global lock order, reduced lock scope, immutable state, `tryLock` with bounded recovery, or by placing the invariant behind one owner.

Livelock means threads keep changing state but make no progress—for example, two workers repeatedly release and reacquire resources to be polite. Randomised/bounded backoff, ownership and progress budgets break the symmetry. Starvation means a runnable task rarely receives CPU, lock access or pool capacity because other work continually wins; fair locks/queues can help, but admission control, workload isolation and bounded tasks are usually more important.

Diagnose with repeated thread dumps, lock-owner/waiter relationships, executor metrics and progress counters. A single dump can show deadlock; livelock and starvation require evidence across time.

**Decision rule.** Describe both safety (“nothing incorrect happens”) and liveness (“valid work eventually completes”), then instrument time spent waiting and forward progress.

### 3.2 CopyOnWriteArrayList

**Answer.** Every mutation acquires a lock and publishes a newly copied backing array. Reads require no lock and iterators traverse an immutable snapshot, so they neither throw `ConcurrentModificationException` nor observe later writes. This is excellent for small, read-mostly collections such as listener/configuration lists where iteration vastly exceeds mutation.

It is dangerous when the collection is large or write-heavy: every change is `O(n)` copy time, allocates a new array, creates GC pressure and temporarily retains old snapshots while iterators live. Compound actions still need atomic APIs or external coordination. Its iterators do not support mutation.

**Decision rule.** Choose it only when snapshot iteration is valuable and writes are demonstrably rare. Use a concurrent queue/map, immutable snapshot held in an `AtomicReference`, or explicit locking for other access patterns.

### 3.3 ThreadLocal internals and leaks

**Answer.** Each `Thread` owns a `ThreadLocalMap`; a `ThreadLocal` is a key into that map, so values are isolated per thread rather than stored in the `ThreadLocal` object itself. Keys are weak references, but values are strong references. If the key becomes unreachable, the stale value can remain attached to a long-lived pool thread until map activity cleans it. That can retain large objects or application class loaders across redeployments.

Use `ThreadLocal` sparingly for truly thread-confined context or non-thread-safe helpers. Always `remove()` in `finally` around pooled-thread usage. Do not use it as hidden dependency injection. Context does not automatically propagate through `CompletableFuture`, reactive pipelines or virtual threads in the way developers often assume; prefer explicit context passing or the platform’s scoped/context mechanism.

**Decision rule.** If the data is request/business state, pass it explicitly. Reserve `ThreadLocal` for infrastructure context whose lifecycle is mechanically bounded.

### 3.4 ForkJoinPool versus ThreadPoolExecutor

**Answer.** `ForkJoinPool` targets recursive CPU-bound work split into many small tasks. Each worker owns a deque and idle workers steal work, improving utilisation when subtasks recursively fork and join. The common pool also backs parallel streams and default `CompletableFuture` async stages, so blocking or monopolising it can create unrelated latency.

`ThreadPoolExecutor` exposes core/max threads, keep-alive, queue, thread factory and rejection policy. It fits independent tasks, workload isolation and explicitly bounded admission. For blocking I/O, use virtual threads or an appropriately isolated bounded executor rather than hiding blocking inside fork-join tasks; `ManagedBlocker` is a specialised fallback.

**Decision rule.** Use fork-join for measured, divide-and-conquer CPU parallelism. Use a dedicated `ThreadPoolExecutor` for independently queued work requiring capacity and rejection control.

### 3.5 Debug high CPU or memory in a JVM service

**Answer.** Start with the symptom’s time window and correlate service latency/error rate with container throttling, CPU, RSS/heap, GC, allocation, thread count, queue depth and a deployment/configuration change. For CPU, take multiple thread dumps and a JFR/profile: identify threads repeatedly RUNNABLE in the same stacks, lock spinning, regex/serialization loops, retry storms or GC CPU. For memory, distinguish Java heap, metaspace, direct buffers, thread stacks and native/container memory.

Compare post-GC live-set trends and class histograms. A growing live set suggests retention; high allocation with a stable live set suggests churn. Heap dumps and dominator trees locate retained owners. Native memory tracking, direct-buffer metrics and thread counts address non-heap growth. Reproduce under representative load and verify the fix against tail latency and throughput.

**Decision rule.** Do not begin with tuning flags. First classify CPU saturation, throttling, allocation pressure, heap retention, native memory, blocked capacity or downstream retry amplification.

### 3.6 Capture and analyse heap and thread dumps safely

**Answer.** Prefer low-overhead continuous JFR and automated diagnostics before an incident. For a thread dump, use `jcmd <pid> Thread.print -l` (or platform-equivalent), take several snapshots seconds apart, and compare state transitions, lock owners, repeated stacks and executor queues. For heap, start with a class histogram; capture a heap dump only when needed because it may pause the JVM, consume disk and contain credentials or personal data.

Analyse heap dumps offline using dominator trees, retained size and paths to GC roots. Compare dumps or histograms over time rather than treating the largest class as the leak. Store artifacts encrypted with restricted access and retention/deletion rules. In Kubernetes, pre-plan permissions, writable volume capacity and safe artifact extraction; an ad hoc dump during disk pressure can worsen the outage.

**Decision rule.** Capture the least invasive artifact that can answer the hypothesis, protect it as production data, and preserve timestamps/deployment metadata for correlation.

### 3.7 Avoid races in financial transaction processing

**Answer.** Start from the invariant—for example, one idempotency key creates at most one payment intent, and an account cannot reserve more available funds than it has. Put the authoritative check and state transition in one database transaction using a unique constraint plus a conditional update or correctly scoped lock. Return the existing result for duplicate requests.

Publish downstream work through a transactional outbox/CDC boundary so a committed state change cannot be lost between the database and broker. Consumers use business idempotency keys and monotonic state transitions; retries are bounded and safe. Avoid holding database transactions across network calls. Treat timeouts as unknown outcomes, then query/reconcile rather than blindly repeating a non-idempotent side effect.

For in-process state, expose one atomic domain operation rather than getters followed by setters. Stress-test with barriers and many concurrent duplicate/reservation requests, then verify persisted invariants—not merely returned responses.

**Decision rule.** Synchronisation protects one process; database constraints, idempotency and reconciliation protect the business invariant across processes and failures.

---

## 4. Spring Boot & Microservices

Focus: banking‑grade microservices and reliability.

### 4.1 DataSource autoconfiguration

**Answer.** Spring Boot applies `DataSourceAutoConfiguration` only when its conditions match: JDBC classes are present, no user-defined `DataSource` bean already wins, and suitable configuration/embedded database information exists. It binds `spring.datasource.*` properties and normally selects the available pool implementation, commonly HikariCP. A manually declared `DataSource` backs off the default configuration; multiple candidates require `@Primary` or explicit qualifiers.

Override through configuration properties for the ordinary single-source case, or define named `DataSourceProperties`, `DataSource`, transaction-manager and entity-manager beans for multiple databases. Debug with the condition evaluation report (`--debug` or Actuator conditions), bean listings, effective configuration, driver/classpath checks and startup logs. Verify secrets and URLs without logging credentials.

**Decision rule.** Prefer Boot’s conventional single `DataSource`; take explicit ownership only when multiple stores, routing or nonstandard lifecycle genuinely require it.

### 4.2 Starter parent and dependency management

**Answer.** Spring Boot’s starter dependencies provide curated capability bundles; the dependency-management BOM aligns compatible library versions. The Maven starter parent additionally supplies plugin management and sensible build defaults. Projects with another corporate parent can import `spring-boot-dependencies` as a BOM instead of inheriting from the Boot parent, but then must configure plugins/defaults themselves.

Do not add arbitrary explicit versions to managed dependencies: that can create binary incompatibility and confusing security upgrades. Inspect the effective POM/dependency tree when versions differ from expectation. Upgrade the Boot release as a tested platform unit, while explicitly managing libraries outside its BOM.

**Decision rule.** Treat dependency management as a tested platform contract, not merely a convenience that removes version numbers.

### 4.3 LazyInitializationException in JPA/Hibernate

**Answer.** A lazy association is a proxy/collection that needs an open persistence context to load. The exception occurs when code touches it after the session/transaction has closed. First identify which boundary returned a partially initialised entity and which query/application layer later dereferenced it. SQL logging, Hibernate statistics and a debugger confirm the access—not a blanket switch to eager loading.

Fetch exactly the data needed inside the service transaction using a fetch join, entity graph, projection or explicit query. Map persistence entities to DTOs before leaving that boundary. Avoid Open Session in View as a default fix: it hides query timing, encourages N+1 behaviour and performs database work during rendering. Also remember Spring proxy limitations: self-invocation and non-public methods may bypass `@Transactional`.

**Decision rule.** Make each use case own its fetch plan; do not make the entire domain graph eager to repair one endpoint.

### 4.4 Transaction isolation for banking operations

**Answer.** `@Transactional(isolation = ...)` requests a database isolation level through the transaction manager; actual behaviour is database-specific. Read Committed prevents dirty reads but permits non-repeatable reads and phantoms. Repeatable Read stabilises previously read rows in the transaction, with implementation-specific handling of phantoms/write conflicts. Serializable aims to make concurrent results equivalent to some serial order, often through locks or serialization failures that must be retried.

Choose isolation from the invariant. For an idempotent request record, a unique constraint under Read Committed may be sufficient. For balance/inventory reservation, use an atomic conditional update such as `UPDATE ... SET available = available - ? WHERE id = ? AND available >= ?`, or a carefully scoped row lock/version check. Serializable can simplify complex multi-row invariants but costs concurrency and requires retry handling.

Do not keep a transaction open during remote I/O. State transitions around external calls belong to a durable workflow with reconciliation.

**Decision rule.** Isolation does not replace constraints. Encode invariants in the database and use the weakest level that still makes the whole transaction correct.

### 4.5 Saga and transactional outbox

**Answer.** A saga is a sequence of local transactions with explicit forward and compensating actions; it does not provide ACID rollback across services. Model payment states such as `CREATED → FUNDS_RESERVED → SUBMITTED → COMPLETED`, plus rejection, unknown and compensation paths. Each command is idempotent and each transition validates the current state/version.

Within one local transaction, update domain state and insert an outbox row. A CDC connector or publisher sends the outbox event to the broker at least once. Consumers deduplicate by stable event/business ID and commit their state before acknowledging. This removes the database-plus-broker dual-write gap but not duplicate delivery, ordering choices or external-side-effect uncertainty.

Use orchestration when the workflow has money, deadlines, compensations and operator visibility; choreography is acceptable for loosely coupled reactions but becomes opaque when many services collectively own one lifecycle.

**Decision rule.** Outbox solves reliable publication; saga defines the cross-service business lifecycle. A payment flow commonly needs both.

### 4.6 RBAC with Spring Security

**Answer.** Authenticate with a trusted identity provider using OAuth2/OIDC or resource-server JWT validation. Convert signed claims or directory groups into application authorities through an explicit mapping layer; do not accept role names from request parameters. Authorise coarse endpoint access in the `SecurityFilterChain` and use method security (`@PreAuthorize`) for service operations.

RBAC alone is insufficient for banking data. Add resource/tenant ownership and contextual policy: a user with `PAYMENT_APPROVER` may approve only their legal entity, within amount/segregation-of-duties rules, and must not approve their own instruction. Centralise policy decisions, deny by default, audit both allowed and denied sensitive actions, and test role × tenant × resource combinations.

**Decision rule.** Roles describe capability; domain policy decides whether this principal may perform this action on this resource now.

### 4.7 Configure and observe HikariCP

**Answer.** Size the pool from database capacity, service replica count and measured transaction duration—not request thread count. Total maximum connections across replicas must remain below the database limit with headroom for administration and migrations. A small saturated pool with bounded waiting can protect the database better than a large pool that converts an outage into connection and lock contention.

Set a connection timeout below the request deadline, validate max lifetime against network/database idle limits, and use leak detection temporarily for diagnosis rather than as a permanent substitute for ownership discipline. Keep transactions short and close resources structurally.

Monitor active, idle, pending and maximum connections; acquisition time; usage/hold time; timeouts; connection creation/failure; database CPU/IO; query latency; lock waits; transaction duration and application queueing. Alert on sustained pending/acquisition latency, not only pool utilisation.

**Decision rule.** The pool is an admission-control boundary to a scarce database, not a throughput knob to turn upward.

### 4.8 Detect and fix N+1 queries

**Answer.** N+1 occurs when one query loads parent rows and subsequent lazy access issues one query per parent. Detect it with SQL/query-count logs, Hibernate statistics, APM traces and integration tests that assert query counts for representative result sizes. It often appears only after mapping/serialisation accesses a relationship.

Fix the use case with a fetch join, entity graph, DTO projection, batch fetching or a deliberate second query using `IN`. Avoid making every association eager: that can produce huge joins, duplicate rows, pagination errors and unnecessary data. For paginated one-to-many views, fetch parent IDs first, then fetch required children in a bounded second query.

**Decision rule.** Optimise the query shape per read use case; do not change the whole object model’s fetch policy to hide one endpoint’s access pattern.

### 4.9 API-gateway rate limiting

**Answer.** Define the policy before the algorithm: key by authenticated client/tenant plus route and possibly operation risk; distinguish sustained rate from bursts; and return `429` with useful retry metadata. Token bucket supports bursts with an average refill rate. Sliding-window variants give smoother fairness at greater state cost. Apply a cheap edge limit for volumetric protection and a business-aware service limit for expensive or financially sensitive operations.

A shared Redis-backed limiter can use an atomic script, but define behaviour when Redis is slow or unavailable. Fail closed for high-risk money movement only if the product accepts lost availability; fail open with conservative local limits for lower-risk reads. Never let rate limiting replace idempotency. Exemptions and administrative overrides must be audited.

Monitor allowed/rejected counts by tenant/route, limiter latency/errors, hot keys, Redis saturation and downstream protection outcomes.

**Decision rule.** Rate-limit the scarce resource and abuse case, then choose explicit degraded behaviour instead of letting a cache outage decide it accidentally.

### 4.10 Circuit breakers and tuning

**Answer.** A circuit breaker observes recent outcomes. When failure or slow-call thresholds exceed policy after a minimum sample size, it opens and rejects calls quickly. After an open duration, half-open permits limited probes; enough successes close it, while failures reopen it. This prevents wasted work and gives a failing dependency recovery room.

Set call timeouts first; otherwise slow calls can occupy resources before the breaker reacts. Tune windows and thresholds from dependency SLOs and traffic volume, not defaults. Isolate by dependency/operation so one failure does not open unrelated traffic. Combine carefully with bulkheads and bounded retries with jitter; retry multiplication across layers can amplify an outage. Count only relevant failures—business rejections should not normally trip infrastructure protection.

Provide a truthful fallback: cached/stale reads may be acceptable, but a payment timeout should become `PENDING/UNKNOWN`, not fabricated success or failure.

**Decision rule.** A breaker protects capacity; it does not repair correctness. Pair it with idempotency, durable state and reconciliation.

### 4.11 Graceful shutdown on Kubernetes

**Answer.** Readiness answers whether the pod should receive new traffic; liveness answers whether it is irrecoverably stuck and should restart. Startup probes protect slow initialisation. Do not make liveness depend on a downstream database or vendor, or a dependency outage can restart every healthy pod.

On termination, Kubernetes sends `SIGTERM` and removes the pod from service endpoints, but propagation is not instantaneous. Spring Boot graceful shutdown should stop accepting new work, allow in-flight HTTP requests to finish within a bounded phase timeout, stop/pause message intake, commit or safely abandon processing, close clients/pools and flush telemetry. Set `terminationGracePeriodSeconds` longer than the application drain budget and align load-balancer deregistration. Consumers should finish and acknowledge only committed work; otherwise let the broker redeliver idempotently.

Test rolling updates and forced timeout paths. Track in-flight work, shutdown duration, forced terminations, redelivery and error rates during deployments.

**Decision rule.** A graceful shutdown is a coordinated traffic-and-work drain with a hard deadline, not merely a process hook.

---

## 5. Databases & Data Modeling

Focus: relational design, NoSQL, and consistency.

### 5.1 Relational versus NoSQL by bounded context

**Answer.** Start with invariants and access patterns, not company preference. Use a relational database when the context needs multi-row transactions, uniqueness/referential constraints, evolving ad hoc queries and a strong system of record—for example ledger posting, account ownership or payment state. Use a key-value/document/wide-column store when aggregate access is known, horizontal scale/availability dominates, denormalisation is acceptable, and cross-record invariants are weak—for example idempotent document retrieval, session state or a derived customer timeline.

Separate authoritative writes from derived read models. A relational ledger can publish events that build a search/document projection; the projection may be rebuilt and eventually consistent. Avoid polyglot persistence without an operational reason: every store adds backup, recovery, security, observability and skill costs. Document partition keys, consistency guarantees, hot-key behaviour, schema evolution and repair.

**Decision rule.** Choose the store that natively enforces the bounded context’s hardest invariant while meeting its dominant access pattern and failure requirements.

### 5.2 MVCC, conflicts and isolation

**Answer.** MVCC stores multiple row versions so readers can usually observe a snapshot without blocking writers. A transaction sees versions allowed by its snapshot/isolation rules; old versions remain until no relevant transaction needs them and cleanup reclaims them. MVCC improves read/write concurrency but does not make concurrent writes safe automatically.

Two writers targeting the same row still contend: one may wait, overwrite under last-writer-wins behaviour, fail an explicit version predicate, or receive a serialization error depending on SQL and isolation. Read Committed usually obtains a new statement snapshot, so repeated reads may differ. Repeatable Read commonly keeps a transaction snapshot, but exact phantom/write-skew rules vary by database. Serializable adds conflict detection or locking to prevent anomalies equivalent to non-serial execution, at the cost of aborts/waits.

Optimistic locking adds `WHERE id=? AND version=?`; zero affected rows means the caller must reload/retry or reject. It protects a known row version but does not alone enforce multi-row predicates.

**Decision rule.** Name the anomaly—lost update, write skew, phantom or stale read—then select SQL constraints/locking and isolation that prevent that anomaly on the actual database.

### 5.3 Add a column to a billion-row table with zero downtime

**Answer.** Use expand–migrate–contract. First verify the database/version’s DDL behaviour on a production-like copy. Add a nullable column, or a metadata-only constant default where supported, with no application dependency. Deploy readers that tolerate both old and new rows and writers that populate the column. Backfill in small primary-key/partition ranges with checkpoints, rate limits and short transactions; monitor replica lag, locks, WAL/log volume, storage and latency.

After backfill, validate counts/checksums and repair gaps. Then add indexes using the database’s online/concurrent mechanism, and enforce `NOT NULL` through a non-blocking validated constraint sequence where supported. Finally switch reads to the new field and remove compatibility code in a later release. A trigger or dual-write may bridge long migrations, but adds load and must be removed deliberately.

Prepare pause/resume and rollback paths. “Zero downtime” means no visible service outage; it does not mean the migration has zero resource impact.

**Decision rule.** Separate schema availability, data backfill and constraint enforcement into independently deployable, observable stages.

### 5.4 Relational double-entry ledger

**Answer.** Model an immutable journal transaction/header and two or more immutable postings/entries. Each posting references an account and contains a signed amount or explicit debit/credit direction plus currency. The core invariant is that postings balance to zero per transaction and currency. Store money in integer minor units or an explicitly bounded decimal—not floating point.

Foreign keys enforce valid transaction/account references; unique business/idempotency keys prevent duplicate journal creation; check constraints reject zero/invalid amounts and illegal account/currency combinations. A database transaction inserts the journal and all postings atomically. Enforcing aggregate zero-sum may require a deferred constraint trigger, stored posting function or a tightly controlled write API because ordinary row checks cannot see the complete set.

Never update a posted entry. Correct with a linked reversal and replacement so history remains auditable. Account balance is a derived sum or transactionally maintained projection that must reconcile to postings. Separate ledger finality from payment workflow state: an external transfer can be pending while reservations/ledger movements are represented explicitly.

**Decision rule.** The immutable postings are the accounting source of truth; balances and reports are projections with reconciliation paths.

### 5.5 Eventual versus strong consistency in banking

**Answer.** Require strong consistency at the point an invariant must hold: preventing duplicate payment acceptance, reserving spendable balance, posting balanced ledger entries, enforcing a limit, or transitioning a workflow from one exclusive state. This does not require a global distributed transaction; it means each authoritative boundary commits its invariant atomically.

Eventual consistency is appropriate for rebuildable or lag-tolerant views: notifications, search, analytics, statements generated from finalised postings, fraud features that are not in the synchronous decision path, and dashboards. State the staleness SLO and user semantics. A stale balance labelled “available to spend” can cause harm; a slightly delayed monthly analytics chart may not.

Cross-service workflows use durable states, idempotent messages and reconciliation. During uncertainty, expose `PENDING` rather than inventing a final result. Measure projection lag, aged pending items and reconciliation breaks.

**Decision rule.** Classify data as authoritative decision state or derived view, then define the cost and maximum duration of staleness explicitly.

### 5.6 Index a high-volume transactions table

**Answer.** Derive indexes from real query shapes. Equality predicates normally lead; then range/sort columns. A customer-history query such as `WHERE account_id=? AND created_at<? ORDER BY created_at DESC LIMIT ?` suggests `(account_id, created_at DESC)` and keyset pagination. Add included columns only when they materially enable index-only reads. Partial indexes can target active/pending rows instead of indexing cold history.

Every index increases write amplification, WAL/log volume, memory/cache demand, vacuum/maintenance and storage. Remove redundant prefix/unused indexes using usage statistics and query plans. Avoid indexing low-cardinality columns alone. For billions of rows, partitioning may provide retention pruning and operational isolation, but the partition key must match access and lifecycle patterns; it is not an automatic query accelerator.

Validate with representative cardinalities and `EXPLAIN ANALYZE`, including worst tenants and recent/historical ranges. Monitor query latency, rows scanned, buffer hit ratio, index size/bloat, write latency and replication lag.

**Decision rule.** Each index needs a named query/SLO owner and a measured read benefit that justifies its write cost.

### 5.7 Detect duplicate rows and reconciliation anomalies

**Answer.** Define the business key first; row equality is rarely the correct notion of duplicate. Exact duplicate candidates are found with grouping:

`SELECT business_key, COUNT(*) FROM transactions GROUP BY business_key HAVING COUNT(*) > 1`.

Use `ROW_NUMBER() OVER (PARTITION BY business_key ORDER BY created_at, id)` to label later copies, but do not delete until the authoritative record and side effects are understood. Prevent recurrence with a unique constraint/index on the true idempotency key.

For reconciliation, normalise internal and external records into comparable keys/amounts/currency/dates, aggregate each side to the intended grain, and full-outer-join them. Classify missing-internal, missing-external, amount/currency/status mismatch and duplicate-on-either-side separately. Allow explicit timing windows for in-flight/late settlement, retain source lineage and create durable breaks with owner, age and resolution—not a one-off query result.

**Decision rule.** Detection is only the first control. A production answer includes prevention, deterministic repair, auditability and proof that the repaired totals reconcile.

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
