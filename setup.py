"""Setup script for psycgod-sage.

Adds a post-install hook for GitHub OAuth authentication.
Runs only during source installs (pip builds from sdist).
For wheel installs, first `sage` CLI invocation handles setup.
"""

from setuptools import setup
from setuptools.command.install import install


class PostInstallCommand(install):
    """Custom install command that runs GitHub OAuth after pip install."""

    def run(self):
        install.run(self)
        self._run_post_install()

    def _run_post_install(self):
        try:
            from sage._post_install import run_post_install

            run_post_install()
        except Exception:
            pass


setup(cmdclass={"install": PostInstallCommand})
