from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

from ome2024_ngff_challenge import dispatch

from .test_utils import mock_aio_aws

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
                "--cc-by",
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
                "--cc-by",
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
                "--cc-by",
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
                "--cc-by",
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
                "--cc-by",
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
# Remote read testing
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
            "--cc-by",
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
            "--cc-by",
            *IDR_BUCKET,
            IDR_3D,
            str(tmp_path / "out.zarr"),
            "--output-shards=1,10,512,512",
            "--output-chunks=1,1,256,256",
        ]
    )


#
# Remote write testing
#

# Use dummy AWS credentials
AWS_REGION = "us-west-2"
AWS_ACCESS_KEY_ID = "dummy_AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "dummy_AWS_SECRET_ACCESS_KEY"


@pytest.fixture()
def aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", AWS_ACCESS_KEY_ID)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", AWS_SECRET_ACCESS_KEY)
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")


@pytest.fixture(scope="session")
def aws_region():
    return AWS_REGION


AWS_BUCKET = (
    "--output-bucket=test-bucket",
    "--output-region=us-west-2",
)


OVERWRITE = ["--output-overwrite"]


@pytest.mark.parametrize(
    ("first_flags", "second_flags", "expected_pass"),
    [
        pytest.param([], [], False, id="simple-twice-fail"),
        pytest.param([], OVERWRITE, True, id="proper-usage-pass"),
        pytest.param(OVERWRITE, OVERWRITE, True, id="double-safe-pass"),
    ],
)
@mock_aws
@pytest.mark.filterwarnings("ignore:datetime.datetime.utcnow")
def test_remote_two_writes(first_flags, second_flags, expected_pass, monkeypatch):
    with mock_aio_aws(monkeypatch):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")

        # First
        converted = dispatch(
            [
                "resave",
                "--cc-by",
                "--output-script",  # By pass tensorstore
                "data/2d.zarr",
                "path/in/bucket/out.zarr",
                *AWS_BUCKET,
                *first_flags,
            ]
        )
        assert converted

        # Second
        cmd = [
            "resave",
            "--cc-by",
            "data/2d.zarr",
            "path/in/bucket/out.zarr",
            *AWS_BUCKET,
            *second_flags,
        ]
        if expected_pass:
            assert dispatch(cmd)
        else:
            with pytest.raises(Exception) as e_info:
                dispatch(cmd)


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
        pytest.param("2d", 1, ["--conversion-notes=INFO"], None),
        pytest.param("bf2raw", 2, [], check_bf2raw),
        pytest.param("bf2raw", 2, ["--output-script"], check_bf2raw),
        pytest.param("bf2raw", 2, ["--conversion-notes=INFO"], check_bf2raw),
        pytest.param("hcs", 8, [], None),
        pytest.param("hcs", 8, ["--output-script"], None),
        pytest.param("hcs", 8, ["--conversion-notes=INFO"], None),
    ],
)
def test_local_tests(tmp_path, input, expected, args, func):
    converted = dispatch(
        [
            "resave",
            "--cc-by",
            *args,
            f"data/{input}.zarr",
            str(tmp_path / "out.zarr"),
        ]
    )
    assert converted == expected
    if func:
        func(tmp_path, input, expected, args)
