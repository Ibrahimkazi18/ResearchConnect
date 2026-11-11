import csv

import pytest

from algorithms import analytics, data_manager


@pytest.fixture
def dataset_factory(tmp_path, monkeypatch):
    monkeypatch.setattr(data_manager, 'DATA_DIR', str(tmp_path))

    def make(papers):
        for filename, fields, rows in [
            ('faculty.csv', data_manager.FACULTY_COLUMNS, []),
            ('papers.csv', data_manager.PAPER_COLUMNS, papers),
            ('authorship.csv', data_manager.AUTHORSHIP_COLUMNS, []),
        ]:
            with (tmp_path / filename).open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        return data_manager.Dataset()

    return make


def test_keyword_trends_exact_counts_and_order(dataset_factory):
    ds = dataset_factory([
        {'paper_id': 'p1', 'year': '2025', 'keywords': 'Vision; AI; ai; AI; IoT'},
        {'paper_id': 'p2', 'year': '2023', 'keywords': 'iot; Ai'},
        {'paper_id': 'p3', 'year': '2025.0', 'keywords': 'ai; VISION'},
        {'paper_id': 'p4', 'year': '2024', 'keywords': 'IoT; Machine   Learning'},
        {'paper_id': 'p5', 'year': '2025', 'keywords': 'machine learning'},
        {'paper_id': 'p6', 'year': '2022', 'keywords': ''},
    ])
    expected = {
        'ai': {2023: 1, 2025: 2},
        'iot': {2023: 1, 2024: 1, 2025: 1},
        'machine learning': {2024: 1, 2025: 1},
        'vision': {2025: 2},
    }
    result = analytics.keyword_trends(ds)
    assert result == expected
    assert list(result) == list(expected)
    for keyword, years in result.items():
        assert list(years) == list(expected[keyword])
        assert all(type(year) is int and type(count) is int for year, count in years.items())


def test_excludes_missing_and_invalid_years(dataset_factory):
    ds = dataset_factory([
        {'paper_id': 'valid', 'year': '2024', 'keywords': 'AI'},
        {'paper_id': 'missing', 'keywords': 'AI; Missing'},
        {'paper_id': 'text', 'year': 'unknown', 'keywords': 'AI; Invalid'},
        {'paper_id': 'early', 'year': '1899', 'keywords': 'AI; Invalid'},
        {'paper_id': 'late', 'year': '2101', 'keywords': 'AI; Invalid'},
    ])
    assert analytics.keyword_trends(ds) == {'ai': {2024: 1}}
    assert analytics.data_coverage(ds)['papers_without_year'] == 4


@pytest.mark.parametrize('papers', [
    [],
    [{'paper_id': 'blank', 'year': '2024', 'keywords': ''}],
    [{'paper_id': 'missing', 'keywords': 'AI'}],
    [{'paper_id': 'invalid', 'year': 'invalid', 'keywords': 'AI'}],
])
def test_no_valid_observations(dataset_factory, papers):
    assert analytics.keyword_trends(dataset_factory(papers)) == {}
