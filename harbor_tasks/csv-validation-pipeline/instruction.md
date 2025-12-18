Create a Python CLI tool at /app/pipeline.py.

The tool processes structured data files, validates records against a JSON schema by enforcing required fields and basic type presence (full JSON Schema constraint enforcement is not required), ingests valid records into a SQLite database, and produces deterministic artifacts.

1. Input Monitoring

- Monitor the directory /app/incoming for input files.

- Only files with extensions .csv or .json must be considered.

- Files are processed once per execution (no daemon or watcher behavior).

2. File Processing Semantics (Authoritative)

- The archive directory is the sole source of truth for file processing state.

- A file in /app/incoming MUST be processed only if there is no file in
/app/archive/ with the same original filename and the suffix .processed.

- A file is considered already processed if a corresponding <original_name>.*.processed file exists in /app/archive/.

- Pre-existing files in /app/incoming that already have a .processed archive entry
MUST be ignored.

- No timestamp comparison, database inspection, state files, checksums, or other tracking
mechanisms may be used.

3. Schema Validation and Normalization

- A JSON schema is provided at /app/schema.json.

- Validation Rules

- Records violating the schema must not be ingested.

- All schema violations must be written to /app/errors.log.

- For each schema violation, the error log entry must include a
  human-readable description of the failure, including the phrase
  "missing required field" when a required field is absent.

Normalization Rules

- The database table name must exactly equal schema["title"].

- Table columns must exactly match the schema’s properties.

- Missing optional fields must be inserted as NULL.

- Extra fields must be dropped before insertion.

- Deduplication applies within a single input file only, based on the fully
normalized record.

4. Database Ingestion

- Use a SQLite database at /app/data.db.

- Tables must be created automatically from the schema.

- If new fields appear in later schema versions, schema migration must be performed
using ALTER TABLE ADD COLUMN.

- Column order must follow the property order defined in the schema.

- The database may persist across executions, but ingestion must be idempotent per file
based solely on archive state.

5. Archiving Processed Files

After processing each input file:

- Rename the file to
<original_name>.<UTC_TIMESTAMP>.processed

- Move the renamed file into /app/archive/

- The timestamp must be in UTC.

6. Generated Outputs

The tool must generate:

Summary Report

- A CSV file at /app/report.csv containing one row per processed file with columns:

   - filename, total_records, ingested_records, rejected_records

Error Log

- An error log at /app/errors.log listing all schema violations.

7. Additional Requirements

- All filesystem paths must be absolute.

- The pipeline must be deterministic.

- The pipeline must be idempotent per file.

- No external services, networking, or internet access may be used.

Notes

- Archive state always takes precedence over filesystem timestamps or database state.

- The implementation must rely only on the presence or absence of .processed files
in /app/archive/ to determine whether a file should be processed.
