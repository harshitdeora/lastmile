MATCH (root:Run {id:$id}) WHERE root.revision=$expected
OPTIONAL MATCH (legacy:Stock) WHERE legacy.id IN ['d1','d2','d3']
WITH root,collect(legacy) AS obsolete
FOREACH (n IN obsolete | DETACH DELETE n)
SET root.data=$metadata,root.revision=$revision
FOREACH (row IN $locations | MERGE (n:Entity:Location {id:row.id}) SET n=row.props)
FOREACH (row IN $roads | MERGE (n:Entity:Road {id:row.id}) SET n=row.props)
FOREACH (row IN $requests | MERGE (n:Entity:DeliveryRequest {id:row.id}) SET n=row.props)
FOREACH (row IN $depots | MERGE (n:Entity:Stock {id:row.id}) SET n=row.props)
FOREACH (row IN $vehicles | MERGE (n:Entity:Vehicle {id:row.id}) SET n=row.props)
FOREACH (row IN $reports | MERGE (n:Entity:Report {id:row.id}) SET n=row.props)
FOREACH (row IN $assignments | MERGE (n:Entity:Assignment {id:row.id}) SET n=row.props)
FOREACH (row IN $reservations | MERGE (n:Entity:Reservation {id:row.id}) SET n=row.props)
FOREACH (row IN $inspections | MERGE (n:Entity:Inspection {id:row.id}) SET n=row.props)
FOREACH (row IN $plans | MERGE (n:Entity:Plan {id:row.id}) SET n=row.props)
FOREACH (row IN $decisions | MERGE (n:Entity:Decision {id:row.id}) SET n=row.props)
FOREACH (row IN $events | MERGE (n:Entity:Event {id:row.id}) SET n=row.props)
FOREACH (e IN $edges |
                MERGE (a:Entity:Location {id:e.a}) MERGE (b:Entity:Location {id:e.b})
                MERGE (r:Entity:Road {id:e.id})
                MERGE (a)-[t:TRAVEL {road:e.id}]->(b)
                SET t.status=e.status,t.minutes=e.minutes,t.valid_until=e.valid_until
                MERGE (r)-[:CONNECTS]->(a) MERGE (r)-[:CONNECTS]->(b))
FOREACH (e IN $reverse |
                MERGE (a:Entity:Location {id:e.a}) MERGE (b:Entity:Location {id:e.b})
                MERGE (r:Entity:Road {id:e.id})
                MERGE (a)-[t:TRAVEL {road:e.id}]->(b)
                SET t.status=e.status,t.minutes=e.minutes,t.valid_until=e.valid_until
                MERGE (r)-[:CONNECTS]->(a) MERGE (r)-[:CONNECTS]->(b))
FOREACH (e IN $rel_DESCRIBES | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:DESCRIBES]->(b))
FOREACH (e IN $rel_DESTINATION | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:DESTINATION]->(b))
FOREACH (e IN $rel_USES | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:USES]->(b))
FOREACH (e IN $rel_FULFILLS | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:FULFILLS]->(b))
FOREACH (e IN $rel_USES_VEHICLE | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:USES_VEHICLE]->(b))
FOREACH (e IN $rel_PART_OF | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:PART_OF]->(b))
FOREACH (e IN $rel_HOLDS | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:HOLDS]->(b))
FOREACH (e IN $rel_FOR | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:FOR]->(b))
FOREACH (e IN $rel_BASED_ON | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:BASED_ON]->(b))
FOREACH (e IN $rel_AFFECTS | MERGE (a:Entity {id:e.a}) MERGE (b:Entity {id:e.b}) MERGE (a)-[:AFFECTS]->(b))
CREATE (:Snapshot {id:$snapshot_id,revision:$revision,time:$time,data:$snapshot}) RETURN root.revision
