"""Read-only API smoke checks against a locally seeded pilot."""
import os
import requests

base=os.getenv('BDF_API_URL','http://127.0.0.1:18080')
def get(path):
    response=requests.get(base+path,timeout=10)
    response.raise_for_status()
    return response.json()

assert get('/healthz')['status']=='ok'
assert len(get('/v1/indicators')['data']['domains'])==12
synthetic=get('/v1/observations?mode=fixture')
assert len(synthetic['data'])==6
assert all(o['quality_status']=='synthetic' for o in synthetic['data'])
assert get('/v1/observations?mode=fixture&as_of=2020-01-01T00:00:00Z')['data']==[]
assert len(get('/v1/indicators/br.debt.gross_pct_gdp/observations?mode=fixture')['data'])==2
assert len(get('/v1/scenarios?mode=fixture')['data'])==3
assert len(get('/v1/alerts?mode=fixture')['data'])==3
assert requests.get(base+'/v1/observations?mode=invalid',timeout=10).status_code==400
assert requests.get(base+'/v1/observations?as_of=2025-01-01',timeout=10).status_code==400
assert requests.post(base+'/v1/alerts',timeout=10).status_code==405
real=get('/v1/observations')['data']
assert all(o['quality_status']=='provisional' for o in real)
assert get('/v1/observations')['meta']['mode']=='source'
print(f'API smoke passed: 6 synthetic points, 3 scenarios, 3 alerts; {len(real)} provisional source points')
