-- JPMorgan practice: managers with more than five reports.
-- PostgreSQL syntax; the employee table models a self-referencing hierarchy.

CREATE TABLE employees (
    empid INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    managerid INTEGER REFERENCES employees (empid)
);

INSERT INTO employees (empid, name, managerid) VALUES
    (1,  'Alice',  NULL),
    (2,  'Bob',     1),
    (3,  'Carol',   2),
    (4,  'David',   2),
    (5,  'Emma',    2),
    (6,  'Frank',   2),
    (7,  'Grace',   2),
    (8,  'Henry',   2),
    (9,  'Irene',   2),
    (10, 'Jack',    3),
    (11, 'Kate',    3),
    (12, 'Leo',     3),
    (13, 'Maya',    3),
    (14, 'Nina',    3),
    (15, 'Omar',    3),
    (16, 'Paula',   4);

-- Direct reports: group immediate children by manager.
SELECT managerid, COUNT(*) AS direct_report_count
FROM employees
WHERE managerid IS NOT NULL
GROUP BY managerid
HAVING COUNT(*) > 5
ORDER BY managerid;

-- Include manager details and exclude any self-managed root rows if present.
SELECT manager.empid, manager.name, COUNT(*) AS direct_report_count
FROM employees report
JOIN employees manager ON manager.empid = report.managerid
WHERE report.managerid IS NOT NULL
  AND report.empid <> report.managerid
GROUP BY manager.empid, manager.name
HAVING COUNT(*) > 5
ORDER BY manager.empid;

-- Indirect reports: recursively walk every manager's descendants.
WITH RECURSIVE hierarchy AS (
    SELECT empid AS manager_empid, empid AS subordinate_empid, 0 AS depth
    FROM employees

    UNION ALL

    SELECT hierarchy.manager_empid, child.empid, hierarchy.depth + 1
    FROM hierarchy
    JOIN employees child ON child.managerid = hierarchy.subordinate_empid
    WHERE child.empid <> child.managerid
)
SELECT manager.empid,
       manager.name,
       COUNT(DISTINCT hierarchy.subordinate_empid) AS descendant_count
FROM hierarchy
JOIN employees manager ON manager.empid = hierarchy.manager_empid
WHERE hierarchy.depth > 0
GROUP BY manager.empid, manager.name
HAVING COUNT(DISTINCT hierarchy.subordinate_empid) > 5
ORDER BY manager.empid;
