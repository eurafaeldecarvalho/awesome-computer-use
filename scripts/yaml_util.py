"""YAML load and dump that keep dates as strings."""

from pathlib import Path

import yaml


class NoDateLoader(yaml.SafeLoader):
    pass


# PyYAML otherwise turns 2026-10-29 into a datetime, which then rewrites the file.
for ch, resolvers in list(NoDateLoader.yaml_implicit_resolvers.items()):
    NoDateLoader.yaml_implicit_resolvers[ch] = [
        item for item in resolvers if item[0] != "tag:yaml.org,2002:timestamp"
    ]


def load_yaml(path):
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.load(handle, Loader=NoDateLoader)


def dump_yaml(data, path):
    text = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        width=100,
        default_flow_style=False,
    )
    Path(path).write_text(text, encoding="utf-8")
