from issue_parser.format import format_key, format_value
from issue_parser.types import FormattedField


def test_format_key_removes_non_alphanumeric_characters() -> None:
    assert format_key('!@#$%^&*()_+') == ''


def test_format_key_converts_to_lowercase() -> None:
    assert format_key('ABC') == 'abc'


def test_format_key_replaces_spaces_with_underscores() -> None:
    assert format_key('a b c') == 'a_b_c'


def test_format_key_replaces_multiple_underscores() -> None:
    assert format_key('a__b__c') == 'a_b_c'


def test_format_key_removes_leading_and_trailing_underscores() -> None:
    assert format_key('_abc_') == 'abc'


def test_format_key_removes_leading_and_trailing_whitespace() -> None:
    assert format_key(' abc ') == 'abc'


def test_format_key_handles_empty_strings() -> None:
    assert format_key('') == ''


def test_format_value_throws_on_invalid_type() -> None:
    try:
        format_value(
            'ABCDEF',
            FormattedField(label='Bad', type='invalid', required=True),
        )
    except ValueError as err:
        assert str(err) == 'Unknown field type: invalid'
    else:
        raise AssertionError('Expected ValueError')


def test_format_value_handles_empty_strings() -> None:
    assert (
        format_value(
            '', FormattedField(label='Input Test', type='input', required=True)
        )
        is None
    )


def test_format_value_handles_no_response_for_dropdown() -> None:
    assert (
        format_value(
            '_No response_',
            FormattedField(
                label='Dropdown Test',
                type='dropdown',
                required=True,
                multiple=False,
                options=['a', 'b', 'c'],
            ),
        )
        == []
    )


def test_format_value_handles_checkboxes() -> None:
    value = """- [ ] a
- [x] b
- [ ] c
- [x] d
- [ ] e"""

    assert format_value(
        value,
        FormattedField(
            label='Checkboxes Test',
            type='checkboxes',
            required=True,
            options=['a', 'b', 'c'],
        ),
    ) == {
        'selected': ['b', 'd'],
        'unselected': ['a', 'c', 'e'],
    }


def test_format_value_handles_no_checkboxes() -> None:
    assert format_value(
        '',
        FormattedField(
            label='Checkboxes Test',
            type='checkboxes',
            required=True,
            options=['a', 'b', 'c'],
        ),
    ) == {'selected': [], 'unselected': []}


def test_format_value_handles_multiline_strings() -> None:
    value = 'a\nb\nc'
    assert (
        format_value(
            value,
            FormattedField(label='Textarea', type='textarea', required=True),
        )
        == value
    )
