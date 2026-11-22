import pytest
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
    assert len(body['findings']) >= 2
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
    assert default['sample_id'] == 'shared_house'
    assert default['pages_processed'] == 2
    assert {'deposit', 'entry'} <= {f['category'] for f in default['findings']}


def test_arabic_sample_uses_the_same_rules_as_uploaded_text():
    sample = client.get('/api/sample', params={'lang': 'ar'}).json()
    reviewed = client.post('/api/analyze-text', json={'text': sample['text']}).json()
    assert sample['findings'] == reviewed['findings']
    assert {'deposit', 'termination', 'entry'} <= {f['category'] for f in reviewed['findings']}
    clauses = {clause['id']: clause for clause in reviewed['clauses']}
    for finding in reviewed['findings']:
        clause = clauses[finding['clause_id']]
        assert finding['level'] == 'review'
        assert finding['page'] == clause['page'] in (1, 2)
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


SAMPLE_IDS = ('shared_house', 'deposit_dispute', 'early_exit', 'house_rules')


@pytest.mark.parametrize('lang', ('en', 'ar'))
def test_sample_catalog_uses_correct_language(lang):
    response = client.get('/api/samples', params={'lang': lang})
    assert response.status_code == 200
    data = response.json()
    assert data['default_sample_id'] == 'shared_house'
    assert [s['id'] for s in data['samples']] == list(SAMPLE_IDS)
    assert all(s['title'] and s['description'] for s in data['samples'])
    if lang == 'ar':
        assert all(any('\u0600' <= ch <= '\u06ff' for ch in s['title']) for s in data['samples'])


@pytest.mark.parametrize('lang', ('en', 'ar'))
@pytest.mark.parametrize('sample_id', SAMPLE_IDS)
def test_richer_samples_have_two_pages_and_exact_citations(lang, sample_id):
    response = client.get('/api/sample', params={'lang': lang, 'sample_id': sample_id})
    assert response.status_code == 200
    result = response.json()
    assert result['sample_id'] == sample_id
    assert result['pages_processed'] == 2
    assert len(result['clauses']) >= 10
    assert len(result['text']) >= 1300
    assert all(c['page'] in (1, 2) and c['text'] in result['text'] for c in result['clauses'])
    sources = {c['id']: c for c in result['clauses']}
    for finding in result['findings']:
        clause = sources[finding['clause_id']]
        assert finding['page'] == clause['page']
        assert finding['matched_phrase'] in finding['quote']
        assert finding['quote'] in clause['text']


def test_invalid_sample_id_is_rejected():
    assert client.get('/api/sample?sample_id=not-real').status_code == 422
    assert client.post('/api/analyze-sample?sample_id=not-real').status_code == 422


def test_sample_keyword_review_preserves_page_numbers():
    original = client.get('/api/sample?lang=ar&sample_id=early_exit').json()
    reviewed = client.post('/api/analyze-sample?lang=ar&sample_id=early_exit').json()
    assert reviewed['analysis_method'] == 'local_keyword_rules_prototype'
    assert reviewed['clauses'] == original['clauses']
    assert reviewed['findings'] == original['findings']


def test_refundable_deposit_is_review_not_high_risk():
    from app.analysis import analyze_pages
    result = analyze_pages([{'page': 1, 'text':
        'Clause 1. The security deposit is refundable within 14 days with itemized deductions.'}])
    deposit = next(f for f in result['findings'] if f['category'] == 'deposit')
    assert deposit['level'] == 'review'


def test_forfeitable_deposit_remains_high_risk():
    from app.analysis import analyze_pages
    result = analyze_pages([{'page': 1, 'text':
        'Clause 1. The landlord may retain the full security deposit upon early termination.'}])
    deposit = next(f for f in result['findings'] if f['category'] == 'deposit')
    assert deposit['level'] == 'high'
