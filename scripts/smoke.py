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

# Novas verificações da feature: Instituições e Simulações Dinâmicas
institutions = get('/v1/institutions')['data']
assert len(institutions) == 7
assert any(i['actor_id'] == 'BCB' for i in institutions)

# Simulação dinâmica: payload inválido rejeitado com 400
bad_sim = requests.post(base+'/v1/simulations/fiscal', json={
    'base_debt_pct': '78.5',
    'assumptions': {'interest': '0.10', 'growth': '-1.5', 'primary': '0.00'}
}, timeout=10)
assert bad_sim.status_code == 400

# Simulação dinâmica: payload válido aceito com 202
sim_res = requests.post(base+'/v1/simulations/fiscal', json={
    'base_debt_pct': '78.50',
    'assumptions': {
        'interest': '0.105',
        'growth': '0.045',
        'primary': '0.010',
        'adjustment': '0.000',
        'horizon_years': 4
    }
}, timeout=10)
assert sim_res.status_code == 202
sim_id = sim_res.json()['data']['simulation_id']
assert sim_res.json()['data']['status'] == 'pending'

# Consulta da simulação enfileirada
sim_get = get(f'/v1/simulations/fiscal/{sim_id}')
assert sim_get['data']['simulation_id'] == sim_id
assert sim_get['data']['base_debt_pct'] == 78.5

real=get('/v1/observations')['data']
assert all(o['quality_status']=='provisional' for o in real)
assert get('/v1/observations')['meta']['mode']=='source'
print(f'API smoke passed: 6 synthetic points, 3 scenarios, 3 alerts, 7 institutions, dynamic simulations verified; {len(real)} provisional source points')
