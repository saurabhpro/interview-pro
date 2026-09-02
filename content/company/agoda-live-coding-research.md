# Agoda: live coding research

## Scope and confidence

This is a role-neutral synthesis of publicly visible candidate reports and Agoda's own interview guidance. Candidate reports are anecdotal, can be stale, and mix locations, levels, and disciplines. They support practice themes, not an exact prompt forecast. No confidential or leaked material is included.

## Stronger public signals

One detailed [Reddit candidate report](https://www.reddit.com/r/developersIndia/comments/1up1lxm/agoda_staff_engineer_bangkok_selected_8_years_of/) describes two coding exercises:

1. A monotonic-stack or nearest-smaller-element problem.
2. Ranking every array element where a higher value means a higher rank.

Another [candidate report](https://leetcode.com/discuss/post/7237792/agoda-interview-experience-staff-backend-gbsq/) describes two easy-to-medium exercises: a stock buy/sell variation and a dynamic-programming problem similar to Jump Game. The reported expectation was to explain, code, run, and pass tests live.

These accounts are useful because they identify algorithm families. They do not prove recurrence.

## Other publicly reported drills

- **Limit duplicates in a list.** Clarify whether input is sorted and whether the cap applies per value. Practise two pointers and frequency maps. [Glassdoor developer reports](https://www.glassdoor.co.in/Interview/Agoda-Developer-Interview-Questions-EI_IE461386.0%2C5_KO6%2C15.htm)
- **Find all pairs in an unsorted array that sum to a target.** Compare hash-map and sort/two-pointer solutions, including duplicate-pair semantics. [Glassdoor developer reports](https://www.glassdoor.co.in/Interview/Agoda-Developer-Interview-Questions-EI_IE461386.0%2C5_KO6%2C15.htm)
- **Three Sum and Rotten Oranges.** Practise sorting plus two pointers, then multi-source BFS. [Glassdoor developer reports](https://www.glassdoor.co.in/Interview/Agoda-Developer-Interview-Questions-EI_IE461386.0%2C5_KO6%2C15.htm)
- **Reach an endpoint in a square matrix** and **minimum time to complete work.** These map to grid traversal and scheduling or heap patterns. [Glassdoor developer reports](https://www.glassdoor.co.in/Interview/Agoda-Developer-Interview-Questions-EI_IE461386.0%2C5_KO6%2C15.htm)
- **Minimum changes so adjacent characters differ** and **minimum product cost under tagged discounts.** Practise local string reasoning, maps, and greedy choice. [LeetCode candidate report](https://leetcode.com/discuss/post/6697591/)
- **First smaller element to the right, returned as index distance.** This independently reinforces the monotonic-stack theme. [Candidate report](https://shantaram-kokate-swift.medium.com/agoda-staff-ios-engineer-interview-experience-strong-technical-rounds-great-discussions-and-key-d9d90cc5b98a)
- **Maximum of minimum via binary search**, followed by endpoint/JSON handling; later exercises included next-greater and backspace-string comparisons. [Interview Experiences report](https://interviewexperiences.in/experience/agoda/senior-software-engineer-interview-experience)

Older reports also mention queues, linked lists, tree distance, largest all-ones square, and egg dropping. Treat these as topic breadth rather than current-format evidence. [Older public report](https://dev.to/freeze_francis/agoda-backend-engineer-interview-4pbp)

## Practice priorities

The public evidence clusters around array, string, and hash-map work plus one of monotonic stack, two pointers, greedy, binary search, graph traversal, or dynamic programming. A balanced practice set is:

1. Nearest smaller or next greater with a monotonic stack.
2. Ranking, frequency, and deterministic tie-breaking in an array.
3. Stock buy/sell and Jump Game-style state transitions.
4. Pair sum, Three Sum, and bounded duplicates.
5. Multi-source BFS on a grid.

Explain the invariant before coding, then test empty input, one element, duplicates or ties, monotone arrays, and largest values. Implement plainly and do not rely on a remembered company prompt.

## Later-stage system-design themes

Public reports also mention booking or travel-platform discussions: fetching bookings by date range, caching, rate limiting, authentication and authorisation, date normalisation, replication or sharding, and sync/async choices. Another asks about hotel inventory sourced from internal and external providers. These are useful system-design themes, not evidence for a coding exercise. [Platform report](https://leetcode.com/discuss/post/7095261/) · [Hotel-inventory report](https://interviewexperiences.in/experience/agoda/senior-software-engineer-interview-experience)

## First-party guidance

Agoda's [technology hiring guide](https://careersatagoda.com/blog/how-we-hire-agodas-tech-team-interview-process/) says coding evaluates problem-solving, algorithms, data structures, complexity, and efficiency. Its [interview guide and AI policy](https://careersatagoda.com/interview) recommends explaining decisions, asking clarifying questions, and improving an initial solution. Follow the current assessment's own integrity rules.
