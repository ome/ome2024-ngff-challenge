from __future__ import annotations

import pytest

from ome2024_ngff_challenge import dispatch

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
        dispatch(
            [
                "resave",
                str(tmp_path / "in.zarr"),
                str(tmp_path / "out.zarr"),
                "--output-chunks=xxx",
            ]
        )


def test_conflicting_args(tmp_path):
    with pytest.raises(SystemExit):
        dispatch(
            [
                "resave",
                str(tmp_path / "in.zarr"),
                str(tmp_path / "out.zarr"),
                "--output-chunks=xxx",
                "--output-read-details=xxx",
            ]
        )


#
# RO-Crate testing
#


def test_rocrate_name(tmp_path):
    assert (
        dispatch(
            [
                "resave",
                "--rocrate-skip",
                "data/2d.zarr",
                str(tmp_path / "out.zarr"),
            ]
        )
        == 1
    )
    rocrate = tmp_path / "out.zarr" / "ro-crate-metadata.json"
    assert not rocrate.is_file(), all_files(tmp_path)


def test_rocrate_set_name(tmp_path):
    assert (
        dispatch(
            [
                "resave",
                "--rocrate-name=XXX",
                "data/2d.zarr",
                str(tmp_path / "out.zarr"),
            ]
        )
        == 1
    )
    rocrate = tmp_path / "out.zarr" / "ro-crate-metadata.json"
    assert rocrate.is_file(), all_files(tmp_path)
    assert "XXX" in rocrate.read_text()


def test_rocrate_full_example(tmp_path):
    organism = "NCBI:txid7227"
    modality = "obo:FBbi_00000243"
    assert (
        dispatch(
            [
                "resave",
                "--rocrate-name=test name",
                "--rocrate-description=this should be a full description",
                f"--rocrate-organism={organism}",
                f"--rocrate-modality={modality}",
                "data/2d.zarr",
                str(tmp_path / "out.zarr"),
            ]
        )
        == 1
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
    dispatch(
        [
            "resave",
            *IDR_BUCKET,
            IDR_PLATE,
            str(tmp_path / "out.zarr"),
            "--output-script",
        ]
    )


def test_remote_simple_with_download(tmp_path):
    # The labels for `6001240.zarr` have chunks like [1,59,69,136] which is
    # not compatible with default shard (whole image, [1,236,275,271]),
    # so we need to specify both:
    dispatch(
        [
            "resave",
            *IDR_BUCKET,
            IDR_3D,
            str(tmp_path / "out.zarr"),
            "--output-shards=1,10,512,512",
            "--output-chunks=1,1,256,256",
        ]
    )


#
# Local testing using files under data/
#


def check_bf2raw(tmp_path, input, expected, args):
    assert (input, expected, args) >= ("", 0, [])
    xml = tmp_path / "out.zarr" / "OME" / "METADATA.ome.xml"
    assert xml.is_file(), str("\n".join([str(x) for x in tmp_path.rglob("*")]))


@pytest.mark.parametrize(
    ("input", "expected", "args", "func"),
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
        dispatch(
            [
                "resave",
                *args,
                f"data/{input}.zarr",
                str(tmp_path / "out.zarr"),
            ]
        )
        == expected
    )
    if func:
        func(tmp_path, input, expected, args)
