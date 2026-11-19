from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    assert client.get('/api/health').json()['status'] == 'ok'

def test_sample_has_grounded_flags():
    res = client.get('/api/sample')
    assert res.status_code == 200
    body = res.json()
    assert len(body['findings']) >= 3
    ids = {c['id'] for c in body['clauses']}
    assert all(f['clause_id'] in ids for f in body['findings'])
    assert all(f['quote'] for f in body['findings'])

def test_text_analysis_does_not_invent_issues():
    body = client.post('/api/analyze-text', json={'text':'The tenant will reside in the unit from January until June.'}).json()
    assert body['findings'] == []

def test_upload_rejects_wrong_extension():
    response = client.post('/api/analyze-file', files={'file': ('test.txt', b'hello', 'text/plain')})
    assert response.status_code == 415
