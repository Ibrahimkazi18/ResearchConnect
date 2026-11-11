import csv
from unittest.mock import patch

import pytest

from algorithms import data_manager, expertise
from app import app


@pytest.fixture
def ds(tmp_path, monkeypatch):
    tables = [
        ('faculty.csv', data_manager.FACULTY_COLUMNS, [
            {'faculty_id': 'a', 'name': 'Alice', 'department': 'Computer Science', 'expertise': 'IoT'},
            {'faculty_id': 'b', 'name': 'Bob', 'expertise': 'Vision; Robotics'},
            {'faculty_id': 'c', 'name': 'Carol', 'expertise': 'Physics'},
            {'faculty_id': 'empty', 'name': 'Empty'},
            {'faculty_id': 'blank'},
        ]),
        ('papers.csv', data_manager.PAPER_COLUMNS, [
            {'paper_id': 'p1', 'keywords': 'AI; ai; IoT'},
            {'paper_id': 'p2', 'keywords': 'ai; Robotics; Vision'},
        ]),
        ('authorship.csv', data_manager.AUTHORSHIP_COLUMNS, [
            {'paper_id': 'p1', 'faculty_id': 'a'},
            {'paper_id': 'p2', 'faculty_id': 'b'},
        ]),
    ]
    for filename, fields, rows in tables:
        with (tmp_path / filename).open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    monkeypatch.setattr(data_manager, 'DATA_DIR', str(tmp_path))
    return data_manager.Dataset()


@pytest.fixture
def client(ds):
    with app.test_client() as client:
        yield client


def test_overlap_and_build_once(ds):
    with patch.object(expertise, 'build_profiles', wraps=expertise.build_profiles) as build:
        result = expertise.compare_faculty(ds, 'a', 'b')
    build.assert_called_once_with(ds)
    assert result['score'] == 25.0
    assert result['shared'] == ['AI']
    assert result['unique_a'] == ['IoT']
    assert result['unique_b'] == ['Robotics', 'Vision']
    assert result['keywords_a'] == ['AI', 'IoT']
    assert result['faculty_b']['department'] == 'Not listed'
    assert not result['self_comparison']


@pytest.mark.parametrize('a,b,score,shared,unique_a,unique_b', [
    ('a', 'c', 0, [], ['AI', 'IoT'], ['Physics']),
    ('empty', 'blank', 0, [], [], []),
    ('a', 'empty', 0, [], ['AI', 'IoT'], []),
    ('a', 'a', 100, ['AI', 'IoT'], [], []),
    ('empty', 'empty', 0, [], [], []),
])
def test_comparison_sets(ds, a, b, score, shared, unique_a, unique_b):
    result = expertise.compare_faculty(ds, a, b)
    assert result['score'] == score
    assert result['shared'] == shared
    assert result['unique_a'] == unique_a
    assert result['unique_b'] == unique_b
    assert result['self_comparison'] == (a == b)


def test_missing_display_name(ds):
    assert expertise.compare_faculty(ds, 'blank', 'a')['faculty_a']['name'] == 'Not listed'


def test_sort_normalized_before_mapping_labels(ds):
    ds.keyword_labels.update({'ai': 'zAI', 'iot': 'aIoT'})
    assert expertise.compare_faculty(ds, 'a', 'a')['shared'] == ['zAI', 'aIoT']


@pytest.mark.parametrize('a,b', [('unknown', 'a'), ('a', 'unknown'), ('', 'a')])
def test_unknown_function_ids(ds, a, b):
    with pytest.raises(ValueError, match='known faculty'):
        expertise.compare_faculty(ds, a, b)


def test_initial_and_directory_link(client):
    response = client.get('/compare')
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '<label class="form-label" for="faculty-a">Faculty A</label>' in html
    assert '<label class="form-label" for="faculty-b">Faculty B</label>' in html
    assert 'Comparison result' not in html
    assert 'role="alert"' not in html
    assert 'href="/compare"' in client.get('/faculty').get_data(as_text=True)


def test_valid_route(client):
    response = client.get('/compare', query_string={'a': 'a', 'b': 'b'})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'Jaccard similarity: 25.0%' in html
    assert 'Alice' in html and 'Bob' in html
    assert 'Shared keywords' in html and 'Unique keywords' in html
    assert 'value="a" selected' in html and 'value="b" selected' in html
    assert 'Not listed' in html


@pytest.mark.parametrize('query,message,selected', [
    ({'a': 'a'}, 'Select both faculty members', 'a'),
    ({'b': 'b'}, 'Select both faculty members', 'b'),
    ({'a': '', 'b': ''}, 'Select both faculty members', None),
    ({'a': 'a', 'b': 'unknown'}, 'Unknown faculty selection', 'a'),
    ({'a': 'unknown', 'b': 'b'}, 'Unknown faculty selection', 'b'),
])
def test_validation(client, query, message, selected):
    response = client.get('/compare', query_string=query)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert message in html
    assert 'Comparison result' not in html
    if selected:
        assert f'value="{selected}" selected' in html


@pytest.mark.parametrize('a,b,text', [
    ('a', 'a', 'same faculty member twice'),
    ('empty', 'blank', 'Two empty keyword sets score 0%'),
    ('a', 'c', 'No shared keywords'),
    ('a', 'empty', 'No keywords listed'),
])
def test_route_empty_and_self_states(client, a, b, text):
    response = client.get('/compare', query_string={'a': a, 'b': b})
    assert response.status_code == 200
    assert text in response.get_data(as_text=True)


def test_no_faculty(client, tmp_path):
    with (tmp_path / 'faculty.csv').open('w', newline='') as handle:
        csv.writer(handle).writerow(data_manager.FACULTY_COLUMNS)
    response = client.get('/compare')
    assert response.status_code == 200
    assert 'No faculty data' in response.get_data(as_text=True)
