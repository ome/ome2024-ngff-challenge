from __future__ import annotations

import importlib.metadata

import ome2024_ngff_challenge as m


def test_version():
    assert importlib.metadata.version("ome2024_ngff_challenge") == m.__version__
