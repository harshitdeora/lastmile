MATCH p=(d:Location)-[:TRAVEL*1..12]->(s:Location)<-[:DESTINATION]-(q:DeliveryRequest)
WHERE d.kind='depot' AND q.status='outstanding'
  AND ALL(n IN nodes(p) WHERE SINGLE(m IN nodes(p) WHERE m.id=n.id))
UNWIND relationships(p) AS edge
WITH edge.road AS road,collect(DISTINCT q.id) AS requests
RETURN road,requests,size(requests) AS affected ORDER BY affected DESC,road LIMIT 25
