#!/usr/bin/env python3
import json
import os
import re
from contextlib import suppress
from dataclasses import dataclass

import requests
import yaml
from github import Auth, Github, GithubException
from parse import parse

from issue_parser.parser import ParsedBody, parse_issue


@dataclass
class IssueBody:
    def __init__(self, issue_body: ParsedBody):
        self.device: str = issue_body['device']
        self.version: str = issue_body['version']
        self.date: str = issue_body['date']
        self.kernel: str = issue_body['kernel']
        self.baseband: str = issue_body['baseband']
        self.mods: str = issue_body['mods']
        self.expected: str = issue_body['expected']
        self.current: str = issue_body['current']
        self.solution: str = issue_body['solution']
        self.reproduce: str = issue_body['reproduce']
        self.directions: str = issue_body['directions']

        # Let's be friendly...
        for pattern in [
            'lineage-{:d}.{:d}-{}',
            'lineage {:d}.{:d}-{}',
            'lineage-{:d}.{:d}',
            'lineage {:d}.{:d}',
            'lineage-{:d}',
            'lineage {:d}',
            'lineageos-{:d}.{:d}-{}',
            'lineageos {:d}.{:d}-{}',
            'lineageos-{:d}.{:d}',
            'lineageos {:d}.{:d}',
            'lineageos-{:d}',
            'lineageos {:d}',
            'lineage os-{:d}.{:d}-{}',
            'lineage os {:d}.{:d}-{}',
            'lineage os-{:d}.{:d}',
            'lineage os {:d}.{:d}',
            'lineage os-{:d}',
            'lineage os {:d}',
            '{:d}.{:d}-{}',
            '{:d}.{:d}',
            '{:d}',
        ]:
            if version := parse(pattern, self.version):
                major = version.fixed[0]
                minor = version.fixed[1] if len(version.fixed) > 1 else 0
                self.version = f'lineage-{major}.{minor}'
                break


def device_list() -> dict:
    ret = {}

    for line in requests.get(
        'https://raw.githubusercontent.com/LineageOS/hudson/main/lineage-build-targets',
        timeout=5,
    ).text.splitlines():
        if ' lineage-' in line:
            codename, _, version, _ = line.split()
            ret[codename] = version

    return ret


def device_names() -> list:
    ret = []

    for x in requests.get(
        'https://raw.githubusercontent.com/LineageOS/hudson/main/updater/devices.json',
        timeout=5,
    ).json():
        ret.append((x['oem'], x['name'], x['model']))

    return ret


def device_maintainers(device: str) -> list:
    ret = []

    for url in [
        f'https://raw.githubusercontent.com/LineageOS/lineage_wiki/main/_data/devices/{device}.yml',
        f'https://raw.githubusercontent.com/LineageOS/lineage_wiki/main/_data/devices/{device}_variant1.yml',
    ]:
        req = requests.get(url, timeout=5)

        if req.status_code == 200:
            ret = yaml.safe_load(req.text)['maintainers']
            break

    if ret:
        req = requests.get(
            'https://raw.githubusercontent.com/LineageOS/lineage_wiki/main/_data/github_usernames.yml',
            timeout=5,
        )

        if req.status_code == 200:
            mapping = yaml.safe_load(req.text)['usernames']
            ret = [mapping.get(x, x) for x in ret]

    return ret


def issue_errors(issue: IssueBody) -> list:
    ret = []

    # Load supported devices list
    devices = device_list()

    for device in devices:
        if device.lower() == issue.device.lower():
            issue.device = device
            break
    else:
        names = device_names()
        names.sort(key=lambda x: (x[0].lower(), x[1].lower(), x[2].lower()))

        text = f'Device "{issue.device}" is not a valid device codename. Supported values are listed below:\n'
        text += '  <details>'
        text += '  <summary>Devices</summary>\n\n'
        text += '  | Vendor | Model | Codename |\n'
        text += '  |--------|-------|----------|\n'
        for vendor, device, codename in names:
            if codename in devices:
                text += f'  | {vendor} | {device} | {codename} |\n'
        text += '\n  </details>'

        ret.append(text)

    if device_version := devices.get(issue.device, None):
        if issue.version != device_version:
            ret.append(
                f'LineageOS version "{issue.version}" is not a valid LineageOS version. Supported value is: {device_version}'
            )

    if not re.findall(r'^\d{4}[-\/]?\d{2}[-\/]?\d{2}(-.*)?$', issue.date):
        ret.append(
            f'Build date "{issue.date}" is not a valid date. Valid date format is YYYYMMDD'
        )

    return ret


def main() -> None:
    # Auth to GitHub
    github = Github(auth=Auth.Token(os.environ.get('GITHUB_TOKEN')))

    # Get repo and issue
    repo = github.get_repo(os.environ.get('GITHUB_REPOSITORY'))
    issue = repo.get_issue(number=int(os.environ.get('ISSUE_NUMBER')))

    # Don't touch already labeled issue
    if [x for x in issue.get_labels() if x.name != 'invalid']:
        print('Labels count > 0, exiting.')
        return

    # Parse issue body
    try:
        with open(os.environ.get('GITHUB_EVENT_PATH')) as f:
            issue_body = json.load(f)['issue']['body']

        with open('.github/ISSUE_TEMPLATE/bugreport.yml') as f:
            issue_template = f.read()

        issue_body = IssueBody(parse_issue(issue_body, issue_template))
    except Exception:
        issue.create_comment(
            '\n'.join(
                [
                    "Hi! It appears that your issue doesn't use the correct template.",
                    'Please create a new one and make sure to select "Bug Report" template.',
                    '',
                    '(this action was performed by a bot)',
                ]
            )
        )
        issue.edit(state='closed')
        return

    # Close issue if there are any errors
    if errors := issue_errors(issue_body):
        issue.create_comment(
            '\n'.join(
                [
                    "Hi! It appears you didn't read or follow the provided issue template.",
                    'Please edit your issue to correct problems listed below.',
                    'For more information please see https://wiki.lineageos.org/how-to/bugreport.',
                    '',
                    'Problems:',
                    '',
                    *[f'* {x}' for x in errors],
                    '',
                    '(this action was performed by a bot)',
                ]
            )
        )
        with suppress(GithubException):
            repo.create_label('invalid', 'b60205')  # just in case
        issue.edit(state='closed', labels=['invalid'])
        return

    # Reopen if closed and label issue
    labels = [x.name for x in issue.labels if x.name != 'invalid']

    for label, color in [
        [f'device:{issue_body.device}', '0075ca'],
        [issue_body.version, '008672'],
    ]:
        with suppress(GithubException):
            repo.create_label(label, color)  # just in case
        labels.append(label)

    issue.edit(state='open', labels=labels)

    # Assign maintainers if possible
    for maintainer in device_maintainers(issue_body.device):
        try:
            user = github.get_user(maintainer)
            _, data = issue._requester.requestJsonAndCheck(
                'POST',
                f'{issue.url}/assignees',
                input={
                    'assignees': [user.login],
                },
            )

            if not any(x['id'] == user.id for x in data['assignees']):
                raise GithubException(status=400, message='User not added')
        except GithubException as e:
            print(
                f'::warning ::Failed to assign {maintainer}: {e.message}',
                flush=True,
            )

            if url := os.environ.get('DISCORD_WEBHOOK'):
                repository_name = os.environ.get('GITHUB_REPOSITORY_NAME')
                workflow_run_url = os.environ.get('GITHUB_WORKFLOW_RUN_URL')

                requests.post(
                    url,
                    json={
                        'username': 'GitHub',
                        'avatar_url': 'https://cdn.discordapp.com/avatars/1483379599995047987/e57fd67dc7ca0cc840a0e87a82281bc5',
                        'embeds': [
                            {
                                'title': f'[{repository_name}] Failed to assign {maintainer}: {e.message}',
                                'url': workflow_run_url,
                                'color': 15426592,
                            }
                        ],
                    },
                )


if __name__ == '__main__':
    main()
