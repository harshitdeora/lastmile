MATCH (s:Snapshot) RETURN s.revision,s.time,s.data ORDER BY s.revision
