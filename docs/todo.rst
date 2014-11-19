What still needs to be done
---------------------------

For version 1.0
...............

- Cache raw queries

Weaknesses to be tested
.......................

- A stale cache issue should never happen when a table is invalidated
  exactly during a SQL read query (fixed, but never tested in the test suite)
