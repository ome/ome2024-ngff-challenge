from __future__ import annotations

import argparse
import logging

import requests

from .utils import configure_logging

LOGGER = logging.getLogger(__file__)


def cli(subparsers: argparse._SubParsersAction):
    cmd = "ome2024-ngff-challenge lookup"
    desc = f"""


The `lookup` subcommand will take search the EBI OLS service
for metadata identifiers matching the given input.


BASIC

    Simplest example:                        {cmd} "light-sheet"


    """
    parser = subparsers.add_parser(
        "lookup",
        help="lookup metadata from EBI OLS",
        description=desc,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.set_defaults(func=main)
    parser.add_argument(
        "--log", default="info", help="'error', 'warn', 'info', 'debug' or 'trace'"
    )
    parser.add_argument("text")


def parse(ns: argparse.Namespace):
    """
    Parse the namespace arguments provided by the dispatcher
    """

    configure_logging(ns, LOGGER)


def main(ns: argparse.Namespace):
    text = ns.text
    url = f"https://www.ebi.ac.uk/ols4/api/search?q={text}&obsoletes=false&local=false&rows=10&start=0&format=json&lang=en"
    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()
        docs = result["response"]["docs"]
        header = "ONTOLOGY  \tTERM                \tLABEL                         \tDESCRIPTION"
        print(header)  # noqa: T201
        for doc in docs:
            onto = doc["ontology_name"]
            term = doc["short_form"]
            name = doc["label"]
            desc = "" if not doc["description"] else doc["description"][0]
            desc = desc.split("\n")[0][:70]  # At most first 70 chars of first line
            print(f"""{onto:10s}\t{term:20s}\t{name:30s}\t{desc}""")  # noqa: T201

    else:
        raise Exception(response)
