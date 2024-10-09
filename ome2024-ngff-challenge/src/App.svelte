<script>
  import VirtualList from "svelte-tiny-virtual-list";

  import { ngffTable } from "./tableStore";
  import ColumnSort from "./ColumnSort.svelte";

  import {
    getSourceIcon,
    SAMPLES_HOME,
    filesizeformat,
    loadCsv,
    lookupImagingModality,
    lookupOrganism,
  } from "./util";
  import Nav from "./Nav.svelte";
  import ZarrListItem from "./ZarrListItem.svelte";
  import ThumbLoader from "./ThumbLoader.svelte";

  // check for ?csv=url
  const params = new URLSearchParams(window.location.search);
  let csvUrl = params.get("csv");
  try {
    new URL(csvUrl);
  } catch (error) {
    console.error("Invalid csv URL", csvUrl);
    csvUrl = SAMPLES_HOME;
  }

  let tableRows = [];
  // e.g. {"IDR": {"idr0004.csv": {"count": 100}}, "JAX": {}...
  let zarrSources = {};
  let totalZarrs = 0;
  let totalBytes = 0;
  let showSourceColumn = false;
  let organismLookup = {};
  let imagingModalityLookup = {};
  let filterDims = "0";
  let sourceFilter = "";

  // The ngffTable is built as CSV files are loaded
  // it is NOT filtered
  ngffTable.subscribe((rows) => {
    tableRows = filterRows(rows);
    // NB: don't use filtered rows for sources
    zarrSources = rows.reduce((prev, row) => {
      let source = row.source;
      if (!prev[source]) {
        prev[source] = {};
      }
      if (!prev[source][row.csv]) {
        prev[source][row.csv] = {"count": 0, "url": row.url}
      }
      prev[source][row.csv].count += 1;
      return prev;
    }, {});
    totalZarrs = rows.length;
    totalBytes = rows.reduce((acc, row) => {
      return acc + parseInt(row["written"]) || 0;
    }, 0);
  });

  $: showSourceColumn = tableRows.some((row) => row.source);

  // kick off loading the CSV to populate ngffTable...
  // This will recursively load other csv files if they are linked in the first one
  if (csvUrl) {
    loadCsv(csvUrl, ngffTable);
  }

  // This is called by the <table> if we are missing organisms from the lookup dict.
  // Updating organismLookup should trigger all table rows to be re-rendered
  function loadOrganism(organismId) {
    console.log("loadOrganism", organismId);
    if (!organismId) {
      return "";
    }
    if (organismLookup[organismId]) {
      return organismLookup[organismId];
    }
    // put a placeholder to avoid multiple requests while we wait for the lookup
    organismLookup[organismId] = organismId;
    lookupOrganism(organismId).then((organism) => {
      organismLookup = { ...organismLookup, [organismId]: organism };
    });
    return organismId;
  }

  function loadImagingModality(fbbiId) {
    if (!fbbiId) {
      return "";
    }
    if (imagingModalityLookup[fbbiId]) {
      return imagingModalityLookup[fbbiId];
    }
    // put a placeholder to avoid multiple requests while we wait for the lookup
    imagingModalityLookup[fbbiId] = fbbiId;
    lookupImagingModality(fbbiId).then((imagingModality) => {
      imagingModalityLookup = {
        ...imagingModalityLookup,
        [fbbiId]: imagingModality,
      };
    });
    return fbbiId;
  }

  let sortedBy = "";
  let sortAscending = true;
  function handleSort(colname) {
    console.log("handleSort", colname, "sortedBy", sortedBy);
    if (sortedBy === colname) {
      sortAscending = !sortAscending;
    } else {
      // start by sorting descending (biggest first)
      sortAscending = false;
    }
    sortedBy = colname;
    ngffTable.sortTable(colname, sortAscending);
  }

  function getItemKey(index) {
    return tableRows[index].url;
  }

  function filterRows(rows) {
    if (filterDims !== "0") {
      rows = rows.filter((row) => {
        return row.dim_count == filterDims;
      });
    }
    if (sourceFilter !== "") {
      rows = rows.filter((row) => {
        return row.source == sourceFilter;
      });
    }
    return rows;
  }

  function filterSource(event) {
    sourceFilter = event.target.value;
    tableRows = filterRows(ngffTable.getRows());
  }
  function filterDimensions(event) {
    filterDims = event.target.value;
    tableRows = filterRows(ngffTable.getRows());
  }
</script>

<div class="app">
  <Nav />

  <main>
    <h1 class="title">OME 2024 NGFF Challenge</h1>

    <div class="summary">
      <h2>
        {totalZarrs} Zarr Images,
        {filesizeformat(totalBytes)}, from {Object.keys(zarrSources).length} sources:
      </h2>

      {#if showSourceColumn}
        <div class="sources">
          {#each Object.keys(zarrSources).sort() as source}
            <label class="source">
              <img title={Object.values(zarrSources[source])[0].url} class="sourceLogo" alt="Source logo" src="{getSourceIcon(source)}" />
              <input
                on:change={filterSource}
                type="radio"
                name="source"
                value={source}
              />
              {source}
              ({Object.values(zarrSources[source]).reduce((prev, collection) => {console.log("COL", collection, prev + collection.count); return prev + collection.count}, 0)} images)
            </label>
          {/each}
          {#if sourceFilter !== ""}
            <label class="source">
              <input
                on:change={filterSource}
                type="radio"
                name="source"
                value=""
              />
              &lt; All Sources
            </label>
          {/if}
        </div>
      {/if}

      <div>
        Filter:
        <select on:change={filterDimensions}>
          <option value="0">All Dimensions</option>
          <option value="2">2D</option>
          <option value="3">3D</option>
          <option value="4">4D</option>
          <option value="5">5D</option>
        </select>
      </div>
      <div>
        Sort:
        <ColumnSort
          col_label={"X"}
          col_name={"size_x"}
          {handleSort}
          {sortedBy}
          {sortAscending}
        />
        <ColumnSort
          col_label={"Y"}
          col_name={"size_y"}
          {handleSort}
          {sortedBy}
          {sortAscending}
        />
        <ColumnSort
          col_label={"Z"}
          col_name={"size_z"}
          {handleSort}
          {sortedBy}
          {sortAscending}
        />
        <ColumnSort
          col_label={"C"}
          col_name={"size_c"}
          {handleSort}
          {sortedBy}
          {sortAscending}
        />
        <ColumnSort
          col_label={"T"}
          col_name={"size_t"}
          {handleSort}
          {sortedBy}
          {sortAscending}
        />
        <ColumnSort
          col_label={"Data size"}
          col_name={"written"}
          {handleSort}
          {sortedBy}
          {sortAscending}
        />
      </div>
    </div>

    {#if tableRows.length != ngffTable.getRows().length}
      <h3>Showing {tableRows.length} zarrs</h3>
    {/if}

    <VirtualList
      width="100%"
      height={600}
      itemCount={tableRows.length}
      itemSize={150}
      getKey={getItemKey}
    >
      <div slot="item" let:index let:style {style} class="row">
        <ZarrListItem listIndex={index} rowData={tableRows[index]} />
      </div>
    </VirtualList>
  </main>
</div>

<style>

  .sources {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
    gap: 5px;
  }
  .source {
    border: solid #333 1px;
    float: left;
    position: relative;
    padding: 3px;
    border-radius: 5px;
    cursor: pointer;
  }
  .sourceLogo {
    width: 24px;
    height: 24px;
    margin: 2px;
    background-color: #fff;
    padding: 2px;
    border-radius: 3px;
    top: 6px;
    left: 6px;
  }
  input[type="radio"] {
    visibility: hidden;
    width: 0;
    margin: 0;
  }
  .row {
    background-color: black;
    padding: 10px;
    color: white;
  }
  .app {
    margin: 0;
    padding: 0;
    background-color: black;
    inset: 0;
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  main {
    background-color: black;
    flex: auto 1 1;
    overflow: scroll;
    color: white;
  }

  .title {
    color: white;
    z-index: 10;
    position: relative;
    margin-bottom: 10px;
  }
  .summary {
    margin-bottom: 2em;
    color: white;
    position: sticky;
    top: 0;
    background-color: black;
    z-index: 20;
    padding: 10px;
  }
</style>
