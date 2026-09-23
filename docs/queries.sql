-- Latest 20 violations
SELECT * FROM violations ORDER BY started_at DESC LIMIT 20;

-- Violation count by type
SELECT violation_type, COUNT(*) FROM violations GROUP BY violation_type ORDER BY COUNT(*) DESC;

-- Violation count by camera (JOIN to get camera name)
SELECT c.name, COUNT(*)
FROM violations v
JOIN cameras c ON v.camera_id = c.id
GROUP BY c.name
ORDER BY COUNT(*) DESC;

-- Violations per hour
SELECT DATE_TRUNC('hour', started_at) AS hour, COUNT(*)
FROM violations
GROUP BY hour
ORDER BY hour DESC
LIMIT 20;

-- NOTE: true "compliance rate" needs total checks (compliant + non-compliant),
-- not just violations. Current schema only stores violations. Revisit once
-- the CV pipeline (Week 2) provides total detection counts per camera.
