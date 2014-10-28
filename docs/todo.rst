What still needs to be done
---------------------------

For version 1.0
...............

- Test if a stale cache issue happens when a table is invalidated
  exactly during a SQL read query
- Write tests for `multi-table inheritance <https://docs.djangoproject.com/en/1.7/topics/db/models/#multi-table-inheritance>`_
- Test if code injections can occur when unpickling query results
  (or use a safer serialization tool)

In a more distant future
........................

- Add a setting to choose if we cache ``QuerySet.order_by('?')``
- Use ``connection.introspection.table_names()`` to detect which tables
  are implied in a ``QuerySet.extra``
