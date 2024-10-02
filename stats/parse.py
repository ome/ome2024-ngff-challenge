#!/usr/bin/env python
from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict

import aiohttp
import pandas as pd
from aiohttp_retry import ExponentialRetry, RetryClient

COLUMNS = ("source", "origin", "url", "written_human_readable", "written")
CONNECTIONS = int(os.environ.get("CONNECTIONS", 80))
RETRIES = int(os.environ.get("RETRIES", 3))
TIMEOUT = float(os.environ.get("TIMEOUT", 60.0))
URL = os.environ.get(
    "URL",
    "https://raw.githubusercontent.com/will-moore/ome2024-ngff-challenge/samples_viewer/samples/ngff_samples.csv",
)
WORKERS = int(os.environ.get("WORKERS", 40))


class Event:
    def __init__(self, queue, depth, url):
        self.queue = queue
        self.depth = depth
        self.url = url
        self.state = {}

    def root(self):
        """drops the /zarr.json suffix from urls"""
        return self.url[:-10]

    def __str__(self):
        return f'{"\t"*self.depth}{self.url}'

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.url}>"

    async def load(self, rsp):
        raise NotImplementedError()


class CSVEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp=None):
        self.state = {"type": "csv"}

        df2 = pd.read_csv(f"{self.url}")

        if not set(df2.columns).issubset(set(COLUMNS)):
            print(f"invalid csv: {self.url}")
            return

        size = len(df2.index)

        df2["csv"] = [self.url] * size
        for colname in COLUMNS:
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
                    await self.queue.put(CSVEvent(self.queue, self.depth + 1, url))
                else:
                    leaf = self.depth + 1
                    zarr = f'{row2["url"]}/zarr.json'
                    await self.queue.put(ZarrEvent(self.queue, self.depth + 1, zarr))
            except Exception:
                print(f"error: {url} (type={type(url)})")
                raise


class ZarrEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        data = await rsp.json()
        ome = data.get("attributes", {}).get("ome", {})

        # Array
        if "multiscales" in ome:
            self.state["type"] = "multiscales"
            inner = ome["multiscales"][0]["datasets"][0]["path"]
            await self.queue.put(
                MultiscaleEvent(
                    self.queue, self.depth + 1, f"{self.root()}/{inner}/zarr.json"
                )
            )

        # Series
        elif "plate" in ome:
            self.state["type"] = "plate"
            # TODO

        # Series
        elif "bioformats2raw.layout" in ome:
            self.state["type"] = "bioformats2raw.layout"
            await self.queue.put(
                OMEEvent(self.queue, self.depth + 1, f"{self.root()}/OME/zarr.json")
            )

        if "type" not in self.state:
            self.state["type"] = f"unknown: {ome.keys()}"


class OMEEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        data = await rsp.json()
        self.state["type"] = "ome"
        series = data["attributes"]["ome"]["series"]
        for s in series:
            await self.queue.put(
                MultiscaleEvent(
                    self.queue, self.depth + 1, f"{self.root()}/{s}/zarr.json"
                )
            )


class MultiscaleEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        data = await rsp.json()
        self.state["type"] = "array"
        self.state["array"] = data


class ErrorEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        self.state["type"] = "error"


async def process(event: Event, client: RetryClient):
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=TIMEOUT, sock_read=TIMEOUT)
    async with client.get(event.url, timeout=timeout) as response:
        print(event)
        await event.load(response)


async def worker(queue, client, state):
    while not queue.empty():
        event = await queue.get()
        try:
            await process(event, client)
            await state.put(event.state)
        except Exception as e:
            await state.put({"event": event, "error": e, "type": "error"})
        finally:
            queue.task_done()


async def main():
    start = time.time()

    # HTTP Setup
    connector = aiohttp.TCPConnector(limit=CONNECTIONS)
    session = aiohttp.ClientSession(connector=connector)
    options = ExponentialRetry(attempts=RETRIES)
    client = RetryClient(
        client_session=session,
        raise_for_status=False,
        retry_options=options,
    )

    queue = asyncio.Queue()
    state = asyncio.Queue()
    csv = CSVEvent(queue, 0, URL)
    await queue.put(csv)
    await process(csv, client)

    # Loading
    consumers = [
        asyncio.create_task(worker(queue, client, state)) for _ in range(WORKERS)
    ]
    await queue.join()
    for c in consumers:
        c.cancel()

    # Parsing
    try:
        tallies = defaultdict(int)
        errors = []
        while not state.empty():
            v = await state.get()
            _type = v.get("type")
            tallies[_type] += 1
            if _type == "error":
                errors.append(v)
        for k, v in tallies.items():
            print(k, v)
        for err in errors:
            print(err)

    # Cleaning
    finally:
        await client.close()

    stop = time.time()
    print(f"in {stop-start:0.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
