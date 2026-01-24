#!/usr/bin/env python3
"""Test functions from projects.py"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from app.html.routes.projects import _pydantic_to_dict, _convert_enum_to_string
from app.enums import ProjectStatus

# Test _convert_enum_to_string
test_dict = {
    "id": "1",
    "name": "Test Project",
    "status": ProjectStatus.ACTIVE,
    "company_id": 1
}

print("Before conversion:", test_dict)
converted = _convert_enum_to_string(test_dict)
print("After conversion:", converted)
print("Status type:", type(converted["status"]))
print("Status value:", converted["status"])

# Check that it's now a string
assert isinstance(converted["status"], str), "Status should be converted to string"
print("\nOK: All tests passed")
