#!/usr/bin/env python3
import requests
import json

resp = requests.post(
    'http://localhost:42005/v1/chat/completions', 
    headers={
        'Content-Type': 'application/json', 
        'Authorization': 'Bearer my-secret-qwen-key'
    },
    json={
        'model': 'qwen3-coder-plus', 
        'messages': [{'role': 'user', 'content': 'Read wiki/github.md'}], 
        'tools': [{
            'type': 'function', 
            'function': {
                'name': 'read_file', 
                'description': 'Read', 
                'parameters': {
                    'type': 'object', 
                    'properties': {'path': {'type': 'string'}}, 
                    'required': ['path']
                }
            }
        }]
    }
)
print(json.dumps(resp.json(), indent=2))
