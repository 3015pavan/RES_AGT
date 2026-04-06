# Migrations Package

This folder stores migration package markers used by the startup migration guard.

Current package:

- 001_unified_schema.sql

Operational flow:

1. Run app/db/sql/schema.sql in Supabase SQL editor.
2. Ensure schema_migrations has matching version rows.
3. Startup /ready check verifies required versions are present.
