What still needs to be done
---------------------------

For version 1.0
...............

- Test if a stale cache issue happens when a table is invalidated
  exactly during a SQL read query
- Test if code injections can occur when unpickling query results
  (or use a safer serialization tool)

In a more distant future
........................

- Use ``connection.introspection.table_names()`` to detect which tables
  are implied in a ``QuerySet.extra``
