Create a Python script /app/transform.py that processes CSV files with complex data transformations and validations. The script must handle real-world data cleaning, aggregation, and format conversion tasks.

The /app/transform.py script should:
- Take a CSV file path as the first command-line argument
- Take an output JSON file path as the second argument
- Read the CSV file with proper encoding handling (UTF-8)
- Perform ALL of the following transformations and validations:

DATA CLEANING:
- Remove rows with ANY missing/empty required fields (id, name, email, age, salary, department, join_date)
- Remove duplicate rows based on 'id' field (keep first occurrence)
- Trim whitespace from all string fields (including leading/trailing spaces)
- Validate email format (must contain @ and domain with proper structure)
- Validate age is between 18 and 100 (inclusive - boundary values must be accepted)
- Validate salary is positive number (must be > 0, not >= 0)
- Validate join_date format is YYYY-MM-DD (must handle leap years correctly)
- Age must be an integer (reject decimal values)
- If all rows are invalid due to data validation errors (bad email, age out of range, etc.), return success (exit code 0) with empty employees array
- NOTE: This is different from CSV parsing errors (see ERROR HANDLING) - malformed CSV structure should return exit code 1

DATA TRANSFORMATIONS:
- Convert all department names to uppercase (regardless of original case)
- Calculate years_of_service from join_date to 2024-01-01 (handle fractional years, round to 2 decimals)
- Add salary_category field: "low" (<50000), "medium" (50000-100000 inclusive), "high" (>100000)
- Add age_group field: "young" (18-30 inclusive), "mid" (31-50 inclusive), "senior" (51+)
- Normalize email to lowercase (preserve unicode characters in names)

AGGREGATIONS (compute and add to output):
- Total number of valid employees after cleaning
- Average salary by department (rounded to 2 decimals)
- Employee count by age_group
- Employee count by salary_category
- Department with highest average salary
- Oldest and youngest employee ages

OUTPUT FORMAT (JSON):
{
  "employees": [
    {
      "id": string,
      "name": string,
      "email": string (lowercase),
      "age": int,
      "salary": float,
      "department": string (uppercase),
      "join_date": string (YYYY-MM-DD),
      "years_of_service": float (rounded to 2 decimals),
      "salary_category": string ("low"|"medium"|"high"),
      "age_group": string ("young"|"mid"|"senior")
    }
  ],
  "statistics": {
    "total_employees": int,
    "avg_salary_by_dept": {dept: float},  // department names are uppercase
    "count_by_age_group": {group: int},
    "count_by_salary_category": {category: int},
    "highest_paying_dept": string,
    "age_range": {"min": int, "max": int}
  }
}

ERROR HANDLING:
- Return exit code 1 if wrong number of command-line arguments provided (expect exactly 2 arguments)
- Return exit code 1 if input file doesn't exist
- Return exit code 1 if CSV has wrong/missing required columns (must have: id, name, email, age, salary, department, join_date)
- Return exit code 1 if CSV parsing fails (due to structural errors like unclosed quotes, inconsistent column counts, invalid CSV format)
- Return exit code 1 if output file cannot be written
- Print descriptive error messages to stderr for all error cases (must contain "error" and describe the specific problem)
