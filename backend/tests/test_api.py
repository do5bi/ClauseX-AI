from fastapi.testclient import TestClient
import pymupdf
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


def test_sample_defaults_to_existing_english_agreement():
    default = client.get('/api/sample').json()
    assert default == client.get('/api/sample', params={'lang': 'en'}).json()
    assert [finding['category'] for finding in default['findings']] == [
        'deposit', 'termination', 'fees', 'entry'
    ]


def test_arabic_sample_uses_the_same_rules_as_uploaded_text():
    sample = client.get('/api/sample', params={'lang': 'ar'}).json()
    reviewed = client.post('/api/analyze-text', json={'text': sample['text']}).json()
    assert sample['findings'] == reviewed['findings']
    assert {f['category'] for f in reviewed['findings']} == {
        'deposit', 'termination', 'fees', 'entry', 'maintenance'
    }
    clauses = {clause['id']: clause for clause in reviewed['clauses']}
    for finding in reviewed['findings']:
        clause = clauses[finding['clause_id']]
        assert finding['level'] == 'review'
        assert finding['page'] == clause['page'] == 1
        assert finding['matched_phrase'] in finding['quote'] in clause['text']
        assert clause['text'] in sample['text']


def test_arabic_evidence_keeps_original_page_and_phrase():
    from app.analysis import analyze_pages

    result = analyze_pages([
        {'page': 1, 'text': 'تقع الغرفة في الطابق الثاني.'},
        {'page': 2, 'text': 'يدفع الطالب وديعة تأمين عند تسلّم الغرفة.'},
    ])
    finding, = result['findings']
    assert (finding['page'], finding['matched_phrase']) == (2, 'وديعة تأمين')


def test_uploaded_arabic_pdf_preserves_extracted_glyphs_in_evidence():
    with pymupdf.open() as document:
        document.new_page().insert_text((72, 72), 'Student rental agreement')
        document.new_page().insert_htmlbox(
            pymupdf.Rect(50, 50, 400, 150), '<p dir="rtl">رسوم إضافية</p>'
        )
        extracted = document[1].get_text().strip()
        pdf = document.tobytes()
    response = client.post('/api/analyze-file', files={'file': ('lease.pdf', pdf, 'application/pdf')})
    assert response.status_code == 200
    finding, = response.json()['findings']
    assert (finding['category'], finding['page']) == ('fees', 2)
    assert finding['matched_phrase'] == extracted == finding['quote']
