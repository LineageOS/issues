from __future__ import annotations

import re
from typing import Any

import yaml

from issue_parser.enums import FieldType
from issue_parser.format import format_key, format_value
from issue_parser.types import (
    CheckboxOption,
    FormattedField,
    ParsedBody,
    TemplateDict,
)


def parse_issue(
    issue: str,
    template: str | None = None,
    options: dict[str, bool] | None = None,
) -> ParsedBody:
    regexp = re.compile(
        r'### *(?P<key>.*?)\s*[\r\n]+(?P<value>[\s\S]*?)(?=\n?###|\n?$)'
    )
    matches = list(regexp.finditer(issue))
    parsed_issue: ParsedBody = {}

    if template is not None:
        parsed_template = parse_template(template)
        parsed_matches: list[dict[str, str]] = []

        for match in matches:
            key = match.group('key')
            value = match.group('value')

            if key is None or value is None or key == '':
                continue

            if any(field.label == key for field in parsed_template.values()):
                parsed_matches.append(
                    {'key': key, 'value': value, 'full': match.group(0)}
                )
                continue

            if value == '' or len(parsed_matches) == 0:
                continue

            parsed_matches[-1]['value'] = (
                parsed_matches[-1]['value'] + '\n' + match.group(0)
            )

        for match in parsed_matches:
            value = match['value']

            if value.strip() == '':
                continue

            key = match['key']

            for parsed_key, parsed_field in parsed_template.items():
                if parsed_field.label == key:
                    key = parsed_key
                    break

            parsed_issue[key] = format_value(value, parsed_template.get(key))
    else:
        for match in matches:
            key = match.group('key')
            value = match.group('value')

            if key is None or value is None or key == '' or value == '':
                continue

            if options is not None and options.get('slugify'):
                key = format_key(key)

            parsed_issue[key] = format_value(value)

    return parsed_issue


def parse_template(template: str | None = None) -> TemplateDict:
    if not template:
        return {}

    fields = yaml.safe_load(template)

    if not isinstance(fields, dict):
        raise ValueError('Issue template could not be parsed into an object.')

    if not isinstance(fields.get('body'), list):
        raise ValueError('Issue template is missing a body array property.')

    parsed_template: TemplateDict = {}

    for item in fields['body']:
        if item.get('type') == FieldType.MARKDOWN.value:
            continue

        attributes: dict[str, Any] = item.get('attributes', {})
        label = attributes.get('label', '')

        key = item.get('id') or format_key(label)

        formatted = FormattedField(
            type=item.get('type'),
            label=label,
            required=item.get('validations', {}).get('required', False),
        )

        if item.get('type') == FieldType.DROPDOWN.value:
            formatted.multiple = attributes.get('multiple', False)
            formatted.options = attributes.get('options', [])

        if item.get('type') == FieldType.CHECKBOXES.value:
            formatted.options = [
                CheckboxOption(
                    label=option.get('label'),
                    required=option.get('required', False),
                )
                for option in attributes.get('options', [])
            ]

        parsed_template[key] = formatted

    return parsed_template
