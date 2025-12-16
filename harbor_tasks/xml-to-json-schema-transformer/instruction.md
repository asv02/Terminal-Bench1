# XML Schema to JSON Schema Transformer

Create a command-line tool that converts XML Schema Definition (XSD) files into JSON Schema (Draft 7) format. The tool must handle common XSD constructs and produce valid, semantically equivalent JSON schemas.

## Implementation Requirements

**File Location**: `/app/transformer.py`

**Command-Line Interface**:
```bash
python /app/transformer.py --input <xsd-file> --output <json-schema-file>
```

The tool must:
- Read an XSD file from the `--input` path
- Parse and transform it to JSON Schema Draft 7
- Write the resulting JSON schema to the `--output` path
- Exit with code 0 on success, non-zero on error

## XSD Features to Support

### 1. Simple Types and Built-in Types

Map XSD built-in types to JSON Schema types:

- `xs:string` → `"type": "string"`
- `xs:integer`, `xs:int`, `xs:long`, `xs:short` → `"type": "integer"`
- `xs:decimal`, `xs:float`, `xs:double` → `"type": "number"`
- `xs:boolean` → `"type": "boolean"`
- `xs:date`, `xs:dateTime`, `xs:time` → `"type": "string"` with `"format": "date"`, `"date-time"`, or `"time"`

### 2. Elements

Transform `xs:element` declarations:
- Element name → JSON property name
- Element type → corresponding JSON type
- `minOccurs="0"` → property is NOT in `required` array
- `minOccurs="1"` or unspecified → property IS in `required` array
- `maxOccurs="unbounded"` → `"type": "array"` with `"items"` containing the element type
- **Array creation rule**: Elements with `maxOccurs` > 1 (including `"unbounded"`) are represented as arrays. **IMPORTANT**: `maxOccurs="1"` (or unspecified, which defaults to 1) does NOT create an array - it creates a regular single-valued property.
- If an element is represented as an array and its `minOccurs` is a positive integer (i.e., `minOccurs >= 1`, including `minOccurs="1"`), include `"minItems": <minOccurs>`.

Elements may have inline type definitions or reference named/built-in types. Your transformer must correctly resolve and process all cases.

### 3. Attributes

Transform `xs:attribute` declarations:
- Attribute name → JSON property name (no special prefix needed)
- Attribute type → corresponding JSON type
- `use="required"` → property IS in `required` array
- `use="optional"` or unspecified → property is NOT in `required` array
- Default values: `default="value"` → `"default": value` in JSON schema (convert to appropriate JSON type: integers to int, decimals to float, "true"/"false" to boolean, otherwise string)

Attributes may reference built-in types, named types, or contain inline type definitions. Your transformer must resolve these correctly, including any restrictions or facets defined by simpleTypes. If an attribute references an unknown named type, exit with code 1.

### 4. Complex Types

Transform `xs:complexType` to JSON Schema objects. Complex types may contain sequences of elements, attributes, or combinations thereof. Nested elements become nested properties in the JSON schema.

### 5. Choice Groups

Transform `xs:choice` to JSON Schema `oneOf`:

```xml
<xs:choice>
  <xs:element name="email" type="xs:string"/>
  <xs:element name="phone" type="xs:string"/>
</xs:choice>
```
→
```json
{
  "oneOf": [
    {
      "type": "object",
      "properties": {"email": {"type": "string"}},
      "required": ["email"]
    },
    {
      "type": "object",
      "properties": {"phone": {"type": "string"}},
      "required": ["phone"]
    }
  ]
}
```

**Requirements for xs:choice:**
- Each element in the choice becomes a separate option in a `oneOf` array
- Each option is an object schema containing one property (the choice element)
- Array transformation rules apply: if a choice element has `maxOccurs` > 1, it becomes an array with `minItems` when `minOccurs >= 1`
- Elements with `minOccurs="0"` are not included in the option's `required` array
- When the root element contains only a choice (no sequence wrapper), the `oneOf` is hoisted to root level (see Section 13)

### 6. List Types

Transform `xs:list` to JSON Schema arrays:

```xml
<xs:simpleType name="integerList">
  <xs:list itemType="xs:integer"/>
</xs:simpleType>
```
→
```json
{
  "type": "array",
  "items": {"type": "integer"}
}
```

**Requirements for xs:list:**
- Lists become JSON Schema arrays (`"type": "array"`)
- The item type can be specified via `itemType` attribute or inline `xs:simpleType`
- If neither exists, default to string items
- Inline simpleTypes may contain restrictions that must be applied to the items schema

### 7. Nillable Elements

Elements with `nillable="true"` must allow null values using `"type": ["string", "null"]` (or other base type instead of string).

### 8. Element Default Values

Elements with `default="value"` attributes must include `"default": value` in the JSON schema, with the value converted to the appropriate JSON type.

### 9. Restrictions and Facets

Transform `xs:restriction` facets to JSON Schema validation. Restrictions can appear in two forms:

**Form 1: Within simpleType (most common)**
```xml
<xs:element name="zipcode">
  <xs:simpleType>
    <xs:restriction base="xs:string">
      <xs:pattern value="[0-9]{5}"/>
    </xs:restriction>
  </xs:simpleType>
</xs:element>
```

**Form 2: Named simpleType**
```xml
<xs:simpleType name="zipcodeType">
  <xs:restriction base="xs:string">
    <xs:pattern value="[0-9]{5}"/>
  </xs:restriction>
</xs:simpleType>
```

**Processing restrictions:**
1. Find the `xs:restriction` element within `xs:simpleType`
2. Get the `base` attribute (e.g., `base="xs:string"`) to determine the JSON type
3. **Check if `base` is a named simpleType** (for restriction chains - see below)
4. Extract all child facet elements (minLength, pattern, etc.)
5. Start with the JSON type from the base, then add validation constraints

**Restriction Chains (Important):**

When a `simpleType` restricts another named `simpleType` (which itself restricts a base type), ALL constraints from the chain must be inherited and merged:

```xml
<xs:simpleType name="basicString">
  <xs:restriction base="xs:string">
    <xs:minLength value="5"/>
    <xs:maxLength value="50"/>
  </xs:restriction>
</xs:simpleType>

<xs:simpleType name="patternedString">
  <xs:restriction base="basicString">
    <xs:pattern value="[A-Z][a-z0-9]+"/>
  </xs:restriction>
</xs:simpleType>

<xs:simpleType name="strictString">
  <xs:restriction base="patternedString">
    <xs:maxLength value="20"/>
  </xs:restriction>
</xs:simpleType>
```

The final `strictString` type must have:
- `minLength: 5` (from basicString)
- `maxLength: 20` (from strictString, overriding basicString's 50)
- `pattern: "[A-Z][a-z0-9]+"` (from patternedString)

**Processing steps for restriction chains:**
1. If `base` attribute references a named simpleType in the type registry, start with a COPY of that schema
2. Apply the facets from the current restriction (overriding where applicable)
3. This ensures constraints are inherited and merged down the restriction chain

**Facet mappings:**
- `xs:minLength` → `"minLength": value` (convert value to integer)
- `xs:maxLength` → `"maxLength": value` (convert value to integer; later restrictions can make this MORE restrictive)
- `xs:pattern` → `"pattern": "regex"` (use the pattern value exactly as-is - see Pattern Preservation below)
- `xs:minInclusive` → `"minimum": value` (convert to number)
- `xs:minExclusive` → `"minimum": value` and `"exclusiveMinimum": true` (convert to number; use the original value from the XSD as-is for "minimum")
- `xs:maxInclusive` → `"maximum": value` (convert to number)
- `xs:maxExclusive` → `"maximum": value` and `"exclusiveMaximum": true` (convert to number; use the original value from the XSD as-is for "maximum")
- `xs:enumeration` → collect all enumeration values into `"enum": [value1, value2, ...]` array

**Pattern Preservation:**
When transforming `xs:pattern` facets, the regex pattern value MUST be preserved exactly as written in the XSD. Do NOT normalize, simplify, or modify the pattern in any way (e.g., do not convert `[0-9]` to `\d`, do not add anchors like `^` or `$`, etc.).

**Note on exclusive bounds**: For `xs:minExclusive value="0"`, output `"minimum": 0, "exclusiveMinimum": true`. The minimum value is the boundary itself (0), and the exclusiveMinimum flag indicates values must be strictly greater than this boundary. The same applies for maxExclusive.

**Example transformation:**
```xml
<xs:element name="age">
  <xs:simpleType>
    <xs:restriction base="xs:integer">
      <xs:minInclusive value="0"/>
      <xs:maxInclusive value="150"/>
    </xs:restriction>
  </xs:simpleType>
</xs:element>
```
→
```json
{
  "type": "integer",
  "minimum": 0,
  "maximum": 150
}
```

### 10. Named Type Definitions and References

XSD schemas can define reusable named types that are referenced by elements and attributes.

**Step 1: Build a Type Registry**

Before processing the root element, scan the schema and build a registry of all named types:

```xml
<!-- Named simpleType definition -->
<xs:simpleType name="ageType">
  <xs:restriction base="xs:integer">
    <xs:minInclusive value="0"/>
    <xs:maxInclusive value="150"/>
  </xs:restriction>
</xs:simpleType>

<!-- Named complexType definition -->
<xs:complexType name="addressType">
  <xs:sequence>
    <xs:element name="street" type="xs:string"/>
    <xs:element name="city" type="xs:string"/>
  </xs:sequence>
</xs:complexType>
```

**Processing steps:**
1. Find all `<xs:simpleType name="...">` elements at the schema level
2. For each, process the simpleType and store the result in a dictionary keyed by the name
3. Find all `<xs:complexType name="...">` elements at the schema level  
4. For each, process the complexType and store the result in a dictionary keyed by the name

**Step 2: Resolve Type References**

When processing an element or attribute with a `type="typeName"` attribute:

```xml
<xs:element name="age" type="ageType"/>
<xs:element name="address" type="addressType"/>
```

1. Extract the type name (strip `xs:` or `xsd:` prefix if present)
2. Check if it's a built-in type (string, integer, etc.) - if so, use the standard mapping
3. If not built-in, look up the type name in your named simpleType registry
4. If not found there, look up in your named complexType registry
5. If found, use the stored schema definition for that named type
6. If not found anywhere, treat as an error and exit with code 1

**Important:** When using a named type definition, make a copy of the stored schema to avoid modifying the cached version.

**Handling unknown named types:**

If an element or attribute references a type name that:
- Is not a built-in XSD type (like xs:string, xs:integer, etc.)
- Is not found in your named simpleType registry
- Is not found in your named complexType registry

Then you should treat this as an error condition and exit with code 1, printing an appropriate error message to stderr. Do not silently default to `{"type": "string"}` for unknown named type references, as this loses validation semantics.

### 11. Type Extension (xs:extension)

XSD supports type inheritance through `xs:extension`, which extends a base type with additional elements or attributes.

**Example:**
```xml
<xs:complexType name="PersonType">
  <xs:sequence>
    <xs:element name="name" type="xs:string"/>
    <xs:element name="age" type="xs:integer"/>
  </xs:sequence>
</xs:complexType>

<xs:complexType name="EmployeeType">
  <xs:complexContent>
    <xs:extension base="PersonType">
      <xs:sequence>
        <xs:element name="employeeId" type="xs:integer"/>
        <xs:element name="department" type="xs:string"/>
      </xs:sequence>
    </xs:extension>
  </xs:complexContent>
</xs:complexType>
```

**Step-by-step implementation algorithm:**

**Step 1: Detect extension structure**
When processing a `<xs:complexType>`, check if it contains:
- A child `<xs:complexContent>` element
- Within that, a child `<xs:extension>` element

If yes, this is a type extension. Otherwise, process as a normal complex type.

**Step 2: Extract base type name**
```python
ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
extension_element = complex_type.find("xs:complexContent/xs:extension", ns)
base_type_name = extension_element.get("base")
```
Remove any `xs:` or `xsd:` prefix from the base type name.

**Step 3: Resolve base type from registry**
```python
if base_type_name not in complex_type_registry:
    # ERROR: Unknown base type
    print(f"Error: Unknown base type '{base_type_name}'", file=sys.stderr)
    sys.exit(1)

base_schema = complex_type_registry[base_type_name].copy()  # Make a deep copy!
```

**CRITICAL:** Detect circular dependencies before resolving:
```python
# Track currently resolving types to detect cycles
resolving_stack = []

def resolve_with_extension(type_name, resolving_stack):
    if type_name in resolving_stack:
        # Circular dependency detected
        print(f"Error: Circular dependency in type extension", file=sys.stderr)
        sys.exit(1)
    
    resolving_stack.append(type_name)
    # ... resolve base type ...
    resolving_stack.pop()
```

**Step 4: Process extension's own content**
The extension element can contain:
- `<xs:sequence>` with elements
- `<xs:choice>` with elements  
- `<xs:attribute>` declarations

Process these exactly as you would for a normal complex type, creating:
- `extension_properties` dict
- `extension_required` list

```python
extension_properties = {}
extension_required = []

# Process sequence if present
sequence = extension_element.find("xs:sequence")
if sequence:
    for element in sequence.findall("xs:element"):
        name = element.get("name")
        # ... process element and add to extension_properties ...
        if element.get("minOccurs") != "0":
            extension_required.append(name)

# Process attributes if present
for attribute in extension_element.findall("xs:attribute"):
    name = attribute.get("name")
    # ... process attribute and add to extension_properties ...
    if attribute.get("use") == "required":
        extension_required.append(name)

```

**Step 4a: Special case — extension with choice must add `oneOf`, and duplicate base/extension fields into each option**

If the `<xs:extension>` contains a direct child `<xs:choice>`, the output schema for the *extended type* must:

1. Keep the "common" (non-choice) fields at the top level as a normal object schema:
  - `"type": "object"`
  - `"properties"` contains all merged base properties plus any non-choice extension properties (from extension sequence and extension attributes)
  - `"required"` contains all required fields from the base type plus any non-choice extension required fields

2. Add a top-level `"oneOf": [...]` describing the choice alternatives.

3. Critically, each `oneOf` option must *duplicate* the common fields into that option:
  - Each option is a `{"type": "object", "properties": ..., "required": ...}` schema
  - Each option's `properties` includes all common properties plus exactly one choice element
  - Each option's `required` includes all common required fields plus the choice element when its `minOccurs` is not `0`

This duplication is required so the base fields (e.g., `id`) are present and required in every `oneOf` alternative.

**Canonical output shape (important):** For an extension-with-choice, the resulting schema is **not** just `{ "oneOf": [...] }`.
It must include the common fields at the top level (`type/properties/required`) **and** include `oneOf`, and also duplicate the
common fields into each `oneOf` option.

This is different from the **root choice hoisting** rule in Section 13, which applies when the root element's complexType contains
only an `xs:choice` (not an `xs:extension`).

**Canonical example (matches expected output):**

Input XSD:
```xml
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:complexType name="BaseType">
    <xs:sequence>
      <xs:element name="id" type="xs:integer"/>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="ExtendedType">
    <xs:complexContent>
      <xs:extension base="BaseType">
        <xs:choice>
          <xs:element name="email" type="xs:string"/>
          <xs:element name="phone" type="xs:string"/>
        </xs:choice>
      </xs:extension>
    </xs:complexContent>
  </xs:complexType>

  <xs:element name="contact" type="ExtendedType"/>
</xs:schema>
```

Output JSON Schema (shape):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "contact",
  "type": "object",
  "properties": {
    "id": {"type": "integer"}
  },
  "required": ["id"],
  "oneOf": [
    {
      "type": "object",
      "properties": {
        "email": {"type": "string"},
        "id": {"type": "integer"}
      },
      "required": ["email", "id"]
    },
    {
      "type": "object",
      "properties": {
        "id": {"type": "integer"},
        "phone": {"type": "string"}
      },
      "required": ["id", "phone"]
    }
  ]
}
```

Implementation sketch (namespace map `ns = {"xs": "http://www.w3.org/2001/XMLSchema"}`):

```python
# Build the "common" part once: base + extension sequence + extension attributes
common_properties = base_schema.get("properties", {}).copy()
common_required = list(base_schema.get("required", []))

for prop_name, prop_schema in extension_properties.items():
  common_properties[prop_name] = prop_schema
for field in extension_required:
  if field not in common_required:
    common_required.append(field)

# If there is a choice inside the extension, expand it into oneOf options
# and also keep the common schema at the top level.
choice = extension_element.find("xs:choice", ns)
if choice is not None:
  options = []
  for element in choice.findall("xs:element", ns):
    opt_properties = common_properties.copy()
    opt_required = list(common_required)

    name = element.get("name")
    opt_properties[name] = resolve_element_schema(element)  # built-in, named, or inline
    if element.get("minOccurs") != "0" and name not in opt_required:
      opt_required.append(name)

    # Apply output ordering rules inside each option
    opt_properties = {k: opt_properties[k] for k in sorted(opt_properties.keys())}
    opt_required = sorted(opt_required)

    options.append({"type": "object", "properties": opt_properties, "required": opt_required})

  # Keep the common fields at the top level
  common_properties = {k: common_properties[k] for k in sorted(common_properties.keys())}
  common_required = sorted(common_required)

  result_schema = {
    "type": "object",
    "properties": common_properties,
    "required": common_required,
    "oneOf": options,
  }
  return result_schema
```


**Step 5: Merge base and extension schemas**
```python
# Start with base schema
merged_properties = base_schema.get("properties", {}).copy()
merged_required = base_schema.get("required", []).copy()

# Add extension properties (overwrites if collision)
for prop_name, prop_schema in extension_properties.items():
    merged_properties[prop_name] = prop_schema

# Add extension required fields
for field in extension_required:
    if field not in merged_required:
        merged_required.append(field)

# Apply alphabetical ordering (Section 13)
sorted_properties = {k: merged_properties[k] for k in sorted(merged_properties.keys())}

result_schema = {
    "type": "object",
    "properties": sorted_properties,
    "required": sorted(merged_required)  # Also sort required array
}
```

**Step 6: Handle property name collisions**
If both base and extension define a property with the same name:
- The extension version **takes precedence** (overwrites the base version)
- This is already handled by the merge algorithm above (dict update)

**Important merge rules:**
- Merge all properties from base and extension types, then apply alphabetical ordering (see Output Format section)
- If a property appears in both (name collision), the extension version takes precedence
- Required fields from base remain required in the extended type
- Required fields from extension are added to the required array

**Example transformation:**
```xml
<xs:element name="employee" type="EmployeeType"/>
```
→
```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer"},
    "employeeId": {"type": "integer"},
    "department": {"type": "string"}
  },
  "required": ["name", "age", "employeeId", "department"]
}
```

**Error handling:**
- If the base type is not found in the type registry, exit with code 1
- If extension creates circular dependencies (A extends B, B extends A), exit with code 1
- xs:restriction within xs:simpleContent is already supported (Section 9), this section covers xs:extension in xs:complexContent

### 12. Union Types (xs:union)

XSD supports union types that allow a value to be one of several types.

**Example:**
```xml
<xs:simpleType name="IDType">
  <xs:union memberTypes="xs:integer xs:string"/>
</xs:simpleType>

<xs:element name="id" type="IDType"/>
```

**Processing xs:union:**

1. Find the `<xs:union>` element within `<xs:simpleType>`
2. Extract the `memberTypes` attribute (space-separated list of type names)
3. For each member type:
   - Resolve it (built-in or named type)
   - Get its JSON schema representation
4. Create an `anyOf` array containing all member type schemas

**Example transformation:**
```xml
<xs:simpleType name="IDType">
  <xs:union memberTypes="xs:integer xs:string"/>
</xs:simpleType>
```
→
```json
{
  "anyOf": [
    {"type": "integer"},
    {"type": "string"}
  ]
}
```

**Multiple member types:**
```xml
<xs:union memberTypes="xs:integer xs:string xs:boolean"/>
```
→
```json
{
  "anyOf": [
    {"type": "integer"},
    {"type": "string"},
    {"type": "boolean"}
  ]
}
```

**Important:** Union types create `anyOf`, while choice groups (Section 5) create `oneOf`. The difference is semantic: `anyOf` means "matches any of these types", while `oneOf` means "matches exactly one alternative structure".

### 13. Root Element

The root `xs:element` in the XSD becomes the top-level schema. The transformation depends on the root element's type:

**All root schemas must include:**
- `"$schema": "http://json-schema.org/draft-07/schema#"`
- `"title"`: MUST be set to the root element name

**Type hoisting rules:**

1. **Simple type root element** (e.g., `type="xs:string"`, `type="xs:integer"`)
   - The primitive type is placed directly at the root level
   - Example: `<xs:element name="message" type="xs:string"/>` →
     ```json
     {
       "$schema": "http://json-schema.org/draft-07/schema#",
       "title": "message",
       "type": "string"
     }
     ```

2. **Complex type with xs:sequence**
   - Becomes an object at root level with `properties` and `required`
   - Example shown in "Example Transformation" section below

3. **Complex type with xs:choice**
   - The `oneOf` array is placed directly at the root level (not nested in properties)
   - Example: Root element with only choice inside →
     ```json
     {
       "$schema": "http://json-schema.org/draft-07/schema#",
       "title": "contact",
       "oneOf": [
         {"type": "object", "properties": {"email": {"type": "string"}}, "required": ["email"]},
         {"type": "object", "properties": {"phone": {"type": "string"}}, "required": ["phone"]}
       ]
     }
     ```

4. **Root element whose resolved schema is a union (`anyOf`)**
   - If resolving the root element's type results in a schema that contains `"anyOf"` (from `xs:union`, Section 12), the `anyOf` must be placed directly at the root level alongside `$schema` and `title`.
   - Do not wrap union roots into an object with `properties`.
   - Example: `<xs:element name="id" type="IDType"/>` where `IDType` is a union →
     ```json
     {
       "$schema": "http://json-schema.org/draft-07/schema#",
       "title": "id",
       "anyOf": [
         {"type": "integer"},
         {"type": "string"}
       ]
     }
     ```

5. **Root element whose resolved schema contains both `properties` and `oneOf`**
   - This occurs for extension-with-choice types (Section 11, Step 4a).
   - Hoist the resolved schema *as-is* to the root level alongside `$schema` and `title`.
   - Do not replace it with a pure `{ "oneOf": [...] }` schema; keep the top-level `type/properties/required` **and** `oneOf`.

**Processing algorithm:**
- Resolve the root element's type (inline, named reference, or built-in)
- **Hoist** the resolved type definition to the root schema level
- Do NOT wrap simple types in an object structure
- Add `$schema` and `title` fields to the root

## Processing Requirements

Your transformer must correctly:
- Parse XML Schema files
- Resolve all type references (named types, inline types, built-in types)
- Handle recursive and nested type definitions
- Process all XSD constructs described in this specification
- Generate valid JSON Schema Draft 7 output

## Output Format

The output JSON must:
- Be valid JSON (properly formatted, escaped)
- Include `"$schema": "http://json-schema.org/draft-07/schema#"` at the top level
- Use proper JSON Schema Draft 7 keywords
- Maintain semantic equivalence with the source XSD
- Be deterministic (same input XSD always produces identical JSON output)
- Correctly resolve all named type references (don't default unknown types to string)
- **Property ordering at ALL levels**: All properties in `"properties"` objects MUST be sorted in **alphabetical order** by property name. This applies **recursively at ALL nesting levels**:
  - Properties at the root level
  - Properties inside nested objects (e.g., `address` object inside `person`)
  - Properties inside objects within arrays (e.g., array items with object type)
  - Properties inside `oneOf` or `anyOf` options
  - Properties at ANY depth in the schema tree
- **Required array ordering**: All `"required"` arrays MUST be sorted in **alphabetical order**. This applies to top-level required arrays AND required arrays within nested objects or `oneOf` options.
- **Enum value ordering**: All `"enum"` arrays MUST be sorted in **alphabetical order** by string value. This ensures canonical representation of enumeration types.
- **Union member ordering (anyOf)**: When processing `xs:union` with `memberTypes` attribute, the resulting `anyOf` array MUST preserve the exact order of types as listed in `memberTypes`. Do NOT sort anyOf members alphabetically or by type category.

**Example of property ordering:**
```json
{
  "properties": {
    "age": {"type": "integer"},
    "email": {"type": "string"},
    "name": {"type": "string"}
  }
}
```
Note: "age" comes before "email" which comes before "name" (alphabetical order).

**Example of enum ordering:**
```xml
<xs:enumeration value="pending"/>
<xs:enumeration value="active"/>
<xs:enumeration value="completed"/>
```
→
```json
{
  "enum": ["active", "completed", "pending"]
}
```
Note: Sorted alphabetically, not in XSD definition order.

## Error Handling

- Invalid XML or malformed XSD → exit with code 1, print error message to stderr
- Missing required arguments (--input or --output) → exit with code 1, print usage/error to stderr
- Unsupported XSD features → process what's supported, ignore unsupported constructs (don't fail)
- File I/O errors (file not found, permission denied, etc.) → exit with code 1, print error message to stderr
- All error conditions must exit with a non-zero code (never exit 0 on error)

## Example Transformation

**Input XSD**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="person">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="name" type="xs:string"/>
        <xs:element name="age" type="xs:integer"/>
        <xs:element name="email" type="xs:string" minOccurs="0"/>
      </xs:sequence>
      <xs:attribute name="id" type="xs:integer" use="required"/>
    </xs:complexType>
  </xs:element>
</xs:schema>
```

**Output JSON Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "person",
  "type": "object",
  "required": ["name", "age", "id"],
  "properties": {
    "name": {
      "type": "string"
    },
    "age": {
      "type": "integer"
    },
    "email": {
      "type": "string"
    },
    "id": {
      "type": "integer"
    }
  }
}
```

## Constraints

- Use Python 3.13 with standard library only (no external XML or schema libraries beyond `xml.etree.ElementTree` or `xml.dom.minidom`)
- Output must be valid JSON Schema Draft 7
- Handle namespaces correctly: XSD elements may use either `xs:` or `xsd:` prefixes (both map to `http://www.w3.org/2001/XMLSchema`)
- Preserve validation semantics (required fields, type constraints, etc.)
- Array handling: single elements with `maxOccurs > 1` become arrays
- The transformation must be deterministic and reproducible
- Unsupported XSD features (like `xs:any`, `xs:group`, etc.) should be silently ignored - continue processing supported elements without failing

## Notes

- Focus on common XSD patterns used in practice
- Elements and attributes become properties in the JSON schema
- Required elements (minOccurs >= 1) and required attributes (use="required") must be listed in the `required` array
- For simplicity, you may inline all type definitions or use `$defs` for named types
- Ensure the output is valid JSON and valid JSON Schema Draft 7
