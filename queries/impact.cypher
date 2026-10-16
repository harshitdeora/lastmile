MATCH (road:Road {id:$road})
OPTIONAL MATCH (report:Report)-[:DESCRIBES]->(road)
OPTIONAL MATCH (a:Assignment)-[:USES]->(road)
WHERE a.state IN ['reserved','in_transit','blocked']
OPTIONAL MATCH (a)-[:FULFILLS]->(q:DeliveryRequest)
RETURN road.id, collect(DISTINCT report.id), collect(DISTINCT a.id), collect(DISTINCT q.id)
