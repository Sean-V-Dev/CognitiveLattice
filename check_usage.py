import json

with open('external_analysis_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
total_tokens = 0
for result in data['results']:
    tokens = result.get('tokens_used', 0)
    model = result.get('model_used', 'unknown')
    chunk_id = result.get('chunk_id', 'unknown')
    print(f'{chunk_id}: {tokens} tokens ({model})')
    total_tokens += tokens

print(f'\nTotal tokens used: {total_tokens}')
print(f'Total chunks processed: {len(data["results"])}')
print(f'API provider: {data["api_provider"]}')
