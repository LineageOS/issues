from enum import Enum


class FieldType(str, Enum):
    """Issue form field types."""

    CHECKBOXES = 'checkboxes'
    DROPDOWN = 'dropdown'
    INPUT = 'input'
    MARKDOWN = 'markdown'
    TEXTAREA = 'textarea'


class EmptyResponse(str, Enum):
    """Special strings used by GitHub issue forms for empty values."""

    NO_RESPONSE = '_No response_'
