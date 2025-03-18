from setuptools import setup, find_packages

setup(
    name="pod-cleaner",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "kubernetes>=29.0.0",
        "PyYAML>=6.0.1",
        "python-logging-loki>=0.3.1",
        "rich>=13.7.0",
        "typer>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "pod-cleaner=pod_cleaner.cli:main",
        ],
    },
) 