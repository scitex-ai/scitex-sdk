"""CPU workflows respect organization admission and host quarantine labels."""
from pathlib import Path

import pytest
import yaml


WORKFLOWS = Path(__file__).resolve().parents[1] / '.github' / 'workflows'
ADMISSION = 'scitex-ai/.github/.github/workflows/runner-admission.yml@d7d96c34d68cdfbb5503a933591f7748b5aa30ee'
DESTINATION = " ".join('''${{ needs.runner-admission.outputs.native_authorized == 'true'
    && fromJSON('{"group":"Organization","labels":["self-hosted","Linux","X64","scitex-org-cpu"]}')
    || fromJSON('["ubuntu-latest"]') }}'''.split())
CPU_JOBS = [
    ('python-package.yml', 'package'),
    ('frontend.yml', 'typecheck'),
    ('frontend.yml', 'lint'),
    ('frontend.yml', 'vitest'),
    ('frontend.yml', 'header-browser'),
    ('app-ui-retirement.yml', 'published-consumer-graphs'),
    ('pypi-publish-and-github-release-on-tag.yml', 'test'),
    ('pypi-publish-and-github-release-on-tag.yml', 'build'),
    ('pypi-publish-and-github-release-on-tag.yml', 'release'),
]


@pytest.mark.parametrize('filename,job_name', CPU_JOBS)
def test_cpu_jobs_require_admission_and_the_quarantine_aware_pool(filename, job_name):
    # Arrange
    jobs = yaml.safe_load((WORKFLOWS / filename).read_text())['jobs']
    job = jobs[job_name]
    # Act
    contract = (jobs.get('runner-admission'), job.get('needs'),
                ' '.join(str(job['runs-on']).split()))
    # Assert
    assert (contract[0], 'runner-admission' in contract[1], contract[2]) == (
        {'uses': ADMISSION, 'permissions': {}, 'with': {
            'runs_on': '["self-hosted","Linux","X64","scitex-org-cpu"]'}},
        True, DESTINATION)


def test_publication_dependencies_are_preserved():
    # Arrange
    path = WORKFLOWS / 'pypi-publish-and-github-release-on-tag.yml'
    # Act
    jobs = yaml.safe_load(path.read_text())['jobs']
    # Assert
    assert (jobs['build']['needs'], jobs['release']['needs'], jobs['publish']['needs']) == (
        ['test', 'frontend', 'runner-admission'],
        ['build', 'publish', 'runner-admission'], 'build')
