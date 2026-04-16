#!/usr/bin/env python
from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from logging import StreamHandler
from logging.handlers import QueueHandler, QueueListener

import aiohttp
import pandas as pd
from aiohttp_retry import ExponentialRetry, RetryClient

try:
    import Queue as queue
except ImportError:
    import queue


COLUMNS = ("source", "origin", "url", "written_human_readable", "written")
CONNECTIONS = int(os.environ.get("CONNECTIONS", 80))
RETRIES = int(os.environ.get("RETRIES", 3))
TIMEOUT = float(os.environ.get("TIMEOUT", 60.0))
URL = os.environ.get(
    "URL",
    "https://raw.githubusercontent.com/ome/ome2024-ngff-challenge/refs/heads/main/samples/ngff_samples.csv",
)
WORKERS = int(os.environ.get("WORKERS", 40))

LOGGER_TASK = None


async def safely_start_logger():
    LOGGER_TASK = asyncio.create_task(init_logger())
    await asyncio.sleep(0)


async def init_logger():
    # helper coroutine to setup and manage the logger
    # https://superfastpython.com/asyncio-log-blocking/#How_to_Log_From_Asyncio_Without_Blocking
    log = logging.getLogger()
    que = queue.Queue()
    log.addHandler(QueueHandler(que))
    log.setLevel(logging.INFO)
    listener = QueueListener(que, StreamHandler())
    try:
        listener.start()
        while True:
            await asyncio.sleep(60)
    finally:
        listener.stop()


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

    async def load(self, *args):
        self.state = {"type": "csv"}

        df2 = pd.read_csv(f"{self}")

        if not set(df2.columns).issubset(set(COLUMNS)):
            logging.warning(f"invalid csv: {self.url}")
            return

        size = len(df2.index)
        logging.info(f"{self}")

        df2["csv"] = [self.url] * size
        for colname in COLUMNS:
            if colname not in df2.columns:
                df2[colname] = [None] * size

        for _, row2 in df2.iterrows():
            url = row2["url"]
            if not url or not isinstance(url, str):
                # TODO: debug?
                continue
            if url.endswith(".csv"):
                # TODO: check for a sub-source
                await self.queue.put(CSVEvent(self.queue, self.depth + 1, url))
            else:
                zarr = f'{row2["url"]}/zarr.json'
                await self.queue.put(ZarrEvent(self.queue, self.depth + 1, zarr))


class ZarrEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        data = await rsp.json()
        ome = data.get("attributes", {}).get("ome", {})
        logging.info(f"{self}")

        # TODO: could check for RO-Crates in subdirectories
        await self.queue.put(
            ROCrateEvent(
                self.queue, self.depth + 1, f"{self.root()}/ro-crate-metadata.json"
            )
        )

        if "multiscales" in ome:
            self.state["type"] = "multiscales"
            inner = ome["multiscales"][0]["datasets"][0]["path"]
            await self.queue.put(
                MultiscaleEvent(
                    self.queue, self.depth + 1, f"{self.root()}/{inner}/zarr.json"
                )
            )

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
                OMESeriesEvent(
                    self.queue, self.depth + 1, f"{self.root()}/OME/zarr.json"
                )
            )

        if "type" not in self.state:
            self.state["type"] = f"unknown: {ome.keys()}"


class ROCrateEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        if rsp.status >= 400:
            raise MissingException(f"status:{rsp.status}")
        else:
            data = await rsp.json()
            logging.info(f"{self}")


class OMESeriesEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        if rsp.status >= 400:
            await self.queue.put(
                OMEMetadataEvent(
                    self.queue, self.depth, f"{self.root()}/METADATA.ome.xml"
                )
            )
        else:
            data = await rsp.json()
            logging.info(f"{self}")
            self.state["type"] = "ome"
            series = data["attributes"]["ome"]["series"]
            for s in series:
                await self.queue.put(
                    MultiscaleEvent(
                        self.queue, self.depth + 1, f"{self.root()[:-4]}/{s}/zarr.json"
                    )
                )


class OMEMetadataEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        if rsp.status >= 400:
            raise MissingException(f"status:{rsp.status}")
            # TODO: just check for the individual series

        data = await rsp.json()
        logging.info(f"{self}")
        self.state["type"] = "ome"
        series = data["attributes"]["ome"]["series"]
        for s in series:
            await self.queue.put(
                MultiscaleEvent(
                    self.queue, self.depth + 1, f"{self.root()[:-4]}/{s}/zarr.json"
                )
            )


class MultiscaleEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, rsp):
        data = await rsp.json()
        logging.info(f"{self}")
        self.state["type"] = "array"
        self.state["array"] = data


class ErrorEvent(Event):
    def __init__(self, *args, **kwargs):
        Event.__init__(self, *args, **kwargs)

    async def load(self, *ignore):
        self.state["type"] = "error"


class MissingException(Exception):
    def __init__(self, code):
        Exception.__init__(self)
        self.code = code


async def process(event: Event, client: RetryClient):
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=TIMEOUT, sock_read=TIMEOUT)
    async with client.get(event.url, timeout=timeout) as response:
        await event.load(response)


async def worker(queue, client, state):
    while not queue.empty():
        event = await queue.get()
        try:
            await process(event, client)
            await state.put(event.state)
        except MissingException as me:
            await state.put({"event": event, "code": me.code})
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

    await safely_start_logger()

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
            logging.info(f"{k}={v}")
        for err in errors:
            logging.error(f"{err}")

    # Cleaning
    finally:
        await client.close()

    stop = time.time()
    logging.info(f"in {stop-start:0.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
