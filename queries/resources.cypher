MATCH (v:Vehicle) OPTIONAL MATCH (a:Assignment)-[:USES_VEHICLE]->(v)
WITH collect(DISTINCT v.data) AS vehicles,collect(DISTINCT a.data) AS assignments
MATCH (d:Stock) OPTIONAL MATCH (r:Reservation)-[:HOLDS]->(d)
RETURN vehicles,assignments,collect(DISTINCT d.data),collect(DISTINCT r.data)
