"""
核心工具函数单元测试
运行: pytest tests/test_utils.py -v
覆盖: clamp_pagination, validate_date, _month_to_range, _year_to_range,
      calculate_overtime_duration, sanitize_csv_field
"""
import pytest
from app import clamp_pagination, validate_date, _month_to_range, _year_to_range, calculate_overtime_duration, sanitize_csv_field, EXPENSE_CATEGORIES
from app import app as flask_app


class TestClampPagination:
    @pytest.mark.parametrize('page,page_size,expected', [
        (1, 5, (1, 5)), (1, 10, (1, 10)), (1, 15, (1, 15)),
        (0, 5, (1, 5)), (-1, 5, (1, 5)),
        (1, 3, (1, 5)), (1, 0, (1, 5)), (1, -5, (1, 5)),
        (1, 20, (1, 15)), (1, 999, (1, 15)),
        ('abc', 'xyz', (1, 5)), (None, None, (1, 5)),
    ])
    def test(self, page, page_size, expected):
        assert clamp_pagination(page, page_size) == expected


class TestValidateDate:
    @pytest.fixture(autouse=True)
    def _ctx(self):
        with flask_app.app_context():
            yield

    @pytest.mark.parametrize('d,err', [
        ('2026-07-08', False), ('2026-01-01', False), ('2024-02-29', False),
        ('', True), ('2026-07-32', True), ('2026/07/08', True),
        ('07-08-2026', True), ('2026-7-8', True), ('2026-13-01', True),
    ])
    def test(self, d, err):
        r = validate_date(d)
        assert (r is not None) == err


class TestMonthToRange:
    @pytest.mark.parametrize('m,expected', [
        ('2026-01', ('2026-01-01', '2026-02-01')),
        ('2026-12', ('2026-12-01', '2027-01-01')),
        ('abc', (None, None)), ('2026-13', (None, None)),
    ])
    def test(self, m, expected):
        assert _month_to_range(m) == expected


class TestYearToRange:
    @pytest.mark.parametrize('y,expected', [
        ('2026', ('2026-01-01', '2027-01-01')),
        ('abc', (None, None)), ('', (None, None)),
    ])
    def test(self, y, expected):
        assert _year_to_range(y) == expected


class TestOvertimeDuration:
    def test_weekday(self):
        assert calculate_overtime_duration('weekday', '19:00', '21:00') == 2.0

    def test_weekday_override(self):
        assert calculate_overtime_duration('weekday', '20:00', '22:00') == 3.0

    def test_weekend_lunch(self):
        assert calculate_overtime_duration('weekend', '09:00', '17:00') == 6.0

    def test_weekend_no_lunch(self):
        assert calculate_overtime_duration('weekend', '14:00', '17:00') == 3.0

    def test_weekend_partial_lunch(self):
        assert calculate_overtime_duration('weekend', '13:00', '15:00') == 1.0


class TestSanitizeCsv:
    @pytest.mark.parametrize('v,e', [
        ("=cmd|'x", "'=cmd|'x"), ("+x", "'+x"), ("-x", "'-x"), ("@x", "'@x"),
        ("ok", "ok"), ("", ""), (None, None),
    ])
    def test(self, v, e):
        assert sanitize_csv_field(v) == e


class TestExpenseCategories:
    def test_valid(self):
        assert '燃气费' in EXPENSE_CATEGORIES
    def test_invalid(self):
        assert '赌博' not in EXPENSE_CATEGORIES