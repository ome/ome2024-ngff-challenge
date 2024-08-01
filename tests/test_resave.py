from __future__ import annotations

import pytest

from ome2024_ngff_challenge import resave

#
# Helpers
#


# See: https://stackoverflow.com/questions/62044541/change-pytest-working-directory-to-test-case-directory
@pytest.fixture(autouse=True)
def _change_test_dir(request, monkeypatch):
    """
    Run all subsequent tests from within the tests directory
    """
    monkeypatch.chdir(request.fspath.dirname)


#
# Argument handling tests
#


def test_bad_chunks(tmp_path):
    with pytest.raises(SystemExit):
        resave.cli(
            [
                str(tmp_path / "in.zarr"),
                str(tmp_path / "out.zarr"),
                "--output-chunks=xxx",
            ]
        )


def test_conflicting_args(tmp_path):
    with pytest.raises(SystemExit):
        resave.cli(
            [
                str(tmp_path / "in.zarr"),
                str(tmp_path / "out.zarr"),
                "--output-chunks=xxx",
                "--output-read-details=xxx",
            ]
        )


#
# Remote testing
#

IDR_BUCKET = (
    "--input-bucket=idr",
    "--input-endpoint=https://uk1s3.embassy.ebi.ac.uk",
    "--input-anon",
)

IDR_PLATE = "zarr/v0.4/idr0001A/2551.zarr"
IDR_PLATE = "zarr/v0.4/idr0072B/9512.zarr"

IDR_3D = "zarr/v0.4/idr0062A/6001240.zarr"


@pytest.mark.skip(reason="too slow")
def test_remote_hcs_with_scripts(tmp_path):
    resave.cli(
        [
            *IDR_BUCKET,
            IDR_PLATE,
            str(tmp_path / "out.zarr"),
            "--output-script",
        ]
    )


def test_remote_simple_with_download(tmp_path):
    resave.cli(
        [
            *IDR_BUCKET,
            IDR_3D,
            str(tmp_path / "out.zarr"),
        ]
    )


#
# Local testing
#


def test_local_2d(tmp_path):
    assert (
        resave.cli(
            [
                "data/2d.zarr",
                str(tmp_path / "out.zarr"),
            ]
        )
        == 1
    )


def test_local_bf2raw(tmp_path):
    assert (
        resave.cli(
            [
                "data/bf2raw.zarr",
                str(tmp_path / "out.zarr"),
            ]
        )
        == 2
    )
    xml = tmp_path / "out.zarr" / "OME" / "METADATA.ome.xml"
    assert xml.is_file(), str("\n".join([str(x) for x in tmp_path.rglob("*")]))


def test_local_hcs(tmp_path):
    assert (
        resave.cli(
            [
                "data/hcs.zarr",
                str(tmp_path / "out.zarr"),
            ]
        )
        == 8
    )
