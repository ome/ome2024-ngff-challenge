#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import logging
import math
import multiprocessing
import os
import random
import time
import warnings
from pathlib import Path

import tensorstore as ts
import tqdm

from .utils import (
    Batched,
    Config,
    SafeEncoder,
    TSMetrics,
    add_creator,
    chunk_iter,
    configure_logging,
    csv_int,
    guess_shards,
    strip_version,
)
from .zarr_crate.rembi_extension import Biosample, ImageAcquistion, Specimen
from .zarr_crate.zarr_extension import ZarrCrate

NGFF_VERSION = "0.5"
LOGGER = logging.getLogger(__file__)


def convert_array(
    input_config: Config,
    output_config: Config,
    dimension_names: list,
    chunks: list,
    shards: list,
    threads: int,
):
    read = input_config.ts_read()

    if shards:
        chunk_grid = {
            "name": "regular",
            "configuration": {"chunk_shape": shards},
        }  # write size

        sharding_codec = {
            "name": "sharding_indexed",
            "configuration": {
                "chunk_shape": chunks,  # read size
                "codecs": [
                    {"name": "bytes", "configuration": {"endian": "little"}},
                    {"name": "blosc", "configuration": {"cname": "zstd", "clevel": 5}},
                ],
                "index_codecs": [
                    {"name": "bytes", "configuration": {"endian": "little"}},
                    {"name": "crc32c"},
                ],
                "index_location": "end",
            },
        }
        codecs = [sharding_codec]
    else:
        # Alternative without sharding...
        chunk_grid = {"name": "regular", "configuration": {"chunk_shape": chunks}}
        codecs = [
            {"name": "bytes", "configuration": {"endian": "little"}},
            {"name": "blosc", "configuration": {"cname": "zstd", "clevel": 5}},
        ]

    base_config = output_config.ts_config.copy()
    base_config["metadata"] = {
        "shape": read.shape,
        "chunk_grid": chunk_grid,
        "chunk_key_encoding": {
            "name": "default"
        },  # "configuration": {"separator": "/"}},
        "codecs": codecs,
        "data_type": read.dtype,
        "dimension_names": dimension_names,
    }

    write_config = base_config.copy()
    write_config["create"] = True
    write_config["delete_existing"] = output_config.overwrite

    LOGGER.log(
        5,
        f"""input_config:
{json.dumps(input_config.ts_config, indent=4)}
    """,
    )
    LOGGER.log(
        5,
        f"""write_config:
{json.dumps(write_config, indent=4, cls=SafeEncoder)}
    """,
    )

    verify_config = base_config.copy()

    write = ts.open(write_config).result()

    before = TSMetrics(input_config.ts_config, write_config)

    # read & write a chunk (or shard) at a time:
    blocks = shards if shards is not None else chunks
    for idx, batch in enumerate(Batched(chunk_iter(read.shape, blocks), threads)):
        start = time.time()
        with ts.Transaction() as txn:
            LOGGER.log(5, f"batch {idx:03d}: scheduling transaction size={len(batch)}")
            for slice_tuple in batch:
                write.with_transaction(txn)[slice_tuple] = read[slice_tuple]
                LOGGER.log(
                    5, f"batch {idx:03d}: {slice_tuple} scheduled in transaction"
                )
            LOGGER.log(5, f"batch {idx:03d}: waiting on transaction size={len(batch)}")
        stop = time.time()
        elapsed = stop - start
        avg = float(elapsed) / len(batch)
        LOGGER.debug(
            f"batch {idx:03d}: completed transaction size={len(batch)} in {stop-start:0.2f}s (avg={avg:0.2f})"
        )

    after = TSMetrics(input_config.ts_config, write_config, before)

    stats = {
        "input": input_config.s3_endpoint(),
        "output": output_config.s3_endpoint(),
        "start": before.time,
        "stop": after.time,
        "read": after.read(),
        "written": after.written(),
        "elapsed": after.elapsed(),
        "threads": threads,
        "cpu_count": multiprocessing.cpu_count(),
    }
    if hasattr(os, "sched_getaffinity"):
        stats["sched_affinity"] = len(os.sched_getaffinity(0))

    LOGGER.info(f"""Re-encode (tensorstore) {input_config} to {output_config}
        read: {stats["read"]}
        write: {stats["written"]}
        time: {stats["elapsed"]}
    """)

    ## TODO: there is likely an easier way of doing this
    metadata = write.kvstore["zarr.json"]
    metadata = json.loads(metadata)
    if "attributes" in metadata:
        attributes = metadata["attributes"]
    else:
        attributes = {}
        metadata["attributes"] = attributes
    attributes["_ome2024_ngff_challenge_stats"] = stats
    metadata = json.dumps(metadata)
    write.kvstore["zarr.json"] = metadata

    ## TODO: This is not working with v3 branch nor with released version
    ## zr_array = zarr.open_array(store=output_config.zr_store, mode="a", zarr_format=3)
    ## zr_array.update_attributes({
    ##     "_ome2024_ngff_challenge_stats": stats,
    ## })

    verify = ts.open(verify_config).result()
    LOGGER.info(f"Verifying <{output_config}>\t{read.shape}\t")
    for x in range(10):
        r = tuple([random.randint(0, y - 1) for y in read.shape])
        before = read[r].read().result()
        after = verify[r].read().result()
        assert before == after
        LOGGER.debug(f"{x}")
    LOGGER.info("ok")


def convert_image(
    input_config: Config,
    output_config: Config,
    output_chunks: list[int] | None,
    output_shards: list[int] | None,
    output_read_details: str | None,
    output_write_details: bool,
    output_script: bool,
    threads: int,
    notes: str | None,
):
    dimension_names = None
    # top-level version...
    ome_attrs = {"version": NGFF_VERSION}
    for key, value in input_config.zr_attrs.items():
        # ...replaces all other versions - remove
        strip_version(value)
        if key == "multiscales":
            dimension_names = [axis["name"] for axis in value[0]["axes"]]
            strip_version(value[0])
        ome_attrs[key] = value

    # Add _creator - NB: this will overwrite existing _creator info
    add_creator(ome_attrs, notes)

    if output_config.zr_group is not None:  # otherwise dry-run
        # dev2: everything is under 'ome' key
        output_config.zr_attrs["ome"] = ome_attrs

    if output_read_details:
        with output_read_details.open() as o:
            details = json.load(o)
    else:
        details = {}
        if output_config.path.exists() and output_config.path.is_file():
            # Someone has already written details. Reload them
            with output_config.path.open() as o:
                details = json.load(o)

    # convert arrays
    multiscales = input_config.zr_attrs.get("multiscales")
    for ds in multiscales[0]["datasets"]:
        ds_path = ds["path"]
        ds_array = input_config.zr_group[ds_path]
        ds_shape = ds_array.shape
        ds_chunks = ds_array.chunks
        ds_shards = guess_shards(ds_shape, ds_chunks)
        ds_input_config = input_config.sub_config(ds_path, False)
        ds_output_config = output_config.sub_config(ds_path, False)

        if output_write_details:
            details.update(
                {
                    ds_input_config.fs_string(): {
                        "shape": ds_shape,
                        "chunks": ds_chunks,
                        "shards": ds_shards,
                    }
                }
            )
            # Note: not S3 compatible and doesn't use subpath!
            with output_config.path.open(mode="w") as o:
                json.dump(details, o)
        else:
            if output_read_details:
                # read row by row and overwrite
                key = ds_input_config.fs_string()
                ds_chunks = details[key]["chunks"]
                ds_shards = details[key]["shards"]
            else:
                if output_chunks:
                    ds_chunks = output_chunks
                if output_shards:
                    ds_shards = output_shards
                elif not output_script and math.prod(ds_shards) > 100_000_000:
                    # if we're going to convert, and we guessed the shards,
                    # let's validate the guess...
                    raise ValueError(
                        f"no shard guess: shape={ds_shape}, chunks={ds_chunks}"
                    )

            if output_script:
                chunk_txt = ",".join(map(str, ds_chunks))
                shard_txt = ",".join(map(str, ds_shards))
                dimsn_txt = ",".join(map(str, dimension_names))
                output_config.zr_write_text(
                    Path(ds_path) / "convert.sh",
                    f"zarrs_reencode --chunk-shape {chunk_txt} --shard-shape {shard_txt} --dimension-names {dimsn_txt} --validate {ds_input_config} {ds_output_config}\n",
                )
            else:
                convert_array(
                    ds_input_config,
                    ds_output_config,
                    dimension_names,
                    ds_chunks,
                    ds_shards,
                    threads,
                )

    # check for labels...
    try:
        labels_config = input_config.sub_config("labels")
    except ValueError:
        # File "../site-packages/zarr/abc/store.py", line 29, in _check_writable
        # raise ValueError("store mode does not support writing")
        LOGGER.debug("No labels group found")
    else:
        labels_attrs = labels_config.zr_attrs.get("labels", [])
        LOGGER.debug("labels_attrs: %s", labels_attrs)

        dry_run = output_config.zr_group is None

        labels_output_config = output_config.sub_config(
            "labels", create_or_open_group=(not dry_run)
        )
        if not dry_run:
            labels_output_config.zr_attrs["ome"] = dict(labels_config.zr_attrs)

        for label_path in labels_attrs:
            label_config = labels_config.sub_config(label_path)
            label_path_obj = Path("labels") / label_path

            label_output_config = output_config.sub_config(
                label_path_obj,
                create_or_open_group=(not dry_run),
            )

            convert_image(
                label_config,
                label_output_config,
                output_chunks,
                output_shards,
                output_read_details,
                output_write_details,
                output_script,
                threads,
                notes,
            )


class ROCrateWriter:
    def __init__(
        self,
        name: str | None = None,
        description: str | None = None,
        data_license: str | None = None,
        organism: str | None = None,
        modality: str | None = None,
    ):
        self.name = name
        self.description = description
        self.data_license = data_license

        # Optional parameters that can be ignored if `process()` is overwritten.
        self.organism = organism
        self.modality = modality

        # Created by generate()
        self.crate = None
        self.zarr_root = None

    def properties(self) -> dict:
        """
        Return a dictionary containing the base properties
        like name, description, and license
        """

        values = {}
        if self.name:
            values["name"] = self.name
        if self.description:
            values["description"] = self.description

        if self.data_license:
            values["license"] = self.data_license
        else:
            warnings.warn("No license specified!", stacklevel=1)

        return values

    def generate(self, dataset="./") -> None:
        """
        Create a ZarrCrate object for the given dataset and
        add the default properties.
        """
        self.crate = ZarrCrate()
        self.zarr_root = self.crate.add_dataset(dataset, properties=self.properties())

    def process(self) -> None:
        """
        Post-process the generated ZarrCrate by adding any appropriate metadata.
        By default, if organism and modality were set on construction add those.
        """
        specimen = None
        if self.organism:
            biosample = self.crate.add(
                Biosample(
                    self.crate,
                    properties={"organism_classification": {"@id": self.organism}},
                )
            )
            specimen = self.crate.add(Specimen(self.crate, biosample))

        if specimen and self.modality:
            image_acquisition = self.crate.add(
                ImageAcquistion(
                    self.crate, specimen, properties={"fbbi_id": {"@id": self.modality}}
                )
            )
            self.zarr_root["resultOf"] = image_acquisition

    def write(
        self,
        config: Config,
        filename: str | Path = "ro-crate-metadata.json",
        indent: int = 2,
    ) -> None:
        """
        Use the config location to write a string representation of the metadata to a file.
        """
        self.generate()
        self.process()
        metadata_dict = self.crate.metadata.generate()
        text = json.dumps(metadata_dict, indent=indent)
        config.zr_write_text(filename, text)


def main(ns: argparse.Namespace) -> None:
    """
    If no images are converted, raises SystemExit.
    """

    converted: int = 0

    parse(ns)
    rocrate: ROCrateWriter = ns.rocrate

    input_config = Config(ns, "input", "r")
    output_config = Config(ns, "output", "w")
    output_config.check_or_delete_path()

    input_config.open_group()

    if not ns.output_write_details:
        output_config.create_group()
        if rocrate:
            rocrate.write(output_config)

    # image...
    if input_config.zr_attrs.get("multiscales"):
        convert_image(
            input_config,
            output_config,
            ns.output_chunks,
            ns.output_shards,
            ns.output_read_details,
            ns.output_write_details,
            ns.output_script,
            ns.output_threads,
            ns.conversion_notes,
        )
        converted += 1

    # plate...
    elif plate_attrs := input_config.zr_attrs.get("plate"):
        ome_attrs = {"version": NGFF_VERSION}
        for key, value in input_config.zr_attrs.items():
            # ...replaces all other versions - remove
            strip_version(value)
            ome_attrs[key] = value

        add_creator(ome_attrs, ns.conversion_notes)

        if output_config.zr_group is not None:  # otherwise dry run
            # dev2: everything is under 'ome' key
            output_config.zr_attrs["ome"] = ome_attrs

        wells = plate_attrs.get("wells")

        for well in tqdm.tqdm(
            wells, position=0, desc="i", leave=False, colour="green", ncols=80
        ):
            well_path = well["path"]

            well_input_config = input_config.sub_config(well_path)

            if output_config.zr_group is not None:  # otherwise dry-run
                well_output_config = output_config.sub_config(well_path)
                well_attrs = {}
                for key, value in well_input_config.zr_attrs.items():
                    strip_version(value)
                    well_attrs[key] = value
                    well_attrs["version"] = "0.5"
                well_output_config.zr_attrs["ome"] = well_attrs

            images = well_attrs["well"]["images"]
            for img in tqdm.tqdm(
                images, position=1, desc="j", leave=False, colour="red", ncols=80
            ):
                img_path = Path(well_path) / img["path"]
                img_input_config = input_config.sub_config(img_path)

                if output_config.zr_group is not None:  # otherwise dry-run
                    img_output_config = output_config.sub_config(str(img_path))
                else:
                    img_output_config = None

                convert_image(
                    img_input_config,
                    img_output_config,
                    ns.output_chunks,
                    ns.output_shards,
                    ns.output_read_details,
                    ns.output_write_details,
                    ns.output_script,
                    ns.output_threads,
                    ns.conversion_notes,
                )
                converted += 1
    # Note: plates can *also* contain this metadata
    elif layout := input_config.zr_attrs.get("bioformats2raw.layout"):
        assert layout == 3
        ome_attrs = {"version": NGFF_VERSION}
        for key, value in input_config.zr_attrs.items():
            # ...replaces all other versions - remove
            strip_version(value)
            ome_attrs[key] = value

        add_creator(ome_attrs, ns.conversion_notes)

        if output_config.zr_group is not None:  # otherwise dry run
            # dev2: everything is under 'ome' key
            output_config.zr_attrs["ome"] = ome_attrs

        ome_config = input_config.sub_config("OME")
        series = ome_config.zr_attrs.get("series", [])
        assert series  # TODO: support implicit case where OME-XML must be read

        filename = "OME/METADATA.ome.xml"
        ome_xml = input_config.zr_read_text(filename)
        if ome_xml is not None:
            output_config.zr_write_text(filename, ome_xml.text)

        for img_path in tqdm.tqdm(
            series, position=0, desc="i", leave=False, colour="green", ncols=80
        ):
            img_input_config = input_config.sub_config(str(img_path))

            if output_config.zr_group is not None:  # otherwise dry-run
                img_output_config = output_config.sub_config(str(img_path))
            else:
                img_output_config = None

            convert_image(
                img_input_config,
                img_output_config,
                ns.output_chunks,
                ns.output_shards,
                ns.output_read_details,
                ns.output_write_details,
                ns.output_script,
                ns.output_threads,
                ns.conversion_notes,
            )
            converted += 1
    else:
        LOGGER.warning(f"no convertible metadata: {input_config.zr_attrs.keys()}")

    if converted == 0:
        raise SystemExit(1)


def cli(subparsers: argparse._SubParsersAction):
    """
    Parses the arguments contained in `args` and passes
    them to `main`. If no images are converted, raises
    SystemExit. Otherwise, return the number of images.
    """
    cmd = "ome2024-ngff-challenge resave"
    desc = f"""


The `resave` subcommand will convert an existing Zarr v2 dataset into a Zarr v3 dataset according
to the challenge specification. Additionally, a number of options are available for adding metadata



BASIC

    Simplest example:                        {cmd} --cc-by in.zarr out.zarr
    Overwrite existing output:               {cmd} --cc-by in.zarr out.zarr --output-overwrite


METADATA

    There are three levels of metadata that the challenge is looking for:

        - strongly recommended: license
        - recommended: organism and modality
        - optional: name and description

    License: CC-BY (most suggested)          {cmd} in.zarr out.zarr --cc-by
    License: public domain                   {cmd} in.zarr out.zarr --cc0
    License: choose your own                 {cmd} in.zarr out.zarr --rocrate-license=https://creativecommons.org/licenses/by-sa/4.0/

    Organism: Arabidopsis thaliana           {cmd} in.zarr out.zarr --cc0 --rocrate-organism=NCBI:txid3702
    Organism: Drosophila melanogaster        {cmd} in.zarr out.zarr --cc0 --rocrate-organism=NCBI:txid7227
    Organism: Escherichia coli               {cmd} in.zarr out.zarr --cc0 --rocrate-organism=NCBI:txid562
    Organism: Homo sapiens                   {cmd} in.zarr out.zarr --cc0 --rocrate-organism=NCBI:txid9606
    Organism: Mus musculus                   {cmd} in.zarr out.zarr --cc0 --rocrate-organism=NCBI:txid10090
    Organism: Saccharomyces cerevisiae       {cmd} in.zarr out.zarr --cc0 --rocrate-organism=NCBI:txid4932

    Modality: bright-field microscopy        {cmd} in.zarr out.zarr --cc0 --rocrate-modality=obo:FBbi_00000243
    Modality: confocal microscopy            {cmd} in.zarr out.zarr --cc0 --rocrate-modality=obo:FBbi_00000251
    Modality: light-sheet microscopy (SPIM)  {cmd} in.zarr out.zarr --cc0 --rocrate-modality=obo:FBbi_00000369
    Modality: scanning electron microscopy   {cmd} in.zarr out.zarr --cc0 --rocrate-modality=obo:FBbi_00000257
    Modality: two-photon laser scanning      {cmd} in.zarr out.zarr --cc0 --rocrate-modality=obo:FBbi_00000253

    Define a name                            {cmd} --cc-by in.zarr out.zarr --rocrate-name="my experiment"
    Define a description                     {cmd} --cc-by in.zarr out.zarr --rocrate-description="More text here"

    No metadata (INVALID DATASET!)           {cmd} --rocrate-skip in.zarr out.zarr

    For more information see the online resources for each metadata term:
    - https://www.ncbi.nlm.nih.gov/Taxonomy/taxonomyhome.html/
    - https://www.ebi.ac.uk/ols4/ontologies/fbbi


CHUNKS/SHARDS

    With the introduction of sharding, it may be necessary to choose a different chunk
    size for your dataset.

    Set the same value for all resolutions   {cmd} --cc-by in.zarr out.zarr --output-chunks=1,1,1,256,256 --output-shards=1,1,1,2048,2048
    Log the current values for all images    {cmd} --cc-by in.zarr cfg.json --output-write-details
    Read values from an edited config file   {cmd} --cc-by in.zarr out.zarr --output-read-details=cfg.json


REMOTE (S3)

    For both the input and output filesets, a number of arguments are available:

    * bucket (required): setting this activates remote access
    * endpoint (optional): if not using AWS S3, set this to your provider's endpoint
    * region (optional): set the region that you would like to access
    * anon (optional): do not attempt to authenticate with the service

    By default, S3 access will try to make use of your environment variables (e.g. AWS_ACCESS_KEY_ID)
    or your local configuration (~/.aws) which you may need to deactivate.

    Read from IDR's bucket:                  {cmd} --cc-by bucket-path/in.zarr out.zarr \\
                                                   --input-anon \\
                                                   --input-bucket=idr \\
                                                   --input-endpoint=https://uk1s3.embassy.ebi.ac.uk

ADVANCED

    Prepare scripts for conversion.          {cmd} --cc-by in.zarr out.zarr --output-script
    Set number of parallel threads           {cmd} --cc-by in.zarr out.zarr --output-threads=128
    Increase logging                         {cmd} --cc-by in.zarr out.zarr --log=debug
    Increase logging even more               {cmd} --cc-by in.zarr out.zarr --log=trace
    Record details about the conversion      {cmd} --cc-by in.zarr out.zarr --conversion-notes="run on a virtual machine"
    """
    parser = subparsers.add_parser(
        "resave",
        help="convert Zarr v2 dataset to Zarr v3",
        description=desc,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.set_defaults(func=main)
    parser.add_argument("--input-bucket")
    parser.add_argument("--input-endpoint")
    parser.add_argument("--input-anon", action="store_true")
    parser.add_argument("--input-region", default="us-east-1")
    parser.add_argument("--output-bucket")
    parser.add_argument("--output-endpoint")
    parser.add_argument("--output-anon", action="store_true")
    parser.add_argument("--output-region", default="us-east-1")
    parser.add_argument(
        "--output-overwrite",
        action="store_true",
        help="CAUTION: Overwrite a previous conversion run",
    )
    parser.add_argument(
        "--output-script",
        action="store_true",
        help="CAUTION: Do not run conversion. Instead prepare scripts for later conversion",
    )
    parser.add_argument(
        "--output-threads",
        type=int,
        default=16,
        help="number of simultaneous write threads",
    )

    # Very recommended metadata (SHOULD!)
    def license_action(group, arg: str, url: str, recommended: bool = True):
        class LicenseAction(argparse.Action):
            def __call__(self, parser, args, *unused, **ignore):  # noqa: ARG002
                args.rocrate_license = url
                if not recommended:
                    warnings.warn(
                        f"This license is not recommended: {url}", stacklevel=1
                    )

        desc = url
        if not recommended:
            desc = "(not recommended) " + url
        group.add_argument(arg, action=LicenseAction, nargs=0, help=desc)

    group_lic = parser.add_mutually_exclusive_group()
    license_action(
        group_lic, "--cc0", "https://creativecommons.org/publicdomain/zero/1.0/"
    )
    license_action(group_lic, "--cc-by", "https://creativecommons.org/licenses/by/4.0/")
    group_lic.add_argument(
        "--rocrate-license",
        type=str,
        help="URL to another license, e.g., 'https://creativecommons.org/licenses/by/4.0/'",
    )

    # Recommended metadata (SHOULD)
    parser.add_argument(
        "--rocrate-organism",
        type=str,
        help="NCBI identifier of the form 'NCBI:txid7227'",
    )
    parser.add_argument(
        "--rocrate-modality",
        type=str,
        help="FBbi identifier of the form 'obo:FBbi_00000243'",
    )

    # Optional metadata (MAY)
    parser.add_argument(
        "--rocrate-name",
        type=str,
        help="optional name of the dataset; taken from the NGFF metadata if available",
    )
    parser.add_argument(
        "--rocrate-description", type=str, help="optional description of the dataset"
    )
    parser.add_argument(
        "--rocrate-skip",
        action="store_true",
        help="skips the creation of the RO-Crate file",
    )
    parser.add_argument(
        "--log", default="warn", help="'error', 'warn', 'info', 'debug' or 'trace'"
    )
    group_ex = parser.add_mutually_exclusive_group()
    group_ex.add_argument(
        "--output-write-details",
        action="store_true",
        help="don't convert array, instead write chunk and proposed shard sizes",
    )
    group_ex.add_argument(
        "--output-read-details", type=Path, help="read chink and shard sizes from file"
    )
    group_ex.add_argument(
        "--output-chunks",
        help="comma separated list of chunk sizes for all subresolutions",
        type=csv_int,
    )
    parser.add_argument(
        "--output-shards",
        help="comma separated list of shards sizes for all subresolutions",
        type=csv_int,
    )
    parser.add_argument(
        "--conversion-notes",
        help="free-text notes on this conversion (e.g., 'run on AWS EC2 instance in docker')",
    )
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_path", type=Path)


def parse(ns: argparse.Namespace):
    """
    Parse the namespace arguments provided by the dispatcher
    """
    configure_logging(ns, LOGGER)

    ns.rocrate = None
    if not ns.rocrate_skip:
        setup = {}
        for key in ("name", "description", "organism", "modality"):
            value = getattr(ns, f"rocrate_{key}", None)
            if value:
                setup[key] = value
        if not ns.rocrate_license:
            message = "No license set. Choose one of the Creative Commons license (e.g., `--cc-by`) or skip RO-Crate creation (`--rocrate-skip`)"
            raise SystemExit(message)
        setup["data_license"] = ns.rocrate_license
        ns.rocrate = ROCrateWriter(**setup)
