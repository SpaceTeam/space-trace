# Scripts

Here are some scripts used in development, they are not part of the server per
se.

All sql scripts can be inserted with [`sqlite3`](https://sqlite.org/cli.html).

**TIPP:** When working on the production database, please for the love of
saitan **user transactions**!
([Obligatory Tom Scott Video](https://www.youtube.com/watch?v=X6NJkWbM1xk))

Example of how to responsible work in production:

```bash
$ sqlite3 instance/trace.db
sqlite> .changes on
sqlite> BEGIN;
changes:   0   total_changes: 0
sqlite> UPDATE users
   ...> SET vaccinated_till = date(vaccinated_till, '-90 days')
   ...> WHERE vaccinated_till NOT NULL;
changes:  24   total_changes: 24
sqlite> ROLLBACK; --or COMMIT; if you want to keep the changes.
changes:  24   total_changes: 24
sqlite> ^D
$
```

## decrement_dates.sql

This sql statement decrements the expiration dates of all vaccines in case
the goverment changes those dates.
