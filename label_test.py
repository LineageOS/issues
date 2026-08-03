#!/usr/bin/env python3
import json
import sys

from label import IssueBody, parse_issue


def main() -> None:
    with open(sys.argv[1]) as f:
        issue_body = json.load(f)['issue']['body']

    with open('.github/ISSUE_TEMPLATE/bugreport.yml') as f:
        issue_template = f.read()

    issue_body = IssueBody(parse_issue(issue_body, issue_template))

    for key, value in issue_body.__dict__.items():
        print(f'{key}:\n{value}\n')


if __name__ == '__main__':
    main()
