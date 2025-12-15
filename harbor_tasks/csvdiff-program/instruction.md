Create an executable Python program at the absolute path `/app/csvdiff.py`.

The script must:
  - Accept command-line arguments of the form:
      --old <absolute path to the previous CSV file, e.g., /app/old.csv>
      --new <absolute path to the current CSV file, e.g., /app/new.csv>
      --keys <one or more column names forming the composite primary key>
      --output <optional absolute path; default: /app/output/changes.json>

    The task instructions ONLY mention absolute paths (e.g., `/app/old.csv`,
    `/app/new.csv`, `/app/output/changes.json`). The script itself may accept
    any path provided by the user, but this task description must not use
    relative paths anywhere.

  - Read both CSV files using robust CSV parsing:
      * Trim leading/trailing whitespace from all column/header names before any comparison or key matching
      * UTF-8 or UTF-8 with BOM
      * Trim leading/trailing whitespace from all field values
      * Tolerate differing column orders between CSV files
      * Missing fields must be treated as empty strings
      * When the old and new CSV files have different column sets , the tool must take the union of all columns and treat any missing fields as empty strings
      * Use Python's standard `csv` module

  - Build a composite primary key using the columns listed after `--keys`
    (in the exact order provided).

  - Compare row sets from the “old” and “new” CSV files and determine:
      * `"added"`   – rows present in the new CSV but not in the old
      * `"removed"` – rows present in the old CSV but not in the new
      * `"updated"` – rows where the composite key exists in both files,
                      but at least one non-key field value differs.
        Each `"updated"` entry must contain:
           {
             "key": { "<keycol>": "<value>", ... },
             "old": { ... entire old row ... },
             "new": { ... entire new row ... }
           }

  - Write a JSON report to the exact absolute path:
      `/app/output/changes.json`
    The directory `/app/output/` must be created if it does not exist.
    All values in the JSON output (including numeric-looking values such as IDs or ages) must be serialized strictly as strings.


    The JSON structure must be:
      {
        "added":   [ { ... }, ... ],
        "removed": [ { ... }, ... ],
        "updated": [
          {
            "key": { ... },
            "old": { ... },
            "new": { ... }
          },
          ...
        ]
      }

  - Exit codes:
      * 0  – no differences found
      * 2  – any added/removed/updated rows are present
      * 3  – usage errors, missing files, unreadable CSV, or malformed arguments

Deliverables required in the workspace:
  - /app/csvdiff.py (Python script with executable permission bit set)
  - `/app/output/changes.json`   (created by running the script)

All file paths appearing in these task instructions MUST be absolute
(starting with `/app/`). No relative paths may appear anywhere.
