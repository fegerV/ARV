#!/usr/bin/env python3
"""Script to check API routes and tags without starting the server."""

import json
from app.main import app

# Get OpenAPI schema
openapi_schema = app.openapi()

# Print tags
print("=== OpenAPI Tags ===")
tags = openapi_schema.get('tags', [])
for tag in tags:
    print(f"- {tag['name']}: {tag.get('description', 'No description')}")

print("\n=== Routes by Path ===")
paths = openapi_schema.get('paths', {})
for path in sorted(paths.keys()):
    print(f"\n{path}:")
    for method, details in paths[path].items():
        if isinstance(details, dict):
            tags = details.get('tags', [])
            operation_id = details.get('operationId', 'No ID')
            print(f"  {method.upper()}: tags={tags}, operationId={operation_id}")

# Check for duplicate tags
print("\n=== Tag Analysis ===")
all_tags = []
for path, methods in paths.items():
    for method, details in methods.items():
        if isinstance(details, dict):
            all_tags.extend(details.get('tags', []))

from collections import Counter
tag_counts = Counter(all_tags)
print("Tag usage counts:")
for tag, count in tag_counts.items():
    print(f"  {tag}: {count}")

# Check for potential duplicates
print("\n=== Potential Issues ===")
company_routes = [p for p in paths.keys() if 'companies' in p.lower()]
auth_routes = [p for p in paths.keys() if 'auth' in p.lower()]

if company_routes:
    print(f"Companies routes: {company_routes}")
if auth_routes:
    print(f"Auth routes: {auth_routes}")

# Check for exact duplicates
print("\n=== Duplicate Route Check ===")
route_signatures = []
for path, methods in paths.items():
    for method, details in methods.items():
        if isinstance(details, dict):
            signature = f"{method.upper()} {path}"
            route_signatures.append(signature)

duplicates = [sig for sig in set(route_signatures) if route_signatures.count(sig) > 1]
if duplicates:
    print(f"Found duplicate routes: {duplicates}")
else:
    print("No duplicate routes found")