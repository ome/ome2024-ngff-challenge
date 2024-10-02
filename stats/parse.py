#!/usr/bin/env python
import fastparquet
import pandas as pd

cols = [ 'source', 'origin', 'url', 'written_human_readable', 'written']
valid = []

df = pd.read_csv('ngff_samples.csv')
urls = []
for index, row in df.iterrows():

    src = row['source']
    url = row['url']
    urls.append(url)

    df2 = pd.read_csv(f'{url}')
    if not set(df2.columns).issubset(set(cols)):
        print(f"invalid csv: {url}")
    else:

        size = len(df2.index)

        df2["csv"] = [url] * size
        df2["who"] = [src] * size
        for colname in cols:
            if colname not in df2.columns:
                df2[colname] = [None] * size

        df2 = df2.reindex(columns=["who", "csv"] + cols)

        filename = f"all.pq/csv={index}"
        df2.to_parquet(filename)
        valid.append(filename)

fastparquet.writer.merge([filename for filename in valid])
df_all = pd.read_parquet('all.pq')
print(df_all)
