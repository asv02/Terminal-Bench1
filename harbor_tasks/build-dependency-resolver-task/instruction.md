Your task is to implement a deterministic build dependency resolver that handles semantic versioning constraints.

The agent must write a single Python file at `/app/output/resolver.py`. This file must define a function :

    def resolve_dependencies(manifest: str) -> str

The function takes a JSON string representing a dependency manifest and returns a JSON string containing the resolution result.

Input manifest format:
  {
    "packages": {
      "<package_name>": {
        "versions": ["1.0.0", "1.1.0", "2.0.0", ...],
        "dependencies": {
          "<version>": {
            "<dep_name>": "<version_constraint>"
          }
        }
      }
    },
    "root_dependencies": {
      "<package_name>": "<version_constraint>"
    }
  }

Version constraints follow semantic versioning with these operators:
  - Exact: "1.2.3" (must be exactly this version)
  - Caret: "^1.2.3" (compatible with 1.2.3, allows versions >=1.2.3 <2.0.0)
  - Tilde: "~1.2.3" (allows patch-level changes: 1.2.x where x >= 3)
  - Range: ">=1.0.0 <2.0.0" (must satisfy both bounds)
  - Wildcard: "1.2.*" (any patch version of 1.2)
  - Or: "1.0.0 || 2.0.0" (either version)

Output format (success):
  {
    "status": "resolved",
    "resolved": {
      "<package_name>": "<resolved_version>"
    },
    "build_order": ["<package_name>", ...]
  }

Output format (conflict):
  {
    "status": "conflict",
    "error": "<description of the conflict>",
    "conflicting_packages": ["<pkg1>", "<pkg2>", ...]
  }

Conflict conditions:
  - Incompatible version constraints on a shared dependency 
  - Missing package: a dependency references a package that does not exist in the packages registry
  - Empty registry: root_dependencies references packages that are not available in the packages registry
  - Invalid JSON: if the input manifest string is not valid JSON, return a conflict with an error message indicating "Invalid JSON"

Output format (cycle detected):
  {
    "status": "cycle",
    "error": "Circular dependency detected",
    "cycle": ["<pkg1>", "<pkg2>", ..., "<pkg1>"]
  }

Requirements:
  - Resolution must be fully deterministic: same input always produces identical output.
  - When multiple versions satisfy constraints, prefer the highest compatible version.
  - The build_order must be a valid topological sort of the dependency graph.
  Build order rule: For every dependency edge pkg → dep, the dependency must appear before the dependent package in build_order (i.e., dep precedes pkg).
  - All transitive dependencies must be resolved.
  - Version comparison must follow semantic versioning rules (major.minor.patch).
  - Pre-release versions (e.g., "1.0.0-alpha") are only selected if explicitly requested (A pre-release version is considered explicitly requested only when the version constraint exactly matches that pre-release (e.g., "1.0.0-alpha")).

Security and sandboxing constraints:
  - The submission file may only import: `json`, `re`, and `math`.
  - Any other import is forbidden.
  - The code must not use file, network, or process APIs.
  - The code must not call `eval`, `exec`, `compile`, `input`, `__import__`.
  - The code must not access dunder attributes.

Size constraints:
  - The Python source file must be at most 15 KB.
  - Output JSON must be at most 100 KB.

Error handling:
  - Invalid JSON input: if the manifest string is not valid JSON, return a conflict status with an error message containing "Invalid JSON".
  - Missing packages: if a dependency references a package that does not exist in the packages registry, return a conflict status with an error message identifying the missing package.
  - Empty registry: if root_dependencies references packages that are not available in the packages registry (empty or missing), return a conflict status with an error message identifying the unavailable package(s).
  - For conflict errors, the error message must mention at least one conflicting package name.

The tests will: 
  - Validate AST for forbidden imports and operations.
  - Test with simple dependency trees to verify basic resolution.
  - Test with complex version constraints to verify semver parsing.
  - Test with diamond dependencies to verify conflict detection.
  - Test with circular dependencies to verify cycle detection.
  - Test with large dependency graphs to verify performance and correctness.
  - Verify determinism by running the same input multiple times.
  - Verify build order is a valid topological sort.
  - Test error handling for invalid JSON input, missing packages, and empty registry scenarios.
  

  
