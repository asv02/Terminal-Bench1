from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest


def _run_transformer(xsd_content: str) -> dict[str, Any] | None:
    """Run the transformer with XSD content and return parsed JSON schema."""
    transformer_path = Path("/app/transformer.py")
    if not transformer_path.exists():
        pytest.fail(f"Expected transformer at {transformer_path} to exist")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        xsd_file = tmppath / "input.xsd"
        json_file = tmppath / "output.json"

        # Write XSD input
        xsd_file.write_text(xsd_content, encoding="utf-8")

        # Run transformer
        result = subprocess.run(
            ["python", str(transformer_path), "--input", str(xsd_file), "--output", str(json_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return None

        if not json_file.exists():
            pytest.fail(f"Transformer succeeded but output file {json_file} was not created")

        # Parse and return JSON
        try:
            return json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}")


def _validate_json_schema_structure(schema: dict[str, Any]) -> None:
    """Validate basic JSON Schema Draft 7 structure."""
    assert "$schema" in schema, "Schema must include $schema field"
    assert schema["$schema"] == "http://json-schema.org/draft-07/schema#", \
        "Schema must reference JSON Schema Draft 7"


def test_simple_string_element():
    """Test transformation of a simple string element with title."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="message" type="xs:string"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)
    assert schema.get("title") == "message"
    assert schema.get("type") == "string"


def test_basic_types():
    """Test transformation of basic XSD types to JSON Schema types."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="data">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="count" type="xs:integer"/>
            <xs:element name="price" type="xs:decimal"/>
            <xs:element name="active" type="xs:boolean"/>
            <xs:element name="timestamp" type="xs:dateTime"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["price"]["type"] == "number"
    assert schema["properties"]["active"]["type"] == "boolean"
    assert schema["properties"]["timestamp"]["type"] == "string"
    assert schema["properties"]["timestamp"]["format"] == "date-time"


def test_complex_type_with_required_and_optional():
    """Test complex type with required and optional elements."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="record">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="id" type="xs:integer"/>
            <xs:element name="notes" type="xs:string" minOccurs="0"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "id" in schema["required"]
    assert "notes" not in schema["required"]


def test_array_with_max_occurs_unbounded():
    """Test that maxOccurs='unbounded' creates an array type."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="list">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="item" type="xs:string" maxOccurs="unbounded"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    item_schema = schema["properties"]["item"]
    assert item_schema["type"] == "array"
    assert item_schema["items"]["type"] == "string"


def test_array_with_min_items_constraint():
    """Test array with minOccurs>0 and maxOccurs>1 creates minItems constraint."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="team">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="member" type="xs:string" minOccurs="2" maxOccurs="10"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    member_schema = schema["properties"]["member"]
    assert member_schema["type"] == "array"
    assert member_schema.get("minItems") == 2


def test_array_with_min_occurs_zero_has_no_min_items():
    """Test that minItems is omitted when minOccurs=0, even for arrays."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="team">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="member" type="xs:string" minOccurs="0" maxOccurs="3"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    member_schema = schema["properties"]["member"]
    assert member_schema["type"] == "array"
    assert "minItems" not in member_schema


def test_attributes():
    """Test attribute handling with required, optional, and default values."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="item">
        <xs:complexType>
          <xs:attribute name="id" type="xs:integer" use="required"/>
          <xs:attribute name="label" type="xs:string" use="optional"/>
          <xs:attribute name="timeout" type="xs:integer" default="30"/>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "id" in schema["required"]
    assert "label" not in schema["required"]
    assert schema["properties"]["timeout"]["default"] == 30


def test_string_restrictions():
    """Test string facet restrictions."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="username">
        <xs:simpleType>
          <xs:restriction base="xs:string">
            <xs:minLength value="3"/>
            <xs:maxLength value="20"/>
            <xs:pattern value="[a-zA-Z0-9]+"/>
          </xs:restriction>
        </xs:simpleType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema.get("minLength") == 3
    assert schema.get("maxLength") == 20
    assert schema.get("pattern") == "[a-zA-Z0-9]+"


def test_integer_restrictions():
    """Test integer facet restrictions including exclusive bounds."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="score">
        <xs:simpleType>
          <xs:restriction base="xs:integer">
            <xs:minExclusive value="0"/>
            <xs:maxExclusive value="100"/>
          </xs:restriction>
        </xs:simpleType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema.get("minimum") == 0
    assert schema.get("exclusiveMinimum") is True
    assert schema.get("maximum") == 100
    assert schema.get("exclusiveMaximum") is True


def test_enumeration():
    """Test enumeration facet creates enum array."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="status">
        <xs:simpleType>
          <xs:restriction base="xs:string">
            <xs:enumeration value="pending"/>
            <xs:enumeration value="active"/>
            <xs:enumeration value="completed"/>
          </xs:restriction>
        </xs:simpleType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert set(schema["enum"]) == {"pending", "active", "completed"}


def test_nested_complex_types():
    """Test deeply nested complex types with mixed elements and attributes."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="company">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="name" type="xs:string"/>
            <xs:element name="employee">
              <xs:complexType>
                <xs:sequence>
                  <xs:element name="firstName" type="xs:string"/>
                  <xs:element name="department" type="xs:string" minOccurs="0"/>
                </xs:sequence>
                <xs:attribute name="id" type="xs:integer" use="required"/>
              </xs:complexType>
            </xs:element>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    employee = schema["properties"]["employee"]
    assert employee["type"] == "object"
    assert "firstName" in employee["required"]
    assert "id" in employee["required"]
    assert "department" not in employee["required"]


def test_named_types():
    """Test named simpleType and complexType definitions."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="ageType">
        <xs:restriction base="xs:integer">
          <xs:minInclusive value="0"/>
          <xs:maxInclusive value="150"/>
        </xs:restriction>
      </xs:simpleType>
      
      <xs:complexType name="addressType">
        <xs:sequence>
          <xs:element name="street" type="xs:string"/>
          <xs:element name="city" type="xs:string"/>
        </xs:sequence>
      </xs:complexType>
      
      <xs:element name="person">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="age" type="ageType"/>
            <xs:element name="address" type="addressType"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    age_schema = schema["properties"]["age"]
    assert age_schema["type"] == "integer"
    assert age_schema.get("minimum") == 0
    assert age_schema.get("maximum") == 150

    address_schema = schema["properties"]["address"]
    assert address_schema["type"] == "object"
    assert "street" in address_schema["properties"]


def test_named_simple_type_deep_copy_prevents_default_leakage():
    """Test that applying defaults does not mutate cached named type schemas."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="statusType">
        <xs:restriction base="xs:string">
          <xs:enumeration value="active"/>
          <xs:enumeration value="inactive"/>
        </xs:restriction>
      </xs:simpleType>

      <xs:element name="config">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="statusWithDefault" type="statusType" default="active"/>
            <xs:element name="statusWithoutDefault" type="statusType"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    with_default = schema["properties"]["statusWithDefault"]
    without_default = schema["properties"]["statusWithoutDefault"]

    assert set(with_default["enum"]) == {"active", "inactive"}
    assert set(without_default["enum"]) == {"active", "inactive"}

    assert with_default.get("default") == "active"
    assert "default" not in without_default


def test_choice_group():
    """Test that xs:choice groups are converted to oneOf."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="contact">
        <xs:complexType>
          <xs:choice>
            <xs:element name="email" type="xs:string"/>
            <xs:element name="phone" type="xs:string"/>
          </xs:choice>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "oneOf" in schema
    assert len(schema["oneOf"]) == 2

    email_option = next((opt for opt in schema["oneOf"] if "email" in opt.get("properties", {})), None)
    phone_option = next((opt for opt in schema["oneOf"] if "phone" in opt.get("properties", {})), None)

    assert email_option is not None
    assert "email" in email_option["required"]
    assert phone_option is not None
    assert "phone" in phone_option["required"]


def test_choice_option_resolves_named_simple_type_restrictions():
    """Test that named simpleType restrictions are applied inside xs:choice options."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="zipType">
        <xs:restriction base="xs:string">
          <xs:pattern value="[0-9]{5}"/>
        </xs:restriction>
      </xs:simpleType>

      <xs:element name="contact">
        <xs:complexType>
          <xs:choice>
            <xs:element name="zipcode" type="zipType"/>
            <xs:element name="email" type="xs:string"/>
          </xs:choice>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)
    assert "oneOf" in schema

    zip_option = next((opt for opt in schema["oneOf"] if "zipcode" in opt.get("properties", {})), None)
    assert zip_option is not None
    zip_schema = zip_option["properties"]["zipcode"]
    assert zip_schema["type"] == "string"
    assert zip_schema.get("pattern") == "[0-9]{5}"


def test_list_type():
    """Test that xs:list types are converted to arrays."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="integerList">
        <xs:list itemType="xs:integer"/>
      </xs:simpleType>
      
      <xs:element name="numbers" type="integerList"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema["type"] == "array"
    assert schema["items"]["type"] == "integer"


def test_nillable_element():
    """Test that nillable elements allow null values."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="person">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="firstName" type="xs:string"/>
            <xs:element name="middleName" type="xs:string" nillable="true"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    middle_name = schema["properties"]["middleName"]
    assert isinstance(middle_name["type"], list)
    assert "string" in middle_name["type"]
    assert "null" in middle_name["type"]


def test_element_default_value():
    """Test that default values on elements are preserved with correct types."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="config">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="status" type="xs:string" default="active"/>
            <xs:element name="timeout" type="xs:integer" default="30"/>
            <xs:element name="enabled" type="xs:boolean" default="true"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema["properties"]["status"]["default"] == "active"
    assert schema["properties"]["timeout"]["default"] == 30
    assert schema["properties"]["enabled"]["default"] is True


def test_property_alphabetical_ordering():
    """Test that properties are sorted alphabetically."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="record">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="zebra" type="xs:string"/>
            <xs:element name="apple" type="xs:string"/>
            <xs:element name="middle" type="xs:string"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    property_keys = list(schema["properties"].keys())
    assert property_keys == ["apple", "middle", "zebra"], \
        f"Properties should be alphabetically ordered, got {property_keys}"


def test_type_extension():
    """Test xs:extension for type inheritance with alphabetical ordering."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
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
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="employee" type="EmployeeType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Should have properties from both base and extension
    assert set(schema["properties"].keys()) == {"name", "age", "employeeId"}
    
    # All should be required
    assert set(schema["required"]) == {"name", "age", "employeeId"}

    # Check alphabetical ordering
    property_keys = list(schema["properties"].keys())
    assert property_keys == sorted(property_keys)


def test_type_extension_with_attributes():
    """Test xs:extension with both elements and attributes."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="BaseType">
        <xs:sequence>
          <xs:element name="value" type="xs:string"/>
        </xs:sequence>
        <xs:attribute name="id" type="xs:integer" use="required"/>
      </xs:complexType>

      <xs:complexType name="ExtendedType">
        <xs:complexContent>
          <xs:extension base="BaseType">
            <xs:sequence>
              <xs:element name="extra" type="xs:string"/>
            </xs:sequence>
            <xs:attribute name="category" type="xs:string" use="required"/>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="item" type="ExtendedType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert set(schema["properties"].keys()) == {"value", "id", "extra", "category"}
    assert set(schema["required"]) == {"value", "id", "extra", "category"}


def test_extension_property_collision():
    """Test that when base and extension define same property, extension takes precedence."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="BaseType">
        <xs:sequence>
          <xs:element name="status" type="xs:string"/>
          <xs:element name="code" type="xs:integer"/>
        </xs:sequence>
      </xs:complexType>

      <xs:complexType name="ExtendedType">
        <xs:complexContent>
          <xs:extension base="BaseType">
            <xs:sequence>
              <xs:element name="status" type="xs:boolean"/>
              <xs:element name="message" type="xs:string"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="response" type="ExtendedType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Extension version of "status" should take precedence (boolean, not string)
    assert schema["properties"]["status"]["type"] == "boolean"
    assert schema["properties"]["code"]["type"] == "integer"
    assert schema["properties"]["message"]["type"] == "string"


def test_union_type():
    """Test xs:union with multiple member types."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="IDType">
        <xs:union memberTypes="xs:integer xs:string"/>
      </xs:simpleType>

      <xs:element name="id" type="IDType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "anyOf" in schema
    assert len(schema["anyOf"]) == 2

    types = [s.get("type") for s in schema["anyOf"]]
    assert "integer" in types
    assert "string" in types


def test_unknown_named_type_error():
    """Test that referencing an unknown named type causes an error."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="person">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="name" type="xs:string"/>
            <xs:element name="age" type="unknownType"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is None, "Should fail when encountering unknown named type"


def test_extension_unknown_base_type():
    """Test that referencing unknown base type in xs:extension exits with error."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="ExtendedType">
        <xs:complexContent>
          <xs:extension base="UnknownBaseType">
            <xs:sequence>
              <xs:element name="extra" type="xs:string"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="item" type="ExtendedType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is None, "Should fail when base type is not found in extension"


def test_extension_circular_dependency():
    """Test that circular dependencies in type extension exit with error."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="TypeA">
        <xs:complexContent>
          <xs:extension base="TypeB">
            <xs:sequence>
              <xs:element name="fieldA" type="xs:string"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:complexType name="TypeB">
        <xs:complexContent>
          <xs:extension base="TypeA">
            <xs:sequence>
              <xs:element name="fieldB" type="xs:string"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="item" type="TypeA"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is None, "Should fail when circular dependency detected in extension"


def test_attribute_unknown_named_type():
    """Test that referencing unknown named type in xs:attribute exits with error."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="item">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="value" type="xs:string"/>
          </xs:sequence>
          <xs:attribute name="customAttr" type="UnknownCustomType" use="required"/>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is None, "Should fail when attribute references unknown named type"


def test_malformed_xml_exits_with_error():
    """Test that malformed XML exits with non-zero code."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="broken">
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is None


def test_cli_missing_arguments():
    """Test that missing CLI arguments cause error exit."""
    transformer_path = Path("/app/transformer.py")
    
    result = subprocess.run(
        ["python", str(transformer_path), "--output", "/tmp/out.json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0

    result = subprocess.run(
        ["python", str(transformer_path), "--input", "/tmp/in.xsd"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_file_not_found_error():
    """Test that missing input file causes error exit."""
    transformer_path = Path("/app/transformer.py")
    
    result = subprocess.run(
        ["python", str(transformer_path), "--input", "/nonexistent/file.xsd", "--output", "/tmp/out.json"],
        capture_output=True,
        text=True,
    )
    
    assert result.returncode != 0


def test_list_with_inline_simple_type():
    """Test xs:list with inline xs:simpleType (Form 2)."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="restrictedList">
        <xs:list>
          <xs:simpleType>
            <xs:restriction base="xs:integer">
              <xs:minInclusive value="1"/>
              <xs:maxInclusive value="100"/>
            </xs:restriction>
          </xs:simpleType>
        </xs:list>
      </xs:simpleType>
      
      <xs:element name="scores" type="restrictedList"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema["type"] == "array"
    assert schema["items"]["type"] == "integer"
    assert schema["items"].get("minimum") == 1
    assert schema["items"].get("maximum") == 100


def test_date_and_time_formats():
    """Test that xs:date and xs:time are mapped with correct formats."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="schedule">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="eventDate" type="xs:date"/>
            <xs:element name="startTime" type="xs:time"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema["properties"]["eventDate"]["type"] == "string"
    assert schema["properties"]["eventDate"]["format"] == "date"
    assert schema["properties"]["startTime"]["type"] == "string"
    assert schema["properties"]["startTime"]["format"] == "time"


def test_xsd_prefix_namespace():
    """Test that xsd: prefix is handled correctly (alternative to xs:)."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="data">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="value" type="xsd:string"/>
            <xsd:element name="count" type="xsd:integer"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema["properties"]["value"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"


def test_choice_only_root_hoisting():
    """Test that root element with only choice creates oneOf at root level."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="contact">
        <xs:complexType>
          <xs:choice>
            <xs:element name="email" type="xs:string"/>
            <xs:element name="phone" type="xs:string"/>
            <xs:element name="address" type="xs:string"/>
          </xs:choice>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # oneOf should be at root level, not nested in properties
    assert "oneOf" in schema
    assert len(schema["oneOf"]) == 3
    assert schema.get("title") == "contact"
    
    # Should not have "properties" at root level for choice-only structure
    assert "properties" not in schema or len(schema.get("properties", {})) == 0


def test_choice_with_min_occurs_optional():
    """Test that choice elements with minOccurs=0 are not marked as required."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="notification">
        <xs:complexType>
          <xs:choice>
            <xs:element name="email" type="xs:string" minOccurs="0"/>
            <xs:element name="sms" type="xs:string" minOccurs="0"/>
          </xs:choice>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "oneOf" in schema
    # Elements with minOccurs=0 should NOT be in required array
    for option in schema["oneOf"]:
        if "email" in option.get("properties", {}):
            assert "email" not in option.get("required", [])
        if "sms" in option.get("properties", {}):
            assert "sms" not in option.get("required", [])


def test_list_fallback_default():
    """Test xs:list fallback when neither itemType nor inline simpleType exists."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="basicList">
        <xs:list/>
      </xs:simpleType>
      
      <xs:element name="items" type="basicList"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert schema["type"] == "array"
    # Should default to string items when no itemType or inline simpleType
    assert schema["items"]["type"] == "string"


def test_attribute_with_named_simple_type():
    """Test attribute using a named simpleType (successful case)."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="statusType">
        <xs:restriction base="xs:string">
          <xs:enumeration value="active"/>
          <xs:enumeration value="inactive"/>
          <xs:enumeration value="pending"/>
        </xs:restriction>
      </xs:simpleType>
      
      <xs:element name="account">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="name" type="xs:string"/>
          </xs:sequence>
          <xs:attribute name="status" type="statusType" use="required"/>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Attribute should resolve the named simpleType
    status_attr = schema["properties"]["status"]
    assert status_attr["type"] == "string"
    assert set(status_attr["enum"]) == {"active", "inactive", "pending"}
    assert "status" in schema["required"]


def test_attribute_with_named_union_type():
    """Test attribute using a named union type resolves to anyOf."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="statusType">
        <xs:restriction base="xs:string">
          <xs:enumeration value="active"/>
          <xs:enumeration value="inactive"/>
        </xs:restriction>
      </xs:simpleType>

      <xs:simpleType name="idOrStatus">
        <xs:union memberTypes="xs:integer statusType"/>
      </xs:simpleType>

      <xs:element name="account">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="name" type="xs:string"/>
          </xs:sequence>
          <xs:attribute name="selector" type="idOrStatus" use="required"/>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    selector = schema["properties"]["selector"]
    assert "anyOf" in selector
    assert any(opt.get("type") == "integer" for opt in selector["anyOf"])
    assert any(opt.get("type") == "string" and set(opt.get("enum", [])) == {"active", "inactive"} for opt in selector["anyOf"])
    assert "selector" in schema["required"]


def test_multi_level_extension():
    """Test multiple levels of type extension (A extends B extends C)."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="BaseType">
        <xs:sequence>
          <xs:element name="id" type="xs:integer"/>
        </xs:sequence>
      </xs:complexType>

      <xs:complexType name="MiddleType">
        <xs:complexContent>
          <xs:extension base="BaseType">
            <xs:sequence>
              <xs:element name="name" type="xs:string"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:complexType name="FinalType">
        <xs:complexContent>
          <xs:extension base="MiddleType">
            <xs:sequence>
              <xs:element name="active" type="xs:boolean"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="item" type="FinalType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Should have properties from all three levels
    assert set(schema["properties"].keys()) == {"id", "name", "active"}
    assert set(schema["required"]) == {"id", "name", "active"}
    
    # Check alphabetical ordering
    property_keys = list(schema["properties"].keys())
    assert property_keys == ["active", "id", "name"]


def test_extension_with_choice():
    """Test extension that adds a choice group."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
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
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Should have id from base, and oneOf for choice
    assert "id" in schema["properties"]
    assert "oneOf" in schema
    
    # Check that oneOf alternatives include id from base type
    for option in schema["oneOf"]:
        assert "id" in option.get("properties", {})
        assert "id" in option.get("required", [])


def test_extension_with_choice_array_min_items():
    """Test extension+choice where a choice alternative is an array with minItems."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="BaseType">
        <xs:sequence>
          <xs:element name="id" type="xs:integer"/>
        </xs:sequence>
        <xs:attribute name="kind" type="xs:string" use="required"/>
      </xs:complexType>

      <xs:complexType name="ExtendedType">
        <xs:complexContent>
          <xs:extension base="BaseType">
            <xs:choice>
              <xs:element name="tags" type="xs:string" minOccurs="2" maxOccurs="unbounded"/>
              <xs:element name="email" type="xs:string"/>
            </xs:choice>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="contact" type="ExtendedType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Common fields present at top-level
    assert schema.get("type") == "object"
    assert "properties" in schema
    assert "id" in schema["properties"]
    assert "kind" in schema["properties"]
    assert set(schema.get("required", [])) >= {"id", "kind"}

    # oneOf present and duplicates common fields into each branch
    assert "oneOf" in schema
    for option in schema["oneOf"]:
        assert "id" in option.get("properties", {})
        assert "kind" in option.get("properties", {})
        assert "id" in option.get("required", [])
        assert "kind" in option.get("required", [])

    tags_option = next((opt for opt in schema["oneOf"] if "tags" in opt.get("properties", {})), None)
    assert tags_option is not None
    tags_schema = tags_option["properties"]["tags"]
    assert tags_schema["type"] == "array"
    assert tags_schema.get("minItems") == 2
    assert tags_schema["items"]["type"] == "string"


def test_extension_with_choice_array_min_items_one_and_required_attribute():
    """Test extension+choice duplication with array(minItems=1) and required attribute in all options."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="BaseType">
        <xs:sequence>
          <xs:element name="id" type="xs:integer"/>
        </xs:sequence>
      </xs:complexType>

      <xs:complexType name="ExtendedType">
        <xs:complexContent>
          <xs:extension base="BaseType">
            <xs:attribute name="source" type="xs:string" use="required"/>
            <xs:choice>
              <xs:element name="ids" type="xs:integer" minOccurs="1" maxOccurs="3"/>
              <xs:element name="email" type="xs:string"/>
            </xs:choice>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="contact" type="ExtendedType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Common fields present at top-level
    assert schema.get("type") == "object"
    assert "properties" in schema
    assert "id" in schema["properties"]
    assert "source" in schema["properties"]
    assert set(schema.get("required", [])) >= {"id", "source"}
    assert "oneOf" in schema

    # Required arrays must be sorted for deterministic output
    assert schema.get("required", []) == sorted(schema.get("required", []))

    # Every option must duplicate base+extension required fields
    for option in schema["oneOf"]:
        assert "id" in option.get("properties", {})
        assert "source" in option.get("properties", {})
        assert "id" in option.get("required", [])
        assert "source" in option.get("required", [])
        assert option.get("required", []) == sorted(option.get("required", []))

    ids_option = next((opt for opt in schema["oneOf"] if "ids" in opt.get("properties", {})), None)
    assert ids_option is not None
    ids_schema = ids_option["properties"]["ids"]
    assert ids_schema["type"] == "array"
    assert ids_schema.get("minItems") == 1
    assert ids_schema["items"]["type"] == "integer"


def test_choice_with_array_elements():
    """Test choice group where elements have maxOccurs>1."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="data">
        <xs:complexType>
          <xs:choice>
            <xs:element name="tags" type="xs:string" maxOccurs="unbounded"/>
            <xs:element name="categories" type="xs:string" maxOccurs="5"/>
          </xs:choice>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "oneOf" in schema
    
    # Find tags option and verify it's an array
    tags_option = next((opt for opt in schema["oneOf"] if "tags" in opt.get("properties", {})), None)
    assert tags_option is not None
    assert tags_option["properties"]["tags"]["type"] == "array"
    
    # Find categories option and verify it's an array
    categories_option = next((opt for opt in schema["oneOf"] if "categories" in opt.get("properties", {})), None)
    assert categories_option is not None
    assert categories_option["properties"]["categories"]["type"] == "array"


def test_choice_array_with_min_items_constraint():
    """Test choice option where an array element also requires minItems from minOccurs."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="payload">
        <xs:complexType>
          <xs:choice>
            <xs:element name="tags" type="xs:string" minOccurs="2" maxOccurs="unbounded"/>
            <xs:element name="ids" type="xs:integer" minOccurs="1" maxOccurs="3"/>
          </xs:choice>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "oneOf" in schema

    tags_option = next((opt for opt in schema["oneOf"] if "tags" in opt.get("properties", {})), None)
    assert tags_option is not None
    assert tags_option["properties"]["tags"]["type"] == "array"
    assert tags_option["properties"]["tags"].get("minItems") == 2
    assert tags_option["properties"]["tags"]["items"]["type"] == "string"

    ids_option = next((opt for opt in schema["oneOf"] if "ids" in opt.get("properties", {})), None)
    assert ids_option is not None
    assert ids_option["properties"]["ids"]["type"] == "array"
    assert ids_option["properties"]["ids"].get("minItems") == 1
    assert ids_option["properties"]["ids"]["items"]["type"] == "integer"


def test_union_with_named_types():
    """Test union type using named types as members."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="positiveInt">
        <xs:restriction base="xs:integer">
          <xs:minInclusive value="1"/>
        </xs:restriction>
      </xs:simpleType>
      
      <xs:simpleType name="statusCode">
        <xs:restriction base="xs:string">
          <xs:enumeration value="OK"/>
          <xs:enumeration value="ERROR"/>
        </xs:restriction>
      </xs:simpleType>
      
      <xs:simpleType name="resultType">
        <xs:union memberTypes="positiveInt statusCode"/>
      </xs:simpleType>
      
      <xs:element name="result" type="resultType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "anyOf" in schema
    assert len(schema["anyOf"]) == 2
    
    # One should be integer with minimum
    int_option = next((opt for opt in schema["anyOf"] if opt.get("type") == "integer"), None)
    assert int_option is not None
    assert int_option.get("minimum") == 1
    
    # One should be string with enum
    str_option = next((opt for opt in schema["anyOf"] if opt.get("type") == "string"), None)
    assert str_option is not None
    assert set(str_option.get("enum", [])) == {"OK", "ERROR"}


def test_nested_complex_type_with_extension():
    """Test extension where nested properties are also complex types."""
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="AddressType">
        <xs:sequence>
          <xs:element name="street" type="xs:string"/>
          <xs:element name="city" type="xs:string"/>
        </xs:sequence>
      </xs:complexType>
      
      <xs:complexType name="PersonType">
        <xs:sequence>
          <xs:element name="name" type="xs:string"/>
          <xs:element name="address" type="AddressType"/>
        </xs:sequence>
      </xs:complexType>

      <xs:complexType name="EmployeeType">
        <xs:complexContent>
          <xs:extension base="PersonType">
            <xs:sequence>
              <xs:element name="employeeId" type="xs:integer"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="employee" type="EmployeeType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Should have all properties
    assert set(schema["properties"].keys()) == {"name", "address", "employeeId"}
    
    # Address should be a nested object
    assert schema["properties"]["address"]["type"] == "object"
    assert "street" in schema["properties"]["address"]["properties"]
    assert "city" in schema["properties"]["address"]["properties"]


def test_enum_alphabetical_ordering_trap():
    """TRAP: Test that enum values are sorted alphabetically, not in XSD definition order.
    
    This is extremely easy to miss and explicitly tested. Naive implementations will
    preserve XSD definition order, but the output must be canonicalized alphabetically.
    """
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="priority">
        <xs:simpleType>
          <xs:restriction base="xs:string">
            <xs:enumeration value="urgent"/>
            <xs:enumeration value="low"/>
            <xs:enumeration value="high"/>
            <xs:enumeration value="medium"/>
          </xs:restriction>
        </xs:simpleType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Must be alphabetically sorted, not ["urgent", "low", "high", "medium"]
    assert schema["enum"] == ["high", "low", "medium", "urgent"], \
        f"Enum values must be alphabetically sorted, got {schema['enum']}"


def test_one_of_option_alphabetical_property_ordering():
    """TRAP: Test that properties within oneOf options are alphabetically ordered.
    
    When a choice creates oneOf options, each option's properties must be sorted.
    Naive implementations might preserve element definition order within options.
    """
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="BaseType">
        <xs:sequence>
          <xs:element name="zebra" type="xs:string"/>
          <xs:element name="alpha" type="xs:string"/>
        </xs:sequence>
      </xs:complexType>

      <xs:complexType name="ExtendedType">
        <xs:complexContent>
          <xs:extension base="BaseType">
            <xs:choice>
              <xs:element name="middle" type="xs:string"/>
              <xs:element name="beta" type="xs:string"/>
            </xs:choice>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="item" type="ExtendedType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Each oneOf option must have alphabetically sorted properties
    assert "oneOf" in schema
    for option in schema["oneOf"]:
        property_keys = list(option.get("properties", {}).keys())
        assert property_keys == sorted(property_keys), \
            f"Properties in oneOf option must be alphabetically sorted, got {property_keys}"


def test_pattern_exact_preservation():
    """TRAP: Test that regex patterns are preserved exactly as-is, not normalized.
    
    Pattern values must be preserved character-for-character from the XSD.
    Naive implementations might normalize [0-9] to \\d or add/remove anchors.
    """
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="data">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="zipcode">
              <xs:simpleType>
                <xs:restriction base="xs:string">
                  <xs:pattern value="[0-9]{5}"/>
                </xs:restriction>
              </xs:simpleType>
            </xs:element>
            <xs:element name="phoneDigits">
              <xs:simpleType>
                <xs:restriction base="xs:string">
                  <xs:pattern value="[0-9]{3}-[0-9]{4}"/>
                </xs:restriction>
              </xs:simpleType>
            </xs:element>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Pattern must be exact - not \\d{5} or ^[0-9]{5}$ or other variants
    assert schema["properties"]["zipcode"]["pattern"] == "[0-9]{5}", \
        f"Pattern must be preserved exactly, got {schema['properties']['zipcode'].get('pattern')}"
    assert schema["properties"]["phoneDigits"]["pattern"] == "[0-9]{3}-[0-9]{4}", \
        f"Pattern must be preserved exactly, got {schema['properties']['phoneDigits'].get('pattern')}"


def test_required_array_deduplication_in_extension():
    """TRAP: Test that required arrays don't contain duplicate field names.
    
    When extending a type that already has required fields, and the extension adds
    the same field name, the required array must not have duplicates.
    """
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="BaseType">
        <xs:sequence>
          <xs:element name="id" type="xs:integer"/>
          <xs:element name="status" type="xs:string"/>
        </xs:sequence>
      </xs:complexType>

      <xs:complexType name="ExtendedType">
        <xs:complexContent>
          <xs:extension base="BaseType">
            <xs:sequence>
              <xs:element name="status" type="xs:boolean"/>
              <xs:element name="message" type="xs:string"/>
            </xs:sequence>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="response" type="ExtendedType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Each field should appear exactly once in required, even if redefined
    required_fields = schema.get("required", [])
    assert len(required_fields) == len(set(required_fields)), \
        f"Required array must not contain duplicates, got {required_fields}"
    
    # Should have all unique field names, alphabetically sorted
    assert required_fields == ["id", "message", "status"], \
        f"Required array should be unique and sorted, got {required_fields}"


def test_deeply_nested_property_ordering_trap():
    """TRAP: Test that properties are alphabetically ordered at ALL nesting levels.
    
    Agents might correctly sort top-level properties and even properties inside oneOf options,
    but fail to sort properties inside nested objects, or inside arrays of objects, or inside
    nested objects within oneOf options. This tests the FULL depth of property ordering.
    """
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:complexType name="AddressType">
        <xs:sequence>
          <xs:element name="zip" type="xs:string"/>
          <xs:element name="city" type="xs:string"/>
          <xs:element name="street" type="xs:string"/>
        </xs:sequence>
      </xs:complexType>

      <xs:complexType name="BaseType">
        <xs:sequence>
          <xs:element name="zebra" type="xs:string"/>
          <xs:element name="addresses" maxOccurs="unbounded">
            <xs:complexType>
              <xs:sequence>
                <xs:element name="country" type="xs:string"/>
                <xs:element name="location" type="AddressType"/>
              </xs:sequence>
            </xs:complexType>
          </xs:element>
        </xs:sequence>
      </xs:complexType>

      <xs:complexType name="ExtendedType">
        <xs:complexContent>
          <xs:extension base="BaseType">
            <xs:choice>
              <xs:element name="metadata">
                <xs:complexType>
                  <xs:sequence>
                    <xs:element name="tags" type="xs:string" maxOccurs="unbounded"/>
                    <xs:element name="created" type="xs:dateTime"/>
                  </xs:sequence>
                </xs:complexType>
              </xs:element>
              <xs:element name="status" type="xs:string"/>
            </xs:choice>
          </xs:extension>
        </xs:complexContent>
      </xs:complexType>

      <xs:element name="record" type="ExtendedType"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Top-level properties should be sorted
    top_props = list(schema["properties"].keys())
    assert top_props == sorted(top_props), \
        f"Top-level properties must be alphabetically sorted, got {top_props}"

    # Properties inside the array items (addresses)
    addresses_items = schema["properties"]["addresses"]["items"]
    addresses_props = list(addresses_items["properties"].keys())
    assert addresses_props == ["country", "location"], \
        f"Properties inside array items must be alphabetically sorted, got {addresses_props}"

    # Properties inside nested object (AddressType) inside array
    location_props = list(addresses_items["properties"]["location"]["properties"].keys())
    assert location_props == ["city", "street", "zip"], \
        f"Properties inside nested object must be alphabetically sorted, got {location_props}"

    # Properties inside oneOf options
    assert "oneOf" in schema
    for option in schema["oneOf"]:
        option_props = list(option.get("properties", {}).keys())
        assert option_props == sorted(option_props), \
            f"Properties in oneOf option must be alphabetically sorted, got {option_props}"
        
        # If this is the metadata option, check nested properties too
        if "metadata" in option.get("properties", {}):
            metadata_props = list(option["properties"]["metadata"]["properties"].keys())
            assert metadata_props == ["created", "tags"], \
                f"Properties inside nested object in oneOf must be alphabetically sorted, got {metadata_props}"


def test_max_occurs_one_not_array_trap():
    """TRAP: Test that maxOccurs=1 does NOT create an array.
    
    Naive implementations might assume any maxOccurs>0 creates an array, but the rule is:
    - maxOccurs > 1: creates array
    - maxOccurs = "unbounded": creates array
    - maxOccurs = 1 (or unspecified): does NOT create array, just a regular property
    
    Even when explicitly set to maxOccurs="1", it should be a regular property type.
    """
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="config">
        <xs:complexType>
          <xs:sequence>
            <xs:element name="singleItem" type="xs:string" minOccurs="0" maxOccurs="1"/>
            <xs:element name="requiredSingle" type="xs:string" minOccurs="1" maxOccurs="1"/>
            <xs:element name="actualArray" type="xs:string" minOccurs="0" maxOccurs="2"/>
          </xs:sequence>
        </xs:complexType>
      </xs:element>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # maxOccurs=1 should NOT create array, just regular string property
    single_item = schema["properties"]["singleItem"]
    assert single_item["type"] == "string", \
        f"maxOccurs=1 should be regular string, not array. Got type={single_item.get('type')}"
    assert "items" not in single_item, \
        "maxOccurs=1 should not have 'items' field (that's only for arrays)"

    required_single = schema["properties"]["requiredSingle"]
    assert required_single["type"] == "string", \
        f"maxOccurs=1 should be regular string even when required. Got type={required_single.get('type')}"
    assert "items" not in required_single

    # maxOccurs=2 SHOULD create array
    actual_array = schema["properties"]["actualArray"]
    assert actual_array["type"] == "array", \
        f"maxOccurs=2 should create array. Got type={actual_array.get('type')}"
    assert "items" in actual_array and actual_array["items"]["type"] == "string"

    # Check required fields
    assert "requiredSingle" in schema["required"]
    assert "singleItem" not in schema["required"]
    assert "actualArray" not in schema["required"]


def test_chained_restriction_inheritance_trap():
    """TRAP: Test that restriction chains correctly merge all constraints.
    
    When a simpleType restricts another simpleType that restricts a base type,
    ALL constraints from the chain must be applied. Naive implementations might
    only apply the immediate restriction and lose constraints from parent types.
    """
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
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

      <xs:element name="value" type="strictString"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    # Should have minLength from basicString (5)
    assert schema.get("minLength") == 5, \
        f"Should inherit minLength=5 from ancestor restriction, got {schema.get('minLength')}"

    # Should have maxLength from strictString (20), overriding basicString's 50
    assert schema.get("maxLength") == 20, \
        f"Should use maxLength=20 from immediate restriction, got {schema.get('maxLength')}"

    # Should have pattern from patternedString
    assert schema.get("pattern") == "[A-Z][a-z0-9]+", \
        f"Should inherit pattern from middle restriction, got {schema.get('pattern')}"


def test_union_member_order_preservation_trap():
    """TRAP: Test that anyOf members appear in the same order as memberTypes attribute.
    
    When xs:union specifies memberTypes="typeA typeB typeC", the resulting anyOf array
    must preserve that exact order, not alphabetically sort by type name or by type category.
    Agents might incorrectly sort anyOf by type (integers first, then strings, etc.).
    """
    xsd = """<?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:simpleType name="statusCode">
        <xs:restriction base="xs:string">
          <xs:enumeration value="OK"/>
          <xs:enumeration value="ERROR"/>
        </xs:restriction>
      </xs:simpleType>

      <xs:simpleType name="numericCode">
        <xs:restriction base="xs:integer">
          <xs:minInclusive value="100"/>
          <xs:maxInclusive value="999"/>
        </xs:restriction>
      </xs:simpleType>

      <xs:simpleType name="booleanFlag">
        <xs:restriction base="xs:boolean"/>
      </xs:simpleType>

      <xs:simpleType name="mixedUnion">
        <xs:union memberTypes="statusCode booleanFlag numericCode"/>
      </xs:simpleType>

      <xs:element name="response" type="mixedUnion"/>
    </xs:schema>"""

    schema = _run_transformer(xsd)
    assert schema is not None
    _validate_json_schema_structure(schema)

    assert "anyOf" in schema
    assert len(schema["anyOf"]) == 3, \
        f"Union should have 3 members, got {len(schema.get('anyOf', []))}"

    # Order must match memberTypes="statusCode booleanFlag numericCode"
    # First should be statusCode (string with enum)
    first = schema["anyOf"][0]
    assert first.get("type") == "string", \
        f"First anyOf member should be string (statusCode), got {first.get('type')}"
    assert set(first.get("enum", [])) == {"OK", "ERROR"}, \
        "First member should have statusCode enum values"

    # Second should be booleanFlag
    second = schema["anyOf"][1]
    assert second.get("type") == "boolean", \
        f"Second anyOf member should be boolean (booleanFlag), got {second.get('type')}"

    # Third should be numericCode (integer with range)
    third = schema["anyOf"][2]
    assert third.get("type") == "integer", \
        f"Third anyOf member should be integer (numericCode), got {third.get('type')}"
    assert third.get("minimum") == 100 and third.get("maximum") == 999, \
        "Third member should have numericCode range constraints"
