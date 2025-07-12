#!/usr/bin/env python3

# Read the file
with open('chart/templates/chart_form.html', 'r') as f:
    content = f.read()

# Replace the gemini-pro model with mistral-7b
old_gemini = '''            'gemini-pro': {
                name: 'Gemini Pro',
                description: 'Google\'s latest model with strong analytical capabilities',
                max_tokens: 2048,
                temperature: 0.7
            },'''

new_mistral = '''            'mistral-7b': {
                name: 'Mistral 7B',
                description: 'Fast and efficient open source model',
                max_tokens: 2048,
                temperature: 0.7
            },'''

content = content.replace(old_gemini, new_mistral)

# Write the file back
with open('chart/templates/chart_form.html', 'w') as f:
    f.write(content)

print("Successfully replaced gemini-pro with mistral-7b in frontend")