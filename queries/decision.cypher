MATCH (d:Decision {id:$decision})
OPTIONAL MATCH (d)-[:BASED_ON]->(e:Entity)
OPTIONAL MATCH (d)-[:AFFECTS]->(p:Plan)
RETURN d.data,collect(DISTINCT e.id),collect(DISTINCT p.id)
