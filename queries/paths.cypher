MATCH p=(a:Location {id:$source})-[:TRAVEL*1..12]->(b:Location {id:$target})
WHERE ALL(n IN nodes(p) WHERE SINGLE(m IN nodes(p) WHERE m.id=n.id))
  AND ALL(e IN relationships(p) WHERE
    (e.road=$override AND $assume_open=true) OR
    (e.road<>$override AND e.status='VERIFIED_OPEN' AND e.valid_until>$now))
WITH p, reduce(t=0,e IN relationships(p) | t+e.minutes) AS cost
RETURN [n IN nodes(p) | n.id], [e IN relationships(p) | e.road], cost
ORDER BY cost, [e IN relationships(p) | e.road] LIMIT 6
