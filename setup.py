import os
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.install import install

from src.scripts.generate_driver_models import main as generate_driver_models
from src.scripts.generate_overloads import main as generate_overloads


class CustomInstall(install):
    def run(self):
        schema_dir = (
            Path(__file__).parent
            / "src"
            / "videoipath_automation_tool"
            / "apps"
            / "inventory"
            / "model"
            / "driver_schema"
        )

        if not schema_dir.exists():
            raise RuntimeError(f"Schema directory not found: {schema_dir}")

        available_versions = sorted(p.stem for p in schema_dir.glob("*.json"))
        if not available_versions:
            raise RuntimeError(f"No schema versions found in {schema_dir}")

        videoipath_api_version = os.getenv("VIDEOIPATH_API_VERSION")

        if videoipath_api_version:
            json_file = schema_dir / f"{videoipath_api_version}.json"
            if not json_file.exists():
                raise ValueError(
                    f"Unsupported VIDEOIPATH_API_VERSION: '{videoipath_api_version}'. "
                    f"Available versions: {available_versions}"
                )
            print(f"[INSTALL] Using specified API version: {videoipath_api_version}")
            generate_driver_models(schema_file=json_file.absolute().as_posix())
        else:
            fallback_version = available_versions[-1]
            print(f"[INSTALL] VIDEOIPATH_API_VERSION not set. Using latest available version: {fallback_version}")
            generate_driver_models()

        generate_overloads()
        print("[INSTALL] Code generation completed successfully.")
        super().run()


setup(
    name="videoipath-automation-tool",
    version="0.2.5",
    description="A Python package for automating VideoIPath configuration workflows.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Paul Winterstein",
    author_email="paul.winterstein@swr.de",
    maintainer="Josia Hildebrandt",
    maintainer_email="manuel_josia.hildebrandt@swr.de",
    url="https://github.com/SWR-MoIP/VideoIPath-Automation-Tool",
    project_urls={
        "Homepage": "https://github.com/SWR-MoIP/VideoIPath-Automation-Tool",
        "Repository": "https://github.com/SWR-MoIP/VideoIPath-Automation-Tool",
        "Issues": "https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/issues",
        "Documentation": "https://github.com/SWR-MoIP/VideoIPath-Automation-Tool#documentation",
    },
    license="AGPL-3.0-only",
    license_files=["LICENSE"],
    python_requires=">=3.11",
    keywords=["videoipath", "automation", "nevion", "media-over-ip", "st2110", "orchestration"],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "requests>=2.31.0,<3.0.0",
        "pydantic>=2.6.4,<3.0.0",
        "pydantic-extra-types>=2.6.0,<3.0.0",
        "pydantic-settings>=2.2.1,<3.0.0",
        "urllib3>=2.2.3,<3.0.0",
        "deepdiff>=8.1.1,<9.0.0",
    ],
    cmdclass={
        "install": CustomInstall,
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
)
