# pyproject.toml

The `pyproject.toml` is the main configuration file for this project. Poetry
defines the package metadata and dependencies there, and `poetry.lock` records
the exact resolved versions.

Install the project and its development dependencies with:

    poetry install --with dev

Run commands in Poetry's environment, for example:

    poetry run pytest
    poetry run pylint src/msftoolbox
