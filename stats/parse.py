#!/usr/bin/env python
from __future__ import annotations

import shutil
import tempfile

import fastparquet
import pandas as pd

cols = {"source", "origin", "url", "written_human_readable", "written"}
valid = []
with tempfile.TemporaryDirectory() as tmpdirname:
    print("created temporary directory", tmpdirname)

    df = pd.read_csv("ngff_samples.csv")
    urls = []
    for index, row in df.iterrows():
        src = row["source"]
        url = row["url"]
        print(url)
        urls.append(url)

        df2 = pd.read_csv(f"{url}")
        if not set(df2.columns).issubset(cols):
            print(f"invalid csv: {url}")
        else:
            filename = f"{tmpdirname}/index.pq"
            df2.to_parquet(filename)
            valid.append(filename)

    fastparquet.writer.merge([filename for filename in valid])
    df_all = pd.read_parquet("all.pq")
    print(df_all)

shutil.rmtree(tmpdirname)
