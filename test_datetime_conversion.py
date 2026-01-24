#!/usr/bin/env python3
"""Test datetime conversion."""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from datetime import datetime
from app.html.routes.projects import _convert_enum_to_string
from app.enums import ProjectStatus

# Test data with datetime
test_dict = {
    "id": "1",
    "name": "Test Project",
    "status": ProjectStatus.ACTIVE,
    "company_id": 1,
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
}

print("Before conversion:")
for key, value in test_dict.items():
    print(f"  {key}: {type(value).__name__} = {value}")

converted = _convert_enum_to_string(test_dict)

print("\nAfter conversion:")
for key, value in converted.items():
    print(f"  {key}: {type(value).__name__} = {value}")

# Test JSON serialization
import json
try:
    json_str = json.dumps(converted)
    print("\nJSON serialization: OK")
    print(f"JSON: {json_str}")
except Exception as e:
    print(f"\nJSON serialization ERROR: {e}")
