"""
Unit tests for the isolation seam (runtime selection).

These tests verify detect_runtime() resolves the requested OCI runtime against
what Docker reports, falling back to runc safely. They mock subprocess.run so no
real Docker daemon is needed.

Style mirrors tests/test_cli.py (pytest-describe describe_/it_ blocks). The
existing suite mocks via unittest.mock rather than the pytest-mock `mocker`
fixture, which is not in the dev dependency set; we follow that pattern here.
"""

import json
from unittest import mock

from lamp_the_djinn.cli import detect_runtime


def _docker_info_result(runtimes: dict, returncode: int = 0) -> mock.Mock:
    """Build a fake `docker info --format '{{json .Runtimes}}'` result."""
    result = mock.Mock()
    result.returncode = returncode
    result.stdout = json.dumps(runtimes)
    return result


def describe_detect_runtime():
    """Unit tests for detect_runtime function."""

    def it_auto_resolves_to_runc_even_when_runsc_present():
        """auto picks the lightest sane runtime (runc) and never auto-escalates
        to gVisor -- runsc breaks the cage's ipset egress firewall."""
        result = _docker_info_result({"runc": {}, "runsc": {}})
        with mock.patch("subprocess.run", return_value=result):
            assert detect_runtime("auto") == "runc"

    def it_auto_does_not_query_docker():
        """The default path short-circuits to runc without a docker info call."""
        with mock.patch("subprocess.run", side_effect=AssertionError("queried docker")):
            assert detect_runtime("auto") == "runc"
            assert detect_runtime("runc") == "runc"

    def it_returns_concrete_runtime_when_present():
        """A concrete request is honored when Docker has that runtime."""
        result = _docker_info_result({"runc": {}, "runsc": {}})
        with mock.patch("subprocess.run", return_value=result):
            assert detect_runtime("runsc") == "runsc"

    def it_warns_and_falls_back_when_concrete_runtime_missing(capsys):
        """A concrete request for a missing runtime warns and falls back to runc."""
        result = _docker_info_result({"runc": {}})
        with mock.patch("subprocess.run", return_value=result):
            assert detect_runtime("runsc") == "runc"
        captured = capsys.readouterr()
        assert "runsc" in captured.err
        assert "runc" in captured.err

    def it_resolves_kata_runtime_when_present():
        """kata-runtime is honored when Docker registers it."""
        result = _docker_info_result({"runc": {}, "kata-runtime": {}})
        with mock.patch("subprocess.run", return_value=result):
            assert detect_runtime("kata-runtime") == "kata-runtime"

    def it_returns_runc_when_docker_info_fails():
        """A non-zero docker exit yields runc rather than raising."""
        result = _docker_info_result({}, returncode=1)
        with mock.patch("subprocess.run", return_value=result):
            assert detect_runtime("auto") == "runc"

    def it_returns_runc_when_docker_missing():
        """A missing docker binary (OSError) yields runc."""
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("docker")):
            assert detect_runtime("auto") == "runc"

    def it_returns_runc_on_malformed_json():
        """Unparseable docker output yields runc rather than raising."""
        result = mock.Mock()
        result.returncode = 0
        result.stdout = "not-json"
        with mock.patch("subprocess.run", return_value=result):
            assert detect_runtime("auto") == "runc"
