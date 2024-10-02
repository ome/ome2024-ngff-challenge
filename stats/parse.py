#!/usr/bin/env python
import asyncio
import aiohttp
import fastparquet
import math
import os
import pandas as pd
import requests
from collections import defaultdict
from aiohttp_retry import RetryClient, ExponentialRetry


CONNECTIONS = int(os.environ.get("CONNECTIONS", 80))
RETRIES = int(os.environ.get("RETRIES", 3))
TIMEOUT = float(os.environ.get("TIMEOUT", 60.0))

cols = ('source', 'origin', 'url', 'written_human_readable', 'written')




class Event:

    def __init__(self, depth, url):
        self.depth = depth
        self.url = url
        self.state = {}

    def __str__(self):
        return f'{"\t"*self.depth}{self.url}'

    async def load(self, rsp):
        raise NotImplementedError()

class CSVEvent(Event):

    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp=None):
        self.state = {"type": "csv"}


class ZarrEvent(Event):

    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        data = await rsp.json()
        ome = data.get("attributes", {}).get("ome", {})
        # Calcluate
        if "multiscales" in ome:
            self.state["type"] = "multiscales"
            inner = ome["multiscales"][0]["datasets"][0]["path"]
            # FIXME
            MultiscaleEvent(self.depth+1, f"{self.url}/{inner}")

        # Defer
        for x in ("plate", "bioformats2raw.layout"):
            if x in ome:
                self.state["type"] = x

        if "type" not in self.state:
            self.state["type"] = f"unknown: {ome.keys()}"


class MultiscaleEvent(Event):

    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)
        self.state = {}

    async def load(self, rsp):
        data = await rsp.json()
        self.state["type"] = "array"
        self.state["array"] = data


def handle_csv(src, url, depth=1):
    df2 = pd.read_csv(f'{url}')

    if not set(df2.columns).issubset(set(cols)):
        print(f"invalid csv: {url}")
        return

    yield CSVEvent(depth, url)
    size = len(df2.index)

    df2["csv"] = [url] * size
    df2["who"] = [src] * size
    for colname in cols:
        if colname not in df2.columns:
            df2[colname] = [None] * size


    for index2, row2 in df2.iterrows():
        url = row2["url"]
        if not url or not isinstance(url, str):
            # TODO: debug?
            continue
        try:
            if url.endswith(".csv"):
                # TODO: check for a sub-source
                yield from handle_csv(src, url, depth=depth+1)
            else:
                leaf = depth + 1
                zarr = f'{row2["url"]}/zarr.json'
                yield ZarrEvent(depth+1, zarr)
        except Exception as e:
            print(f"error: {url} (type={type(url)})")
            raise

def get_events():
    valid = []

    main_url = 'https://raw.githubusercontent.com/will-moore/ome2024-ngff-challenge/samples_viewer/samples/ngff_samples.csv'
    print(main_url)
    df = pd.read_csv(main_url)
    urls = []

    events = []
    for index, row in df.iterrows():

        src = row['source']
        url = row['url']
        urls.append(url)
        for event in handle_csv(src, url):
            events.append(event)

    return events


async def get(event: Event, client: RetryClient):
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=TIMEOUT, sock_read=TIMEOUT)
    async with client.get(event.url, timeout=timeout) as response:
        print(event)
        await event.load(response)



async def main():

    # Setup
    connector = aiohttp.TCPConnector(limit=CONNECTIONS)
    session = aiohttp.ClientSession(connector=connector)
    options = ExponentialRetry(attempts=RETRIES)
    client = RetryClient(
            client_session=session,
            raise_for_status=False,
            retry_options=options,
    )

    # Loading
    events = get_events()
    ret = await asyncio.gather(*(get(event, client) for event in events))

    # Parsing
    try:
        tallies = defaultdict(int)
        for event in events:
            _type = event.state.get("type")
            tallies[_type] += 1

        for k, v in tallies.items():
            print(k, v)

    # Cleaning
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
