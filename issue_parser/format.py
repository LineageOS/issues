from __future__ import annotations

import re

from issue_parser.enums import EmptyResponse, FieldType
from issue_parser.types import FormattedField, ParsedValue


def is_empty_response(value: str) -> bool:
    lowered = value.lower()
    return lowered == EmptyResponse.NO_RESPONSE.value.lower() or value == ''


def format_key(name: str) -> str:
    return re.sub(
        r'_+',
        '_',
        re.sub(r'^_+|_+$', '', re.sub(r'[^a-z0-9]', '_', name.strip().lower())),
    )


def format_value(
    input_value: str, field: FormattedField | None = None
) -> ParsedValue:
    checked_exp = re.compile(r'^-\s\[x\]\s', re.IGNORECASE)

    value = input_value.strip().replace('\r', '')
    value = re.sub(r'^[\n]+|[\n]+$', '', value)

    if field is None:
        return value

    if field.type in (FieldType.INPUT.value, FieldType.TEXTAREA.value):
        return None if is_empty_response(value) else value

    if field.type == FieldType.DROPDOWN.value:
        return [] if is_empty_response(value) else re.split(r', *', value)

    if field.type == FieldType.CHECKBOXES.value:
        checkboxes = {
            'selected': [],
            'unselected': [],
        }

        if is_empty_response(value):
            return checkboxes

        for line in value.split('\n'):
            line = line.strip()
            if checked_exp.search(line):
                checkboxes['selected'].append(
                    re.sub(
                        r'-\s\[x\]\s', '', line, count=1, flags=re.IGNORECASE
                    )
                )
            else:
                checkboxes['unselected'].append(
                    re.sub(
                        r'-\s\[\s\]\s', '', line, count=1, flags=re.IGNORECASE
                    )
                )

        return checkboxes

    raise ValueError(f'Unknown field type: {field.type}')
