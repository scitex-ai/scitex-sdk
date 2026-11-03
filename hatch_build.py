"""Bootstrap SDK's own shared inert producer during a normal isolated build."""

from pathlib import Path
import sys

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        self._api_metadata = None
        if self.target_name != "wheel":
            return
        source = Path(self.root).resolve() / "src"
        previous = list(sys.path)
        try:
            sys.path.insert(0, str(source))
            from scitex_sdk.app import api_build

            if not Path(api_build.__file__).resolve().is_relative_to(source):
                raise RuntimeError("SDK self-build must use its own metadata producer")
            self._api_metadata = api_build.prepare_hatch_api_metadata(self, build_data)
        finally:
            sys.path[:] = previous

    def finalize(self, version, build_data, artifact_path):
        if self._api_metadata is not None:
            self._api_metadata.cleanup()
