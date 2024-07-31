from __future__ import annotations

import pytest

from ome2024_ngff_challenge import resave


def test_bad_chunks(tmp_path):
    with pytest.raises(SystemExit):
        resave.cli(
            [
                str(tmp_path / "in.zarr"),
                str(tmp_path / "out.zarr"),
                "--output-chunks=xxx",
            ]
        )
