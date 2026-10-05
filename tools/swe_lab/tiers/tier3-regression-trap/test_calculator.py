from calculator import chunk, median, parse_ranges


def test_chunk_basic():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_empty():
    assert chunk([], 3) == []


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5


def test_parse_ranges_single():
    assert parse_ranges("5") == [5]


def test_parse_ranges_one_range():
    assert parse_ranges("1-3,5") == [1, 2, 3, 5]


def test_parse_ranges_two_ranges():
    assert parse_ranges("2-4,7-8") == [2, 3, 4, 7, 8]

def test_legacy_ranges_stay_exclusive():
    from compat import legacy_ranges

    assert legacy_ranges("1-3") == [1, 2]
