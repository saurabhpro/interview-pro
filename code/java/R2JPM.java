import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * JPMorgan practice: find managers with more than five reports.
 *
 * The direct-report method counts only immediate children. The descendant
 * method follows the hierarchy to count all levels below each manager.
 */
public final class R2JPM {

    public record Employee(String empId, String name, String managerId) {}

    private static final int REPORT_THRESHOLD = 5;

    /** Returns employee IDs having strictly more than five direct reports. */
    public static List<String> managersHavingMoreThanFiveDirectReports(
            List<Employee> employees) {
        Map<String, Long> directReportsByManager = new HashMap<>();

        for (Employee employee : employees) {
            if (employee.managerId() != null
                    && !employee.empId().equals(employee.managerId())) {
                directReportsByManager.merge(employee.managerId(), 1L, Long::sum);
            }
        }

        return directReportsByManager.entrySet().stream()
                .filter(entry -> entry.getValue() > REPORT_THRESHOLD)
                .map(Map.Entry::getKey)
                .toList();
    }

    /** Returns employee IDs having strictly more than five descendants. */
    public static List<String> managersHavingMoreThanFiveDescendants(
            List<Employee> employees) {
        Map<String, List<String>> childrenByManager = new HashMap<>();

        for (Employee employee : employees) {
            if (employee.managerId() != null
                    && !employee.empId().equals(employee.managerId())) {
                childrenByManager
                        .computeIfAbsent(employee.managerId(), ignored -> new java.util.ArrayList<>())
                        .add(employee.empId());
            }
        }

        return employees.stream()
                .map(Employee::empId)
                .filter(managerId -> countDescendants(managerId, childrenByManager)
                        > REPORT_THRESHOLD)
                .toList();
    }

    private static int countDescendants(
            String managerId, Map<String, List<String>> childrenByManager) {
        Set<String> descendants = new HashSet<>();
        ArrayDeque<String> pending = new ArrayDeque<>(
                childrenByManager.getOrDefault(managerId, List.of()));

        while (!pending.isEmpty()) {
            String childId = pending.removeFirst();
            if (childId.equals(managerId) || !descendants.add(childId)) {
                continue;
            }
            pending.addAll(childrenByManager.getOrDefault(childId, List.of()));
        }
        return descendants.size();
    }

    /** Idiomatic Java LRU variant; access-order reads update recency. */
    public static final class LruCache<K, V> extends LinkedHashMap<K, V> {
        private final int capacity;

        public LruCache(int capacity) {
            super(capacity, 0.75f, true);
            if (capacity <= 0) throw new IllegalArgumentException("capacity");
            this.capacity = capacity;
        }

        @Override
        protected boolean removeEldestEntry(Map.Entry<K, V> eldest) {
            return size() > capacity;
        }
    }
}
