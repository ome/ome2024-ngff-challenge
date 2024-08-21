"""
Copyright (c) 2024 Josh Moore. All rights reserved.

ome2024-ngff-challenge: Tools for converting OME-Zarr data within the ome2024-ngff-challenge (see https://forum.image.sc/t/ome2024-ngff-challenge/97363)
"""

from __future__ import annotations

import argparse
import sys

from .resave import cli as resave_cli

__version__ = "0.0.0"

__all__ = ["__version__"]


def dispatch(args=sys.argv[1:]):
    """
    Parses the arguments contained in `args` and passes
    them to `main`. If no images are converted, raises
    SystemExit. Otherwise, return the number of images.
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(help="subparser help")
    resave_cli(subparsers)
    # Upcoming parsers to be moved to submodules
    subparsers.add_parser("validate", help="TBD: evaluate a converted fileset locally")
    subparsers.add_parser("lookup", help="TBD: lookup the identifier for an OLS term")
    subparsers.add_parser(
        "update", help="TBD: updated the RO-Crate metadata in a fileset"
    )
    ns = parser.parse_args(args)
    return ns.func(ns)
