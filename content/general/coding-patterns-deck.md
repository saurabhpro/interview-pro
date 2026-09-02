# Staff-Level Coding Interview Deck — Pattern Recognition & Templates

**How to use this:** Coding rounds at staff level use roughly the same problem difficulty as senior (LeetCode medium, occasional hard) — what changes is the grading. You're scored on whether you'd be a good *code reviewer*: pattern recognition speed, stated complexity before code, narrated invariants, and unprompted edge-case testing. This deck is organized around the skill that actually decides the round: **routing an unknown problem to the right pattern in under two minutes.**

Templates are in Python for brevity — they translate 1:1 to Java. Interview in whichever language you can write a correct hashmap-and-loop in without thinking; the patterns are identical.

---

## 1. The Routing Table — "see this → think this"

This is the single highest-value thing in the deck. Drill it until it fires before conscious thought.

| Signal in the problem statement | Pattern |
|---|---|
| Input is sorted (or rotated-sorted) | Binary search / two pointers |
| "Contiguous" subarray/substring + longest/shortest/count under a constraint | Sliding window |
| Pair/triplet with target, or in-place partition/dedup | Two pointers |
| "K largest / K closest / K most frequent / merge K sorted" | Heap |
| "Next greater/smaller", spans, "days until warmer", histogram areas | Monotonic stack |
| Matching/nesting (parentheses), undo, evaluate expression | Stack |
| "Prerequisites", "build order", "course schedule", any dependency wording | Topological sort |
| Connected components, islands, provinces, "are these linked" | DFS / BFS / union-find |
| Edges arrive over time, "does adding this edge create a cycle" | Union-find |
| Shortest path, unweighted | BFS |
| Shortest path, weighted non-negative | Dijkstra |
| "Number of ways", "min cost to reach", "can it be done", subsequences | DP |
| "All permutations/combinations/subsets", N-queens, word search | Backtracking |
| Prefix matching, autocomplete, search many words at once | Trie |
| Overlapping meetings/ranges, "minimum rooms" | Intervals |
| Cycle in linked list, find middle, kth from end | Fast & slow pointers |
| "Minimize the maximum X" / "maximize the minimum X" / "smallest capacity such that..." | Binary search **on the answer** |
| Complement lookup, "seen before", frequency counting | Hashmap |
| Subarray **sum** equals/at-most K, especially with negatives present | Prefix sum + hashmap |
| Single number, XOR tricks, powers of two, "without using +" | Bit manipulation |

## 2. Confusable Pairs — the disambiguation table

Half of wrong-pattern choices are between these specific pairs. Know the tiebreaker.

| Confusion | Tiebreaker |
|---|---|
| Sliding window vs prefix-sum+hashmap | Negatives in the array + a sum target ⇒ window logic breaks (shrinking no longer monotonically decreases the sum) ⇒ prefix-sum+hashmap. All-positive or distinct-count constraints ⇒ window. |
| DFS vs BFS | Need *shortest* path in unweighted graph ⇒ BFS, always. Need *any* path, exhaustive exploration, or subtree computation ⇒ DFS. |
| Backtracking vs DP | Must *enumerate* every solution ⇒ backtracking. Must *count* or *optimize* over solutions ⇒ DP. (Memoized backtracking IS top-down DP — same thing, different hat.) |
| Greedy vs DP | Can you state an exchange argument in one sentence ("swapping any choice for the greedy one never hurts")? Yes ⇒ greedy. Unsure ⇒ DP. Greedy without the proof sentence is a guess. |
| Heap vs sort | Need everything in order ⇒ sort. Need k of n, or data is streaming ⇒ heap (O(n log k) beats O(n log n) when k ≪ n — say that out loud). |
| Two pointers vs binary search | Both want sorted input. Interaction *between two elements* (pair sum, container) ⇒ two pointers. Locating a value/boundary ⇒ binary search. |
| Union-find vs DFS for components | Static graph, one-shot query ⇒ either. Edges arriving incrementally / repeated connectivity queries ⇒ union-find. |
| Trie vs hashmap | Exact-match lookup ⇒ hashmap. Prefix queries or shared-prefix search across many words ⇒ trie. |
| Subsequence vs substring | "Subsequence" (non-contiguous) ⇒ almost always DP. "Substring/subarray" (contiguous) ⇒ window, stack, or prefix sums. This single word routes the problem. |

---

## 3. Arrays & Hashing

**Recognize it:** complement lookups ("two numbers that sum to..."), frequency counting, "have I seen this before", grouping (anagrams), O(1)-lookup needs, subarray-sum with negatives.

**Mental model:** trade O(n) space for O(1) lookup. The hashmap stores *the thing you'd otherwise re-scan for*: a complement, a count, a first-seen index, or a running prefix sum. Ask: "what do I wish I could look up instantly at each step?" — that's your key.

**Template — prefix sum + hashmap (subarray sum == k, handles negatives):**
```python
def subarray_sum(nums, k):
    seen = {0: 1}          # CRITICAL seed: empty prefix
    run = count = 0
    for x in nums:
        run += x
        count += seen.get(run - k, 0)   # prefixes that complete a k-sum
        seen[run] = seen.get(run, 0) + 1
    return count
```

**Complexity:** O(n) time, O(n) space.

**Validation set:** Two Sum · Group Anagrams · Top K Frequent Elements · Product of Array Except Self · Longest Consecutive Sequence · Valid Sudoku.

**Traps:**
- Forgetting to seed `{0: 1}` — silently miscounts subarrays that start at index 0.
- Longest Consecutive Sequence: only start counting from `x` when `x-1` is *not* in the set — otherwise O(n²).
- Decide upfront whether the map stores counts, indices, or last-seen positions — mixing them mid-solution is a classic live-coding bug.

---

## 4. Two Pointers

**Recognize it:** sorted input + pair/triplet with target; palindrome checks; in-place dedup/partition; "container/trapping water" geometry.

**Mental model:** two indices moving with a *provable discard rule* — at each step, one pointer's move eliminates a set of candidates that provably can't contain the answer. If you can't say *why* moving that pointer is safe, you don't have a two-pointer solution yet, you have two variables.

**Template — pair sum in sorted array:**
```python
l, r = 0, len(a) - 1
while l < r:
    s = a[l] + a[r]
    if s == target: return [l, r]
    if s < target: l += 1      # a[l] can't pair with anything smaller than a[r]
    else:          r -= 1
```

**Complexity:** O(n) time, O(1) space (O(n log n) if you must sort first — say so).

**Validation set:** Valid Palindrome · Two Sum II · 3Sum · Container With Most Water · Trapping Rain Water · Sort Colors.

**Traps:**
- 3Sum dedup: after fixing `i`, skip `a[i] == a[i-1]`; inside the scan, skip equal neighbors after a hit — missing either produces duplicate triplets.
- Container With Most Water: always move the *shorter* wall — moving the taller one can never help (that's the discard-rule sentence; say it).
- Reader/writer variant (dedup in place): writer only advances on keep — don't conflate the two roles.

---

## 5. Sliding Window

**Recognize it:** "contiguous" + longest/shortest/count + a constraint ("at most K distinct", "no repeating characters", "sum ≥ target", "at most K flips").

**Mental model:** a window `[left, right]` maintaining an invariant. `right` expands every step (for-loop); `left` shrinks (while-loop) only when the invariant breaks. The window never moves backward — that's what buys O(n). Two flavors: **grow-until-invalid** (longest valid window) and its inversion **shrink-while-valid** (shortest valid window).

**Template — longest window satisfying constraint:**
```python
def longest_valid(s):
    left = best = 0
    state = {}                       # counts / whatever tracks the invariant
    for right, ch in enumerate(s):
        state[ch] = state.get(ch, 0) + 1          # expand
        while broken(state):                       # shrink until valid
            state[s[left]] -= 1
            left += 1
        best = max(best, right - left + 1)         # window len = r - l + 1
    return best
```

**Template — minimum window (shrink-while-valid inversion, e.g., Minimum Window Substring):**
```python
from collections import Counter
def min_window(s, t):
    need, missing = Counter(t), len(t)
    best = (float('inf'), 0, 0)
    left = 0
    for right, ch in enumerate(s, 1):          # right is exclusive end
        missing -= need[s[right-1]] > 0
        need[s[right-1]] -= 1
        while missing == 0:                    # valid → record, then shrink
            if right - left < best[0]:
                best = (right - left, left, right)
            need[s[left]] += 1
            missing += need[s[left]] > 0
            left += 1
    return "" if best[0] == float('inf') else s[best[1]:best[2]]
```

**Complexity:** O(n) — each index enters and leaves the window once.

**Validation set:** Best Time to Buy & Sell Stock · Longest Substring Without Repeating Characters · Longest Repeating Character Replacement · Permutation in String · Minimum Window Substring · Sliding Window Maximum (monotonic-deque crossover).

**Traps:**
- Window length is `right - left + 1`. Say it every single time; off-by-one here is the most common window bug in live interviews.
- **Negatives break sum-based windows** — shrinking no longer monotonically decreases the sum, so the discard logic is invalid. Route to prefix-sum+hashmap instead. This is the #1 misroute on this pattern.
- Character Replacement: the window never needs to shrink below its best size — `max_freq` can go stale harmlessly. Knowing *why* that's safe is a differentiator question.

---

## 6. Stack & Monotonic Stack

**Recognize it:** matching/nesting (parentheses), most-recent-first processing (undo, RPN), and — for the monotonic variant — "next greater/smaller element", "days until warmer", stock spans, largest rectangle in histogram.

**Mental model (monotonic):** the stack holds a *sorted frontier of unresolved candidates* — elements still waiting for their answer. Each new element resolves (pops) everything it dominates, then joins the frontier. Every index pushes once and pops once, so the nested-looking loop is O(n).

**Template — next greater element:**
```python
def next_greater(a):
    res = [-1] * len(a)
    stack = []                        # indices; values strictly decreasing
    for i, x in enumerate(a):
        while stack and a[stack[-1]] < x:
            res[stack.pop()] = x      # x is the answer for those waiting
        stack.append(i)
    return res
```

**Complexity:** O(n) time — amortized single push/pop per element.

**Validation set:** Valid Parentheses · Min Stack · Evaluate Reverse Polish Notation · Daily Temperatures · Car Fleet · Largest Rectangle in Histogram.

**Traps:**
- Store **indices**, not values, whenever the answer needs a distance ("how many days") — restructuring mid-solution is painful.
- Histogram: append a sentinel `0` to flush the stack at the end, or you'll hand-roll a messy post-loop.
- State the stack's invariant out loud ("indices of a strictly decreasing sequence") before coding — it's the sentence that proves your while-condition is right.

---

## 7. Binary Search (including on-the-answer)

**Recognize it:** sorted/rotated input; O(log n) demanded; and the disguised form — "minimize the maximum", "smallest speed/capacity/days such that condition holds". If the answer space is monotonic (once feasible, always feasible beyond), you can binary-search the *answer* even when nothing is sorted.

**Mental model:** maintain the invariant "the answer, if it exists, is inside [lo, hi]" and prove each branch halves the space without evicting the answer. Pick **one** convention and never deviate mid-problem — convention drift causes more binary-search bugs than logic errors do.

**Template — classic (lo ≤ hi, exact match):**
```python
lo, hi = 0, len(a) - 1
while lo <= hi:
    mid = (lo + hi) // 2
    if a[mid] == t: return mid
    if a[mid] < t: lo = mid + 1
    else:          hi = mid - 1
return -1
```

**Template — on the answer (lo < hi, smallest feasible):**
```python
lo, hi = min_possible, max_possible
while lo < hi:
    mid = (lo + hi) // 2
    if feasible(mid): hi = mid        # mid might BE the answer — keep it
    else:             lo = mid + 1
return lo
```

**Complexity:** O(log n) × cost of `feasible()` for on-the-answer variants.

**Validation set:** Binary Search · Search in Rotated Sorted Array · Find Minimum in Rotated Sorted Array · Time Based Key-Value Store · Koko Eating Bananas · Capacity to Ship Packages / Split Array Largest Sum · Median of Two Sorted Arrays (hard).

**Traps:**
- Rotated arrays: decide "which half is sorted" by comparing `a[mid]` against one fixed end, consistently — flip-flopping between ends mid-solution is the classic failure.
- On-the-answer problems: state the feasibility predicate and its monotonicity in one sentence *before* coding ("if speed k works, every speed > k works") — that sentence is the pattern.
- The two templates have different loop conditions and different shrink rules. Mixing them (`lo < hi` with `hi = mid - 1`) skips candidates.

---

## 8. Linked List

**Recognize it:** explicit list structure; cycle detection; find middle / kth-from-end; reverse in place; merge; and the design classic, LRU cache.

**Mental model:** three tools cover nearly everything — a **dummy head** (eliminates all "deleting the first node" special-casing), **three-pointer reversal**, and **fast & slow pointers** (fast moves 2, slow moves 1: meeting ⇒ cycle; fast at end ⇒ slow at middle).

**Template — reversal:**
```python
prev, cur = None, head
while cur:
    nxt = cur.next
    cur.next = prev
    prev, cur = cur, nxt
return prev                    # new head
```

**Template — fast & slow:**
```python
slow = fast = head
while fast and fast.next:
    slow, fast = slow.next, fast.next.next
    if slow is fast: return True       # cycle
# cycle entry: reset one pointer to head, advance both by 1; they meet at entry
```

**Complexity:** O(n) time, O(1) space — the whole point over copying to an array.

**Validation set:** Reverse Linked List · Merge Two Sorted Lists · Reorder List · Remove Nth Node From End · Linked List Cycle · LRU Cache (hashmap + doubly-linked list) · Merge K Sorted Lists (heap crossover).

**Traps:**
- Any deletion problem: dummy head, no exceptions. The bug you avoid is always "what if I delete the head."
- Draw the pointer surgery for reorder/reversal segments before coding — narrating "save next, rewire, advance" is exactly the reviewer-brain signal staff loops want.
- LRU: the list stores recency order, the map stores node handles; forgetting to move-to-front on *get* (not just put) is the standard bug.

---

## 9. Trees — DFS

**Recognize it:** any per-subtree computation — depth, diameter, balance, path sums, LCA, validate/serialize. Default tree tool.

**Mental model:** trust the recursion. Define precisely what `dfs(node)` *returns for a subtree*, handle the null base case, combine children. The pattern-within-the-pattern: often the value you **return up** (e.g., height) differs from the **answer you're tracking** (e.g., diameter) — keep a separate best-so-far rather than contorting the return value.

**Template — return-up vs track-global (diameter shape):**
```python
def diameter(root):
    best = 0
    def height(node):
        nonlocal best
        if not node: return 0
        L, R = height(node.left), height(node.right)
        best = max(best, L + R)        # answer uses BOTH children
        return 1 + max(L, R)           # but only the taller path goes up
    height(root)
    return best
```

**Complexity:** O(n) time, O(h) stack space — say "O(n) worst case for a skewed tree" unprompted.

**Validation set:** Maximum Depth · Invert Binary Tree · Diameter of Binary Tree · Balanced Binary Tree · Lowest Common Ancestor · Validate BST · Kth Smallest in BST · Serialize and Deserialize Binary Tree.

**Traps:**
- Validate BST: pass down `(min, max)` bounds — comparing only parent↔child is the famous wrong answer (a grandchild can violate a grandparent).
- BST + "kth smallest / in order" ⇒ inorder traversal is sorted order. Reach for it by reflex.
- Serialize: include null markers, or deserialization is ambiguous.

---

## 10. Trees — BFS / Level Order

**Recognize it:** "level by level", "right side view", "zigzag", minimum depth, "rotting oranges"-style simultaneous spread — anything where distance-in-layers is the semantics.

**Mental model:** queue + the **level-freeze idiom**: capture `len(queue)` before the inner loop so you process exactly one level per outer iteration. BFS gives shortest paths in unweighted graphs *because* it explores in distance order.

**Template:**
```python
from collections import deque
q = deque([root])
while q:
    for _ in range(len(q)):        # freeze current level size
        node = q.popleft()
        # process node; per-level logic goes around this loop
        for child in (node.left, node.right):
            if child: q.append(child)
```

**Complexity:** O(n) time, O(width) space — worst case O(n) on the last level of a full tree.

**Validation set:** Level Order Traversal · Right Side View · Zigzag Level Order · Minimum Depth · Rotting Oranges · Word Ladder.

**Traps:**
- **Mark visited when enqueuing, not when dequeuing** — in graphs/grids, the dequeue-time version enqueues the same cell many times and blows up. This is the single most common BFS bug in live interviews.
- Multi-source BFS (rotting oranges): seed the queue with *all* sources at distance 0 — don't run BFS per source.

---

## 11. Tries

**Recognize it:** prefix queries, autocomplete, "does any word start with...", searching many words against one board/text simultaneously.

**Mental model:** a tree where the *path* is the key. Shared prefixes are stored once, so prefix lookup is O(prefix length) regardless of how many words are stored. When searching many words at once (Word Search II), walk the trie *in step with* the search — the trie prunes the search space for all words simultaneously.

**Template:**
```python
class TrieNode:
    __slots__ = ("kids", "end")
    def __init__(self): self.kids, self.end = {}, False

def insert(root, word):
    cur = root
    for ch in word:
        cur = cur.kids.setdefault(ch, TrieNode())
    cur.end = True

def has_prefix(root, p):
    cur = root
    for ch in p:
        if ch not in cur.kids: return False
        cur = cur.kids[ch]
    return True
```

**Complexity:** insert/search O(L) per word of length L; space O(total characters).

**Validation set:** Implement Trie · Design Add and Search Words (with `.` wildcard → DFS branch) · Word Search II.

**Traps:**
- Word Search II without a trie (running word-by-word search) is the intended-failure path — the trie is the point of the problem.
- Prune as you go in Word Search II: mark words found / delete exhausted leaf nodes, or the board DFS re-explores dead branches and times out on the large cases.

---

## 12. Heap / Priority Queue

**Recognize it:** "K largest/smallest/closest/frequent", "merge K sorted", streaming median, "schedule the most frequent task" — anything needing repeated access to the extreme element without full sorting.

**Mental model:** for top-K largest, keep a **min-heap of size K** — the root is the gatekeeper; anything bigger evicts it. For streaming median, **two heaps** (max-heap of the lower half, min-heap of the upper half) balanced within one element. Justify heap over sort out loud: O(n log k) vs O(n log n), decisive when k ≪ n or data streams.

**Template — kth largest / top-K:**
```python
import heapq
h = nums[:k]
heapq.heapify(h)                     # min-heap of size k
for x in nums[k:]:
    if x > h[0]:
        heapq.heapreplace(h, x)      # pop smallest, push x — one op
# h[0] is the kth largest; h holds the top k
```

**Complexity:** O(n log k) time, O(k) space.

**Validation set:** Kth Largest Element · K Closest Points to Origin · Top K Frequent Elements · Merge K Sorted Lists · Find Median from Data Stream · Task Scheduler.

**Traps:**
- Python has min-heaps only — negate values (or use tuples `(-priority, item)`) for max-heap behavior; say you're doing it.
- Two-heap median: re-balance after *every* insert; sizes may differ by at most one, and the median rule depends on which side is larger.
- Kth largest also has an O(n)-average quickselect — *mention* it as the alternative, code the heap (fewer edge cases under time pressure). Naming the trade-off is the staff move.

---

## 13. Backtracking

**Recognize it:** "all subsets / permutations / combinations", "all valid X", N-Queens, word search on a grid, palindrome partitioning — enumeration of a solution *space*, not a single optimum.

**Mental model:** DFS over partial solutions with the sacred trio — **choose, explore, un-choose**. The state you mutate on the way down must be exactly restored on the way up. Pruning (abandoning a partial solution the moment it's provably invalid) is what separates "correct" from "finishes before the heat death of the interview."

**Template:**
```python
def backtrack(start, path):
    if is_solution(path):
        results.append(path[:])        # COPY — the classic bug
        # return here only if solutions can't extend
    for i in range(start, len(choices)):
        if not promising(choices[i]): continue      # prune
        path.append(choices[i])                     # choose
        backtrack(i + 1, path)                      # explore (i, not i+1, if reuse allowed)
        path.pop()                                  # un-choose
```

**Complexity:** exponential by nature — O(2ⁿ) subsets, O(n!) permutations. State it plainly; the interviewer wants to hear you know enumeration can't beat its output size.

**Validation set:** Subsets I/II · Combination Sum I/II · Permutations · Word Search · Palindrome Partitioning · Letter Combinations of a Phone Number · N-Queens.

**Traps:**
- `results.append(path[:])` — appending the live reference means every result mutates into the same empty list. The most common backtracking bug in existence.
- Duplicates in input: sort, then skip `if i > start and a[i] == a[i-1]` — skipping at the same *depth*, not globally.
- `start = i + 1` (each element once) vs `start = i` (unlimited reuse, Combination Sum) — one character, different problem.
- Grid search: mark the cell before recursing, restore after — forgetting the restore breaks sibling paths.

---

## 14. Graphs — DFS / BFS / Grids

**Recognize it:** islands, provinces, regions, clone graph, flood fill — reachability and component questions on explicit graphs or implicit grid-graphs.

**Mental model:** a grid *is* a graph (cells = nodes, 4-directional moves = edges). Components: loop all cells/nodes, launch a traversal from each unvisited one, count launches. Choose DFS for exhaustive/reachability, BFS when distance matters (see §10).

**Template — count islands:**
```python
def num_islands(grid):
    R, C = len(grid), len(grid[0])
    def sink(r, c):
        if not (0 <= r < R and 0 <= c < C) or grid[r][c] != '1': return
        grid[r][c] = '0'               # mark visited in-place
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            sink(r + dr, c + dc)
    count = 0
    for r in range(R):
        for c in range(C):
            if grid[r][c] == '1':
                count += 1
                sink(r, c)
    return count
```

**Complexity:** O(V + E) — for grids, O(R·C).

**Validation set:** Number of Islands · Max Area of Island · Clone Graph · Pacific Atlantic Water Flow · Surrounded Regions · Rotting Oranges (BFS).

**Traps:**
- Recursion depth: a 300×300 all-land grid is ~90K deep — Python's default limit is 1000. Mention the iterative-stack fallback; converting live is trivial if you flag it early.
- Pacific Atlantic: search *from the oceans inward* (reverse the flow) — the forward direction is the intended trap and quadratic-ish.
- Ask (or state) whether you may mutate the input grid as the visited set; if not, budget the O(R·C) visited structure.

---

## 15. Topological Sort

**Recognize it:** the words "prerequisites", "dependencies", "build order", "course schedule". Directed graph + valid ordering = topo sort, every time.

**Mental model:** Kahn's algorithm — repeatedly remove nodes with indegree 0. If you can't remove all n nodes, the leftovers form a cycle; that's your cycle detection for free, and it's usually what the problem is actually asking.

**Template — Kahn's:**
```python
from collections import deque
def topo_order(n, edges):
    adj = [[] for _ in range(n)]
    indeg = [0] * n
    for u, v in edges:                 # u must come before v
        adj[u].append(v)
        indeg[v] += 1
    q = deque(i for i in range(n) if indeg[i] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0: q.append(v)
    return order if len(order) == n else []      # short ⇒ cycle
```

**Complexity:** O(V + E).

**Validation set:** Course Schedule · Course Schedule II · Alien Dictionary (build the graph from pairwise word comparisons — the graph *construction* is the hard part).

**Traps:**
- Edge direction: "A is a prerequisite of B" means A → B. Fix the direction in a comment before coding; reversed edges produce a plausible-looking wrong order.
- Alien Dictionary edge cases: adjacent words where the first is a strict prefix of the second in the *wrong* order (`["abc","ab"]`) ⇒ invalid input, return early.
- DFS-coloring (white/gray/black) is the equivalent alternative; gray→gray edge = cycle. Know it exists; code Kahn's (fewer states to hold under pressure).

---

## 16. Union-Find (Disjoint Set)

**Recognize it:** dynamic connectivity — edges arriving over time, "does this edge create a cycle" (undirected), merging groups (accounts, provinces), Kruskal-style construction.

**Mental model:** a forest where each component has one root representative. `find` walks to the root (with path compression flattening as it goes); `union` links roots. `union` returning False *is* the cycle detector — the two nodes were already connected.

**Template:**
```python
parent = list(range(n))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]      # path halving
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra == rb: return False              # already connected ⇒ cycle edge
    parent[ra] = rb
    return True
```

**Complexity:** effectively O(α(n)) ≈ O(1) amortized per op with compression (+ rank/size). Say "inverse Ackermann — effectively constant"; nobody expects the proof.

**Validation set:** Number of Connected Components · Redundant Connection · Graph Valid Tree (tree ⇔ n−1 edges AND no union returns False) · Accounts Merge.

**Traps:**
- Compare **roots** (`find(a) == find(b)`), never raw parents — the array is lazily flattened.
- Union-find is for **undirected** cycle detection; directed cycles need topo sort or DFS coloring. Applying UF to a directed problem is a real and memorable misroute.
- Accounts Merge: union on a stable key (email → index map), then group by root at the end.

---

## 17. Shortest Path — Dijkstra

**Recognize it:** shortest/cheapest path with **weighted, non-negative** edges — network delay, minimum effort, cheapest route.

**Mental model:** BFS's distance-order exploration, upgraded with a priority queue because edge weights make "nearest unvisited" non-obvious. Lazy-deletion flavor: allow duplicate heap entries, skip any popped entry worse than the recorded best — the skip line *is* the algorithm's correctness under duplicates.

**Template:**
```python
import heapq
def dijkstra(adj, src):                 # adj[u] = [(v, w), ...]
    dist = {src: 0}
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float('inf')): continue   # stale entry — skip
        for v, w in adj[u]:
            nd = d + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist
```

**Complexity:** O(E log V).

**Validation set:** Network Delay Time · Path With Minimum Effort · Swim in Rising Water · Cheapest Flights Within K Stops (**careful** — see traps).

**Traps:**
- Negative edges break Dijkstra's core assumption (settled = final). Negative weights ⇒ Bellman-Ford. State the precondition unprompted.
- Cheapest Flights *Within K Stops*: the stop constraint breaks plain Dijkstra (a settled node might need revisiting via a longer-but-fewer-stops path) — use K rounds of Bellman-Ford-style relaxation or BFS by layers. This is a deliberately planted trap problem.
- Forgetting the stale-skip line turns the algorithm quadratic-ish on dense graphs and can return wrong answers in modified variants.

---

## 18. Dynamic Programming — 1D

**Recognize it:** "how many ways", "minimum cost to reach the end", "can you make it", longest increasing *subsequence*, word break — a sequence of positions with choices, where the best answer at position i depends only on earlier positions.

**Mental model:** the whole game is one sentence: **define dp[i] in English before writing any code** ("dp[i] = the minimum coins to make amount i"). Then the recurrence is just "which earlier states can reach i, and at what cost." If you can't say the definition sentence, you don't have the recurrence — you have vibes.

**Template — the general shape:**
```python
dp = [BASE] * (n + 1)
dp[0] = base_case                       # often also dp[1]
for i in range(1, n + 1):
    dp[i] = best(dp[i - step] + cost    # over all legal steps/choices
                 for each choice)
return dp[n]
```

**Named recurrences worth having cold:**
```python
# Kadane (max subarray) — DP in disguise:
cur = best = nums[0]
for x in nums[1:]:
    cur = max(x, cur + x)               # extend or restart
    best = max(best, cur)

# Coin change (min coins):  dp[a] = min(dp[a], dp[a-c] + 1) for each coin c
# House Robber:             dp[i] = max(dp[i-1], dp[i-2] + a[i])
# LIS in O(n log n) — binary-search crossover:
import bisect
tails = []
for x in nums:
    i = bisect.bisect_left(tails, x)
    if i == len(tails): tails.append(x)
    else: tails[i] = x
# len(tails) = LIS length
```

**Complexity:** typically O(n) or O(n·choices); LIS O(n log n) with the patience trick.

**Validation set:** Climbing Stairs · House Robber I/II · Coin Change · Word Break · Decode Ways · Longest Increasing Subsequence · Maximum Product Subarray.

**Traps:**
- Counting **combinations** vs **permutations** is loop order: coins-outer counts combinations (Coin Change II); amounts-outer counts ordered ways (Combination Sum IV). One swapped loop, silently different answer.
- House Robber II (circular): run the linear solution twice — exclude first house, exclude last — and take the max. Reducing to the solved case is the move.
- Max Product Subarray: track min *and* max (negatives flip roles). The "track two things" adaptation is a favorite follow-up.
- Say the space compression ("I only need the last two values — O(1) space") even if you don't bother implementing it.

---

## 19. Dynamic Programming — 2D (grid / two-sequence / knapsack)

**Recognize it:** two sequences compared (LCS, edit distance), grid path counting/cost, subset-sum / partition ("can we pick items summing to T"), palindromic substrings.

**Mental model:** dp[i][j] = answer for *prefixes* — first i of one thing × first j of another (or cell (i,j) of a grid). Fill order must respect dependencies (usually row-major). Knapsack is 2D (items × capacity) compressible to 1D — and the compression **direction** encodes the problem type (see traps; this is a real interview differentiator).

**Named recurrences worth having cold:**
```python
# LCS:
# dp[i][j] = dp[i-1][j-1] + 1                  if a[i-1] == b[j-1]
#          = max(dp[i-1][j], dp[i][j-1])       otherwise

# Edit distance:
# dp[i][j] = dp[i-1][j-1]                      if chars match
#          = 1 + min(dp[i-1][j],    # delete
#                    dp[i][j-1],    # insert
#                    dp[i-1][j-1])  # replace

# 0/1 knapsack, 1D-compressed (Partition Equal Subset Sum):
dp = [False] * (target + 1)
dp[0] = True
for x in nums:
    for t in range(target, x - 1, -1):     # DESCENDING — 0/1, use item once
        dp[t] = dp[t] or dp[t - x]
```

**Complexity:** O(n·m) time; O(min(n, m)) space with row compression — mention it.

**Validation set:** Unique Paths · Longest Common Subsequence · Edit Distance · Partition Equal Subset Sum · Target Sum · Longest Palindromic Substring (also solvable by expand-around-center in O(1) space — offer both).

**Traps:**
- **Knapsack loop direction is the whole trick:** capacity descending = 0/1 (each item once); ascending = unbounded (reuse allowed). Getting this backwards produces plausible wrong answers that pass small tests.
- Index offset: dp is (n+1)×(m+1) for prefixes, so the character comparison is `a[i-1] == b[j-1]`. Announce the convention before coding.
- Initialize boundary row/column explicitly (edit distance: dp[i][0] = i) — leaving them zero is a silent bug.

---

## 20. Greedy

**Recognize it:** interval scheduling ("max non-overlapping"), jump games, gas station, partition labels — problems where a locally best choice is *provably* globally safe.

**Mental model:** greedy is DP plus a proof that you never need to look back. The proof is the **exchange argument**: "take any optimal solution; swapping its choice for my greedy choice never makes it worse." If you can't say that sentence for your specific rule, treat the problem as DP. Sorting by the right key is usually 80% of the solution — and the right key is often the counterintuitive one (intervals: sort by **end**, not start).

**Canonical shapes:**
```python
# Max non-overlapping intervals: sort by END; take every interval that
# starts at/after the last taken end. (Earliest end leaves maximum room —
# that's the exchange argument.)

# Jump Game: track farthest reachable; if i > farthest, fail.
far = 0
for i, x in enumerate(nums):
    if i > far: return False
    far = max(far, i + x)
return True

# Gas Station: if total gas >= total cost an answer exists; restart the
# candidate start at i+1 whenever the running tank goes negative.
```

**Complexity:** typically O(n log n) for the sort + O(n) scan.

**Validation set:** Jump Game I/II · Gas Station · Hand of Straights · Partition Labels · Valid Parenthesis String · Non-overlapping Intervals.

**Traps:**
- Announcing "greedy" without the exchange sentence is a coin flip presented as a strategy — at staff level the interviewer *will* ask "why does that never fail?"
- Gas Station's non-obvious lemma (failing at j means no start in (start, j] can work) is exactly the kind of one-line justification that separates levels.

---

## 21. Intervals

**Recognize it:** meetings, ranges, bookings — merge them, count overlaps, find minimum rooms.

**Mental model:** **sort, then sweep.** Sort by start for merging (overlap ⇔ `next.start <= current.end`). For "minimum rooms"-type concurrency, either a min-heap of end times (room freed when earliest end ≤ next start) or the event sweep: explode intervals into (+1 at start, −1 at end) events, sort, running sum, take the max.

**Template — merge:**
```python
intervals.sort(key=lambda x: x[0])
merged = [intervals[0]]
for s, e in intervals[1:]:
    if s <= merged[-1][1]:
        merged[-1][1] = max(merged[-1][1], e)    # extend
    else:
        merged.append([s, e])
```

**Complexity:** O(n log n).

**Validation set:** Merge Intervals · Insert Interval · Non-overlapping Intervals · Meeting Rooms I/II · Minimum Interval to Include Each Query.

**Traps:**
- Ask about boundary semantics up front: does [1,3] overlap [3,5]? The `<=` vs `<` in your condition depends on the answer, and guessing wrong fails hidden tests.
- Merging: compare with `max(current_end, e)` — a fully-contained interval must not *shrink* the merged end.
- Event-sweep tiebreak: at equal timestamps, process ends (−1) before starts (+1) when touching doesn't count as overlap.

---

## 22. Bit Manipulation

**Recognize it:** "single number", "without using +/−", counting set bits, missing number, power-of-two checks.

**Mental model:** two workhorses do almost everything — **XOR self-cancels** (`x ^ x = 0`, so pairs vanish and the singleton survives) and **`x & (x-1)` clears the lowest set bit** (loop count = popcount; equals 0 ⇔ power of two).

**One-liners worth having cold:**
```python
x ^ x == 0                    # pairs annihilate → Single Number
x & (x - 1)                   # drop lowest set bit → count bits / power of 2
x & (-x)                      # isolate lowest set bit
missing = n*(n+1)//2 - sum(a) # Missing Number (or XOR 0..n against elements)
```

**Validation set:** Single Number · Number of 1 Bits · Counting Bits · Reverse Bits · Missing Number · Sum of Two Integers.

**Traps:**
- Python ints are unbounded — problems assuming 32-bit overflow (Sum of Two Integers) need explicit masking (`& 0xFFFFFFFF`) and a signed-conversion step at the end. Flag it or your loop never terminates.
- Counting Bits has the elegant DP: `bits[i] = bits[i >> 1] + (i & 1)` — worth producing on demand.

---

## 23. The Execution Protocol (what staff loops actually grade)

Run this identical sequence on every problem. It is the coding-round equivalent of the system-design skeleton and helps prevent cold-start mistakes under pressure.

1. **Restate + interrogate constraints** (60s): input size (drives target complexity), value ranges, negatives?, duplicates?, sorted?, empty allowed?, return format. Input size is a leaked hint: n ≤ 20 whispers backtracking/bitmask; n ~ 10⁵ demands ≤ O(n log n); n ~ 10⁸ or "stream" means O(n)/O(1)-space.
2. **Work one example by hand** — catches misreads before they become code.
3. **State the brute force + its complexity out loud, don't code it** (30s): "Brute force is all pairs, O(n²). Let's beat it." This banks partial credit and proves the optimization is deliberate.
4. **Route via the table → name the pattern and target complexity, get a nod**: "Contiguous + longest + constraint — variable sliding window, O(n)." The naming sentence is the recognition skill being graded.
5. **Outline invariants as comments before code** — 3–4 lines. This is where bugs die cheapest.
6. **Code cleanly, narrating invariants**, not keystrokes: "the stack holds indices of a decreasing sequence, so popping here is safe because..."
7. **Dry-run your example line by line** — then the edge ladder: empty → single element → two elements → all duplicates → negatives → max-size input (complexity check, not a trace).
8. **Close with complexity + one refactor you'd make with more time.** Finding your own bug during the dry run is *positive* signal; being handed it by the interviewer is not.

**Global key points — the cross-cutting reflexes:**
- Complexity **before** code, always. Ask "is O(n log n) acceptable?" — it's a free requirements-gathering point.
- Window length = `right − left + 1`. BFS marks visited **on enqueue**. Backtracking appends a **copy**. Binary search: one convention, never mixed. Knapsack: descending = 0/1, ascending = unbounded. These five lines are ~half of all live-coding bugs in these patterns.
- "Subsequence" ⇒ DP; "substring/subarray" ⇒ window/stack/prefix. One word routes the problem.
- Stuck for 2 minutes? Say so, then run the unstick ladder aloud: sort the input? hashmap for the inner loop? work backwards from the answer? smaller n by hand to spot the recurrence? Visible systematic recovery scores; silent stalling doesn't.

---

## 24. Validation Rubric — how to know a pattern is actually trained

For each problem in a pattern's validation set, solve cold (no hints, no editorial) with a timer — 25 min for mediums, 40 for hards — and score four binary checks:

| Check | Pass condition |
|---|---|
| Recognition | Named the correct pattern within 2 minutes, from the problem statement alone |
| Complexity-first | Stated time/space **before** writing code |
| Clean execution | At most one bug, found by **your own** dry run (not by running/submitting) |
| Edge discipline | Ran the edge ladder unprompted before declaring done |

4/4 = pass. **A pattern counts as trained when ≥70% of its validation set passes at 4/4** — not when you've "seen" the problems. Track it per pattern in a simple grid; your weakest two patterns at any moment are your next study block. Re-test a passed pattern once a week with one random problem from it — recognition decays faster than implementation.

The failure mode this rubric exists to catch is the same one from your system-design mock: recognizing a solution when shown it versus *producing the routing decision cold*. Only the timer and the 2-minute recognition check measure the second thing — and the second thing is the interview.
