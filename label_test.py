#!/usr/bin/env python3
import json
import pprint
import sys
from contextlib import suppress

from label import IssueBody, parse_issue


def main() -> None:
    with open(sys.argv[1]) as f:
        issue_body = f.read()

        with suppress(json.JSONDecodeError):
            issue_body = json.loads(issue_body)['issue']['body']

    with open('.github/ISSUE_TEMPLATE/bugreport.yml') as f:
        issue_template = f.read()

    issue_body = IssueBody(parse_issue(issue_body, issue_template))

    pprint.pp(issue_body.__dict__)


if __name__ == '__main__':
    main()
