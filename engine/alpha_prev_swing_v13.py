"""Fetch previous v1.3 artifact using the workflow token (read-only).

Fail closed: if a baseline cannot be authenticated or validated, no baseline is
written. Distinguish listing from archive-download failures in Actions logs.
"""
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

API = 'https://api.github.com'
OUT = Path('artifacts/previous_alpha_swing_v13.json')


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Never send the GitHub bearer token to a redirected non-API host."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        result = super().redirect_request(req, fp, code, msg, headers, newurl)
        if result is None:
            return None
        target = urllib.parse.urlparse(newurl)
        if target.hostname != 'api.github.com' or target.scheme != 'https':
            for key in list(result.headers):
                if key.lower() in ('authorization', 'cookie', 'proxy-authorization'):
                    del result.headers[key]
            for key in list(result.unredirected_hdrs):
                if key.lower() in ('authorization', 'cookie', 'proxy-authorization'):
                    del result.unredirected_hdrs[key]
        return result


def get_bytes(opener, url, headers, limit, timeout):
    request = urllib.request.Request(url, headers=headers)
    with opener.open(request, timeout=timeout) as response:
        payload = response.read(limit + 1)
        if len(payload) > limit:
            raise ValueError('response_too_large')
        return payload


def main():
    repo = os.getenv('GITHUB_REPOSITORY', '')
    token = os.getenv('GITHUB_TOKEN', '')
    current_run = os.getenv('GITHUB_RUN_ID', '')
    if not repo or not token:
        print('BASELINE_NOT_CONFIGURED')
        return

    headers = {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'alpha-v13-baseline',
    }
    opener = urllib.request.build_opener(SafeRedirect())
    stage = 'LIST_ARTIFACTS'
    try:
        url = f'{API}/repos/{repo}/actions/artifacts?name=alpha-swing-v13&per_page=100'
        payload = get_bytes(opener, url, headers, 2_000_000, 20)
        data = json.loads(payload)
        if not isinstance(data, dict) or not isinstance(data.get('artifacts'), list):
            raise ValueError('invalid_artifact_listing')
        candidates = sorted(
            (
                entry for entry in data['artifacts']
                if not entry.get('expired')
                and str(entry.get('workflow_run', {}).get('id')) != current_run
                and entry.get('archive_download_url')
            ),
            key=lambda entry: entry.get('created_at', ''),
            reverse=True,
        )
        if not candidates:
            print('NO_PREVIOUS_BASELINE')
            return

        stage = 'DOWNLOAD_ARCHIVE'
        archive_url = candidates[0]['archive_download_url']
        if not archive_url.startswith(API + '/repos/'):
            raise ValueError('unexpected_archive_host')
        raw = get_bytes(opener, archive_url, headers, 15_000_000, 35)

        stage = 'VALIDATE_ARCHIVE'
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            matches = [
                item for item in archive.infolist()
                if item.filename == 'alpha_swing_v13.json' and not item.is_dir()
            ]
            if len(matches) != 1:
                print('PREVIOUS_REPORT_NOT_FOUND')
                return
            if matches[0].file_size > 15_000_000:
                raise ValueError('report_too_large')
            report = json.loads(archive.read(matches[0]))
        if report.get('version') != 'alpha-1.3-directional-research-alerts':
            print('INVALID_BASELINE_VERSION')
            return
        if not isinstance(report.get('assets'), dict):
            raise ValueError('invalid_baseline_assets')

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False), encoding='utf-8')
        print('PREVIOUS_BASELINE_OK')
    except urllib.error.HTTPError as error:
        print(f'BASELINE_RETRIEVAL_FAILED stage={stage} HTTP_{error.code}')
        if error.code in (401, 403):
            print('BASELINE_AUTH_CHECK: verify actions:read and GITHUB_TOKEN access')
    except Exception as error:
        print(f'BASELINE_RETRIEVAL_FAILED stage={stage} {type(error).__name__}: {str(error)[:140]}')


if __name__ == '__main__':
    main()
