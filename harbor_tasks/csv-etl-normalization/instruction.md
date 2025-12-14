Fix the Python ETL script located at the absolute path /app/process.py.

The script must read all CSV files under the absolute directory /app/data/
and produce a consolidated JSON array at the absolute path
/app/output/data.json.

All validation will be performed using runtime execution and output checks.

Input handling requirements:

- The script must process all files matching /app/data/*.csv.
- All file paths used or referenced by the script must be absolute.
- Only Python standard-library modules may be used.

Encoding and parsing requirements:
- For UTF-16 CSV files without a BOM, the file must still be decoded correctly and deterministically.

- Supported encodings include:
    * UTF-8
    * UTF-8 with BOM
    * UTF-16LE and UTF-16BE, with or without a BOM
- Encoding must be detected dynamically and decoded without crashing.
- CSV delimiters may be comma (,), semicolon (;), or tab (\t) and must be
  detected dynamically.
- Line endings may be LF, CRLF, or CR and must be normalized.
- Missing final EOF newlines must be tolerated.
- Empty rows must be ignored.
- Missing fields must be treated as empty strings.
- Header names must be preserved exactly as they appear in the CSV.
- **Header order must be preserved when emitting JSON objects.**
- All emitted JSON values must be strings.

Error handling requirements:

- Files that cannot be read due to filesystem permissions must be skipped.
- Skipping unreadable files must not terminate the script.
- CSV decoding or parsing errors in one file must not affect others.
- The script must never crash due to UnicodeDecodeError or ValueError.

Exit code requirements:

- The script must exit with status code 0 if it completes without crashing,
  even if all CSV files are unreadable or skipped.
- No non-zero exit code is permitted for input-related issues.

Output requirements:

- The directory /app/output/ must be created if it does not exist.
- The file /app/output/data.json must always be written.
- The output must be a single JSON array containing all successfully parsed
  rows from all readable CSV files.
