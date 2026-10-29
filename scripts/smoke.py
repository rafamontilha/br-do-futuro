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

# Verificações do Incremento 02: Saúde Operacional, Agendamentos e Replay
sources_health = get('/v1/health/sources')['data']
assert len(sources_health) >= 3
ipca_sched = next(s for s in sources_health if s['indicator_id'] == 'br.ipca.monthly')
assert ipca_sched['primary_source'] == 'IBGE_SIDRA'
assert ipca_sched['fallback_source'] == 'BCB_SGS'

# Replay sem justificativa: rejeitado com 400
bad_replay = requests.post(base+'/v1/admin/outbox/replay', json={'reason': '   '}, timeout=10)
assert bad_replay.status_code == 400

# Replay com justificativa: aceito com 202
good_replay = requests.post(base+'/v1/admin/outbox/replay', json={
    'reason': 'Teste automatizado de fumaça para replay de outbox',
    'triggered_by': 'smoke-test'
}, timeout=10)
assert good_replay.status_code == 202
replay_id = good_replay.json()['data']['replay_id']
assert replay_id.startswith('replay-')

# Consulta do registro de auditoria do replay
replay_get = get(f'/v1/admin/outbox/replay/{replay_id}')['data']
assert replay_get['id'] == replay_id
assert replay_get['status'] == 'completed'
assert replay_get['triggered_by'] == 'smoke-test'

# Verificações do Incremento 03: Propostas Públicas, Guidance e Calibrações
proposals = get('/v1/proposals')['data']
assert len(proposals) >= 3
assert any(p['id'] == 'prop-fiscal-mandatory-spending' for p in proposals)
assert any(p['id'] == 'prop-infra-investment-acceleration' for p in proposals)
assert any(p['id'] == 'prop-tax-reform-neutrality' for p in proposals)

single_prop = get('/v1/proposals/prop-fiscal-mandatory-spending')['data']
assert single_prop['institutional_competence'] == 'constitutional_amendment'
assert 'desindexação' in single_prop['causal_mechanism'].lower()
assert float(single_prop['cost_estimate_annual_brl']) == -45.0

bad_prop = requests.get(base+'/v1/proposals/nao-existe', timeout=10)
assert bad_prop.status_code == 404

commitments = get('/v1/guidance/commitments')['data']
assert len(commitments) >= 3
for comm in commitments:
    assert comm['human_review_required'] is True
    assert comm['status'] == 'experimental_hypothesis'
    assert comm['baseline_value'] is not None
    assert comm['target_value'] is not None

# Validação do corte temporal histórico (as_of) para evitar anacronismo
historical_guidance = get('/v1/guidance/commitments?as_of=2020-01-01T00:00:00Z')['data']
assert len(historical_guidance) == 0, "Guidance commitments cannot appear before creation date"

historical_proposals = get('/v1/proposals?as_of=2020-01-01T00:00:00Z')['data']
assert len(historical_proposals) == 0, "Proposals cannot appear before creation date"

calibrations = get('/v1/scenarios/calibrations')['data']
assert len(calibrations) >= 4

real=get('/v1/observations')['data']
assert all(o['quality_status']=='provisional' for o in real)
assert get('/v1/observations')['meta']['mode']=='source'
print(f'API smoke passed: 6 synthetic points, 3 scenarios, 3 alerts, 7 institutions, dynamic simulations, source health ({len(sources_health)} schedules), outbox replay, {len(proposals)} proposals, {len(commitments)} guidance commitments and {len(calibrations)} calibrations verified; {len(real)} provisional source points')
