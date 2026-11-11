import csv
import json
from html.parser import HTMLParser

import pytest

from algorithms import analytics, data_manager
from app import app


SHORT = 'Computer Engineering & IT'
LONG = 'Computer Engineering & Information Technology'


@pytest.fixture
def ds(tmp_path, monkeypatch):
    tables = [
        ('faculty.csv', data_manager.FACULTY_COLUMNS, [
            {'faculty_id': 'a', 'name': 'Alice', 'department': SHORT},
            {'faculty_id': 'b', 'name': 'Bob', 'department': SHORT},
            {'faculty_id': 'c', 'name': 'Carol', 'department': LONG},
            {'faculty_id': 'd', 'name': 'Dana', 'department': 'No Papers'},
            {'faculty_id': 'e', 'department': 'No Keywords'},
        ]),
        ('papers.csv', data_manager.PAPER_COLUMNS, [
            {'paper_id': 'same', 'title': 'Same department', 'year': '2024', 'keywords': 'AI; ai; IoT'},
            {'paper_id': 'cross', 'title': 'Cross department', 'year': '2025', 'keywords': 'ai; Vision'},
            {'paper_id': 'long', 'title': 'Long department only', 'keywords': 'Robotics'},
            {'paper_id': 'blank'},
            {'paper_id': 'unlinked', 'keywords': 'Ignore'},
        ]),
        ('authorship.csv', data_manager.AUTHORSHIP_COLUMNS, [
            {'paper_id': 'same', 'faculty_id': 'a'},
            {'paper_id': 'same', 'faculty_id': 'b'},
            {'paper_id': 'same', 'faculty_id': 'b'},
            {'paper_id': 'cross', 'faculty_id': 'a'},
            {'paper_id': 'cross', 'faculty_id': 'c'},
            {'paper_id': 'long', 'faculty_id': 'c'},
            {'paper_id': 'blank', 'faculty_id': 'e'},
        ]),
    ]
    for filename, fields, rows in tables:
        with (tmp_path / filename).open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    monkeypatch.setattr(data_manager, 'DATA_DIR', str(tmp_path))
    return data_manager.Dataset()


def test_same_department_papers_and_keyword_counts(ds):
    result = analytics.department_summary(ds, SHORT)
    assert result['name'] == SHORT
    assert [f['faculty_id'] for f in result['faculty']] == ['a', 'b']
    assert [p['paper_id'] for p in result['publications']] == ['cross', 'same']
    assert result['top_keywords']['labels'] == ['AI', 'IoT', 'Vision']
    assert result['top_keywords']['values'] == [2, 1, 1]
    assert json.loads(json.dumps(result)) == result


def test_cross_department_and_exact_names(ds):
    short = analytics.department_summary(ds, SHORT)
    long = analytics.department_summary(ds, LONG)
    assert [f['faculty_id'] for f in long['faculty']] == ['c']
    assert [p['paper_id'] for p in long['publications']] == ['cross', 'long']
    assert short['publications'][0]['paper_id'] == long['publications'][0]['paper_id']
    assert long['top_keywords']['labels'] == ['AI', 'Robotics', 'Vision']
    assert long['top_keywords']['values'] == [1, 1, 1]


def test_known_without_papers(ds):
    result = analytics.department_summary(ds, 'No Papers')
    assert len(result['faculty']) == 1
    assert result['publications'] == []
    assert result['top_keywords']['labels'] == []
    assert result['top_keywords']['values'] == []


def test_missing_keywords_and_display_fields(ds):
    result = analytics.department_summary(ds, 'No Keywords')
    assert result['faculty'][0]['name'] == 'Not listed'
    assert result['top_keywords']['labels'] == []
    paper = result['publications'][0]
    assert paper['keywords'] == []
    for key in ('title', 'year', 'venue', 'doi'):
        assert paper[key] == 'Not listed'


@pytest.mark.parametrize('name', ['Unknown', '', SHORT.lower(), SHORT + ' '])
def test_unknown_department(ds, name):
    assert analytics.department_summary(ds, name) is None


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.hrefs.extend(value for key, value in attrs if key == 'href')


def test_directory_links_and_routes_with_spaces_ampersand(ds):
    with app.test_client() as client:
        parser = Links()
        parser.feed(client.get('/faculty').get_data(as_text=True))
        with app.test_request_context():
            from flask import url_for
            short_url = url_for('department_detail', name=SHORT)
            long_url = url_for('department_detail', name=LONG)
        assert short_url != long_url
        assert '%20' in short_url
        for url, included, excluded in [
            (short_url, 'Same department', 'Long department only'),
            (long_url, 'Long department only', 'Same department'),
        ]:
            assert url in parser.hrefs
            response = client.get(url)
            assert response.status_code == 200
            html = response.get_data(as_text=True)
            assert included in html and excluded not in html
            assert html.count('Cross department') == 1
        assert 'href="/compare"' in client.get('/faculty').get_data(as_text=True)


@pytest.mark.parametrize('name,expected', [
    ('No Papers', ['No publications linked', 'No keywords listed', 'Dana']),
    ('No Keywords', ['No keywords listed', 'Keywords: Not listed', 'Venue: Not listed']),
])
def test_route_empty_states(ds, name, expected):
    with app.test_client() as client:
        response = client.get('/department/' + name.replace(' ', '%20'))
        assert response.status_code == 200
        for text in expected:
            assert text in response.get_data(as_text=True)


def test_unknown_route(ds):
    with app.test_client() as client:
        assert client.get('/department/Unknown').status_code == 404
