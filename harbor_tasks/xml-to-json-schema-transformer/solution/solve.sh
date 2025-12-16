#!/bin/bash
set -e

# Create the transformer implementation
cat > /app/transformer.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""XML Schema to JSON Schema transformer."""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from typing import Any


# XML Schema namespace
XS_NS = "{http://www.w3.org/2001/XMLSchema}"


def strip_ns(tag: str) -> str:
    """Remove namespace prefix from tag."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def find_element(root, tag_name: str):
    """Find element with given tag name, handling both xs: and xsd: prefixes."""
    # Try with namespace
    elem = root.find(f"{XS_NS}{tag_name}")
    if elem is not None:
        return elem
    # Fallback for elements without proper namespace
    return None


def findall_elements(root, tag_name: str):
    """Find all elements with given tag name, handling both xs: and xsd: prefixes."""
    return root.findall(f"{XS_NS}{tag_name}")


def get_json_type(xs_type: str) -> dict[str, Any]:
    """Map XSD type to JSON Schema type."""
    xs_type = xs_type.replace("xs:", "").replace("xsd:", "")
    
    type_mapping = {
        "string": {"type": "string"},
        "integer": {"type": "integer"},
        "int": {"type": "integer"},
        "long": {"type": "integer"},
        "short": {"type": "integer"},
        "decimal": {"type": "number"},
        "float": {"type": "number"},
        "double": {"type": "number"},
        "boolean": {"type": "boolean"},
        "date": {"type": "string", "format": "date"},
        "dateTime": {"type": "string", "format": "date-time"},
        "time": {"type": "string", "format": "time"},
    }
    
    return type_mapping.get(xs_type, {"type": "string"})


def sort_schema_properties(schema: dict[str, Any]) -> None:
    """Recursively sort all properties in a schema (nested objects, arrays, oneOf, anyOf)."""
    if not isinstance(schema, dict):
        return
    
    # Sort properties at this level
    if "properties" in schema and isinstance(schema["properties"], dict):
        schema["properties"] = dict(sorted(schema["properties"].items()))
        # Recursively sort nested object properties
        for prop_schema in schema["properties"].values():
            sort_schema_properties(prop_schema)
    
    # Handle array items
    if "items" in schema:
        sort_schema_properties(schema["items"])
    
    # Handle oneOf alternatives
    if "oneOf" in schema and isinstance(schema["oneOf"], list):
        for option in schema["oneOf"]:
            sort_schema_properties(option)
    
    # Handle anyOf alternatives
    if "anyOf" in schema and isinstance(schema["anyOf"], list):
        for option in schema["anyOf"]:
            sort_schema_properties(option)
    
    # Sort required array if present
    if "required" in schema and isinstance(schema["required"], list):
        schema["required"] = sorted(schema["required"])


def process_restriction(restriction: ET.Element, named_simple_types: dict = None) -> dict[str, Any]:
    """Process xs:restriction element and extract facets."""
    if named_simple_types is None:
        named_simple_types = {}
    
    base_type = restriction.get("base", "xs:string")
    
    # Check if base is a named simpleType (for restriction chains)
    base_name = base_type.replace("xs:", "").replace("xsd:", "")
    if base_name in named_simple_types:
        # Start with base schema (inheriting constraints from parent restriction)
        schema = named_simple_types[base_name].copy()
    else:
        # Start with built-in type
        schema = get_json_type(base_type)
    
    enum_values = []
    
    for child in restriction:
        tag = strip_ns(child.tag)
        
        if tag == "minLength":
            schema["minLength"] = int(child.get("value"))
        elif tag == "maxLength":
            # Later restrictions can override (be more restrictive)
            schema["maxLength"] = int(child.get("value"))
        elif tag == "pattern":
            schema["pattern"] = child.get("value")
        elif tag == "minInclusive":
            schema["minimum"] = int(child.get("value"))
        elif tag == "maxInclusive":
            schema["maximum"] = int(child.get("value"))
        elif tag == "minExclusive":
            val = int(child.get("value"))
            schema["minimum"] = val
            schema["exclusiveMinimum"] = True
        elif tag == "maxExclusive":
            val = int(child.get("value"))
            schema["maximum"] = val
            schema["exclusiveMaximum"] = True
        elif tag == "enumeration":
            enum_values.append(child.get("value"))
    
    if enum_values:
        schema["enum"] = sorted(enum_values)  # Sort alphabetically for canonical output
    
    return schema


def process_simple_type(simple_type: ET.Element, named_simple_types: dict = None) -> dict[str, Any]:
    """Process xs:simpleType element."""
    if named_simple_types is None:
        named_simple_types = {}
    
    for child in simple_type:
        tag = strip_ns(child.tag)
        if tag == "restriction":
            return process_restriction(child, named_simple_types)
        elif tag == "list":
            return process_list(child, named_simple_types)
        elif tag == "union":
            return process_union(child, named_simple_types)
    
    return {"type": "string"}


def process_union(union_elem: ET.Element, named_simple_types: dict = None) -> dict[str, Any]:
    """Process xs:union element to create anyOf schema."""
    if named_simple_types is None:
        named_simple_types = {}
    
    member_types_attr = union_elem.get("memberTypes")
    
    if not member_types_attr:
        return {"type": "string"}
    
    # Split space-separated list of member types
    member_types = member_types_attr.split()
    any_of_schemas = []
    
    for member_type in member_types:
        type_name = member_type.replace("xs:", "").replace("xsd:", "")
        
        # Check if it's a named type
        if type_name in named_simple_types:
            any_of_schemas.append(named_simple_types[type_name].copy())
        else:
            # Try built-in type
            any_of_schemas.append(get_json_type(member_type))
    
    return {"anyOf": any_of_schemas}


def process_list(list_elem: ET.Element, named_simple_types: dict = None) -> dict[str, Any]:
    """Process xs:list element."""
    if named_simple_types is None:
        named_simple_types = {}
    
    item_type_attr = list_elem.get("itemType")
    
    if item_type_attr:
        # itemType specified as attribute
        type_name = item_type_attr.replace("xs:", "").replace("xsd:", "")
        if type_name in named_simple_types:
            item_schema = named_simple_types[type_name].copy()
        else:
            item_schema = get_json_type(item_type_attr)
    else:
        # itemType specified as inline simpleType
        inline_type = list_elem.find(f"{XS_NS}simpleType")
        if inline_type is not None:
            item_schema = process_simple_type(inline_type, named_simple_types)
        else:
            item_schema = {"type": "string"}
    
    return {
        "type": "array",
        "items": item_schema
    }


def process_element(element: ET.Element, named_simple_types: dict = None, named_complex_types: dict = None) -> tuple[str, dict[str, Any], bool]:
    """Process xs:element and return (name, schema, is_required)."""
    if named_simple_types is None:
        named_simple_types = {}
    if named_complex_types is None:
        named_complex_types = {}
    
    name = element.get("name")
    el_type = element.get("type")
    min_occurs = int(element.get("minOccurs", "1"))
    max_occurs = element.get("maxOccurs", "1")
    nillable = element.get("nillable", "false").lower() == "true"
    default = element.get("default")
    
    is_required = min_occurs >= 1
    
    # Check for inline type definition
    complex_type = element.find(f"{XS_NS}complexType")
    simple_type = element.find(f"{XS_NS}simpleType")
    
    if complex_type is not None:
        schema = process_complex_type(complex_type, named_simple_types, named_complex_types)
    elif simple_type is not None:
        schema = process_simple_type(simple_type, named_simple_types)
    elif el_type:
        # Check if it's a named type
        type_name = el_type.replace("xs:", "").replace("xsd:", "")
        if type_name in named_simple_types:
            schema = named_simple_types[type_name].copy()
        elif type_name in named_complex_types:
            schema = named_complex_types[type_name].copy()
        else:
            # Try to get built-in type
            json_type = get_json_type(el_type)
            # Check if it was actually a built-in type or defaulted to string
            base_type = type_name
            known_types = ["string", "integer", "int", "long", "short", "decimal", 
                          "float", "double", "boolean", "date", "dateTime", "time"]
            if base_type not in known_types:
                print(f"Error: Unknown type '{el_type}' referenced", file=sys.stderr)
                sys.exit(1)
            schema = json_type
    else:
        schema = {"type": "string"}
    
    # Handle nillable (add null to type)
    if nillable:
        current_type = schema.get("type")
        if isinstance(current_type, str):
            schema["type"] = [current_type, "null"]
        elif isinstance(current_type, list):
            if "null" not in current_type:
                schema["type"] = current_type + ["null"]
    
    # Handle default values
    if default is not None:
        current_type = schema.get("type")
        base_type = current_type[0] if isinstance(current_type, list) else current_type
        
        if base_type == "integer":
            schema["default"] = int(default)
        elif base_type == "number":
            schema["default"] = float(default)
        elif base_type == "boolean":
            schema["default"] = default.lower() == "true"
        else:
            schema["default"] = default
    
    # Handle arrays (maxOccurs > 1 or unbounded)
    if max_occurs == "unbounded" or (max_occurs.isdigit() and int(max_occurs) > 1):
        schema = {
            "type": "array",
            "items": schema
        }
        if min_occurs > 0:
            schema["minItems"] = min_occurs
    
    return name, schema, is_required


def process_attribute(attribute: ET.Element, named_simple_types: dict = None) -> tuple[str, dict[str, Any], bool]:
    """Process xs:attribute and return (name, schema, is_required)."""
    if named_simple_types is None:
        named_simple_types = {}
    
    name = attribute.get("name")
    attr_type = attribute.get("type", "xs:string")
    use = attribute.get("use", "optional")
    default = attribute.get("default")
    
    # Check if it's a named type
    type_name = attr_type.replace("xs:", "").replace("xsd:", "")
    if type_name in named_simple_types:
        schema = named_simple_types[type_name].copy()
    else:
        # Try to get built-in type
        schema = get_json_type(attr_type)
        # Check if it was actually a built-in type
        known_types = ["string", "integer", "int", "long", "short", "decimal", 
                      "float", "double", "boolean", "date", "dateTime", "time"]
        if type_name not in known_types:
            print(f"Error: Unknown type '{attr_type}' referenced in attribute", file=sys.stderr)
            sys.exit(1)
    
    if default is not None:
        # Try to convert default to appropriate type
        if schema.get("type") == "integer":
            schema["default"] = int(default)
        elif schema.get("type") == "number":
            schema["default"] = float(default)
        elif schema.get("type") == "boolean":
            schema["default"] = default.lower() == "true"
        else:
            schema["default"] = default
    
    is_required = use == "required"
    
    return name, schema, is_required


def process_complex_type(complex_type: ET.Element, named_simple_types: dict = None, named_complex_types: dict = None) -> dict[str, Any]:
    """Process xs:complexType element."""
    if named_simple_types is None:
        named_simple_types = {}
    if named_complex_types is None:
        named_complex_types = {}
    
    # Check for xs:complexContent with xs:extension
    complex_content = complex_type.find(f"{XS_NS}complexContent")
    if complex_content is not None:
        extension = complex_content.find(f"{XS_NS}extension")
        if extension is not None:
            return process_extension(extension, named_simple_types, named_complex_types)
    
    # Check for xs:choice first
    choice = complex_type.find(f"{XS_NS}choice")
    if choice is not None:
        return process_choice(choice, named_simple_types, named_complex_types)
    
    schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # Process sequence
    sequence = complex_type.find(f"{XS_NS}sequence")
    if sequence is not None:
        for child in sequence:
            tag = strip_ns(child.tag)
            if tag == "element":
                name, prop_schema, is_required = process_element(child, named_simple_types, named_complex_types)
                if name:
                    schema["properties"][name] = prop_schema
                    if is_required:
                        schema["required"].append(name)
            # Ignore unsupported elements like xs:any
    
    # Process attributes
    for attr in complex_type.findall(f"{XS_NS}attribute"):
        name, attr_schema, is_required = process_attribute(attr, named_simple_types)
        if name:
            schema["properties"][name] = attr_schema
            if is_required:
                schema["required"].append(name)
    
    # Sort properties alphabetically
    schema["properties"] = dict(sorted(schema["properties"].items()))
    
    # Sort required array alphabetically
    if schema["required"]:
        schema["required"] = sorted(schema["required"])
    
    # Remove empty required array
    if not schema["required"]:
        del schema["required"]
    
    return schema


def process_extension(extension: ET.Element, named_simple_types: dict = None, named_complex_types: dict = None) -> dict[str, Any]:
    """Process xs:extension element to handle type inheritance."""
    if named_simple_types is None:
        named_simple_types = {}
    if named_complex_types is None:
        named_complex_types = {}
    
    base_type_name = extension.get("base", "")
    base_type_name = base_type_name.replace("xs:", "").replace("xsd:", "")
    
    # Resolve base type from named complex types
    if base_type_name not in named_complex_types:
        print(f"Error: Base type '{base_type_name}' not found for extension", file=sys.stderr)
        sys.exit(1)
    
    # Get base type schema (make a deep copy)
    base_schema = json.loads(json.dumps(named_complex_types[base_type_name]))
    
    # Initialize extension schema
    extension_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # Process extension's own sequence
    sequence = extension.find(f"{XS_NS}sequence")
    if sequence is not None:
        for child in sequence:
            tag = strip_ns(child.tag)
            if tag == "element":
                name, prop_schema, is_required = process_element(child, named_simple_types, named_complex_types)
                if name:
                    extension_schema["properties"][name] = prop_schema
                    if is_required:
                        extension_schema["required"].append(name)

    # Process extension's own choice (if present)
    choice = extension.find(f"{XS_NS}choice")
    choice_schema = None
    if choice is not None:
        choice_schema = process_choice(choice, named_simple_types, named_complex_types)
    
    # Process extension's attributes
    for attr in extension.findall(f"{XS_NS}attribute"):
        name, attr_schema, is_required = process_attribute(attr, named_simple_types)
        if name:
            extension_schema["properties"][name] = attr_schema
            if is_required:
                extension_schema["required"].append(name)
    
    # Merge base and extension schemas
    merged_schema = {
        "type": "object",
        "properties": {},
        "required": []
    }
    
    # Add base properties first
    if "properties" in base_schema:
        merged_schema["properties"].update(base_schema["properties"])
    
    # Add extension properties (overwrites if same name)
    merged_schema["properties"].update(extension_schema["properties"])
    
    # Merge required arrays
    if "required" in base_schema:
        merged_schema["required"].extend(base_schema["required"])
    merged_schema["required"].extend(extension_schema["required"])

    # Deduplicate and sort required array alphabetically
    if merged_schema["required"]:
        merged_schema["required"] = sorted(dict.fromkeys(merged_schema["required"]))
    
    # Sort properties alphabetically
    merged_schema["properties"] = dict(sorted(merged_schema["properties"].items()))

    # If this extension introduces a choice group, attach it and ensure base/extension
    # properties are present in each oneOf alternative.
    if choice_schema is not None and "oneOf" in choice_schema:
        merged_schema["oneOf"] = []
        for opt in choice_schema["oneOf"]:
            # Make a deep copy (avoid mutating shared dicts)
            opt_copy = json.loads(json.dumps(opt))

            # Merge properties: base+extension first, then option-specific
            opt_props: dict[str, Any] = {}
            if "properties" in merged_schema:
                opt_props.update(merged_schema["properties"])
            opt_props.update(opt_copy.get("properties", {}))
            opt_copy["properties"] = dict(sorted(opt_props.items()))

            # Merge required: base+extension required plus option required
            merged_required = list(merged_schema.get("required", []))
            merged_required.extend(opt_copy.get("required", []))
            if merged_required:
                opt_copy["required"] = sorted(dict.fromkeys(merged_required))
            else:
                opt_copy.pop("required", None)

            # Ensure object type
            opt_copy.setdefault("type", "object")
            merged_schema["oneOf"].append(opt_copy)
    
    # Remove empty required array
    if not merged_schema["required"]:
        del merged_schema["required"]
    
    return merged_schema


def process_choice(choice: ET.Element, named_simple_types: dict = None, named_complex_types: dict = None) -> dict[str, Any]:
    """Process xs:choice element to create oneOf schema."""
    if named_simple_types is None:
        named_simple_types = {}
    if named_complex_types is None:
        named_complex_types = {}
    
    one_of_options = []
    
    for child in choice:
        tag = strip_ns(child.tag)
        if tag == "element":
            name, prop_schema, is_required = process_element(child, named_simple_types, named_complex_types)
            if name:
                option = {
                    "type": "object",
                    "properties": {name: prop_schema}
                }
                if is_required:
                    option["required"] = [name]
                one_of_options.append(option)
    
    return {"oneOf": one_of_options}


def transform_xsd_to_json_schema(xsd_content: str) -> dict[str, Any]:
    """Transform XSD string to JSON Schema dict."""
    try:
        root = ET.fromstring(xsd_content)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Build a registry of named types
    named_simple_types = {}
    named_complex_types = {}
    
    for simple_type in root.findall(f"{XS_NS}simpleType"):
        name = simple_type.get("name")
        if name:
            named_simple_types[name] = process_simple_type(simple_type, named_simple_types)
    
    for complex_type in root.findall(f"{XS_NS}complexType"):
        name = complex_type.get("name")
        if name:
            named_complex_types[name] = process_complex_type(complex_type, named_simple_types, named_complex_types)
    
    # Find root element
    root_element = root.find(f"{XS_NS}element")
    if root_element is None:
        print("Error: No root element found in XSD", file=sys.stderr)
        sys.exit(1)
    
    name = root_element.get("name")
    el_type = root_element.get("type")
    
    # Base schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#"
    }
    
    if name:
        schema["title"] = name
    
    # Check for inline complex type
    complex_type = root_element.find(f"{XS_NS}complexType")
    simple_type = root_element.find(f"{XS_NS}simpleType")
    
    if complex_type is not None:
        type_schema = process_complex_type(complex_type, named_simple_types, named_complex_types)
        schema.update(type_schema)
    elif simple_type is not None:
        type_schema = process_simple_type(simple_type, named_simple_types)
        schema.update(type_schema)
    elif el_type:
        # Check if it's a named type
        type_name = el_type.replace("xs:", "").replace("xsd:", "")
        if type_name in named_simple_types:
            type_schema = named_simple_types[type_name]
        elif type_name in named_complex_types:
            type_schema = named_complex_types[type_name]
        else:
            type_schema = get_json_type(el_type)
        schema.update(type_schema)
    else:
        schema["type"] = "string"
    
    # Ensure properties are alphabetically sorted if present
    if "properties" in schema:
        schema["properties"] = dict(sorted(schema["properties"].items()))
    
    # Ensure required array is alphabetically sorted if present
    if "required" in schema and isinstance(schema["required"], list):
        schema["required"] = sorted(schema["required"])
    
    # Recursively sort all nested properties
    sort_schema_properties(schema)
    
    return schema


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Convert XSD to JSON Schema")
    parser.add_argument("--input", required=True, help="Input XSD file")
    parser.add_argument("--output", required=True, help="Output JSON Schema file")
    
    args = parser.parse_args()
    
    # Read XSD
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            xsd_content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file {args.input} not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Transform
    schema = transform_xsd_to_json_schema(xsd_content)
    
    # Write output
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

chmod +x /app/transformer.py

echo "Transformer created successfully"
