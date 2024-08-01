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


def all_files(path):
    """
    Return a string of all the files in a directory. Useful for asserts:

    assert something, all_files(path)
    """
    return str("\n".join([str(x) for x in path.rglob("*")]))


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
# Local testing using files under data/
#


@pytest.mark.parametrize(
    "input,expected,args,func",
    [
        pytest.param("2d", 1, [], None),
        pytest.param("2d", 1, ["--output-script"], None),
        pytest.param("bf2raw", 2, [], check_bf2raw),
        pytest.param("bf2raw", 2, ["--output-script"], check_bf2raw),
        pytest.param("hcs", 8, [], None),
        pytest.param("hcs", 8, ["--output-script"], None),
    ],
)
def test_local_tests(tmp_path, input, expected, args, func):
    assert (
        resave.cli(
            [
                *args,
                f"data/{input}.zarr",
                str(tmp_path / "out.zarr"),
            ]
        )
        == expected
    )
    func(tmp_path, input, expected, args)


def check_bf2raw(tmp_path, input, expected, args):
    xml = tmp_path / "out.zarr" / "OME" / "METADATA.ome.xml"
    assert xml.is_file(), str("\n".join([str(x) for x in tmp_path.rglob("*")]))
