import re

with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the main script tag
script_start = content.find('<script>\n        const API_URL')
script_end = content.find('    </script>', script_start)
script = content[script_start:script_end]

# Check for balanced braces
opens = script.count('{')
closes = script.count('}')
print(f'Braces: {{ = {opens}, }} = {closes}, balanced = {opens == closes}')

# Check for balanced parens
opens_p = script.count('(')
closes_p = script.count(')')
print(f'Parens: ( = {opens_p}, ) = {closes_p}, balanced = {opens_p == closes_p}')

# Check for balanced backticks
backticks = script.count('`')
print(f'Backticks: {backticks}, balanced = {backticks % 2 == 0}')
