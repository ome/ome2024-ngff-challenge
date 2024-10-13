<script>
  import VirtualList from "svelte-tiny-virtual-list";

  import { ngffTable } from "./tableStore";
  import { organismStore, imagingModalityStore } from "./ontologyStore";
  import ColumnSort from "./ColumnSort.svelte";

  import {
    SAMPLES_HOME,
    filesizeformat,
    loadCsv,
  } from "./util";
  import Nav from "./Nav.svelte";
  import ZarrListItem from "./ZarrListItem.svelte";
  import SourcePanel from "./SourcePanel.svelte";

  // check for ?csv=url
  const params = new URLSearchParams(window.location.search);
  let csvUrl = params.get("csv");
  try {
    new URL(csvUrl);
  } catch (error) {
    csvUrl = SAMPLES_HOME;
  }

  let tableRows = [];
  // e.g. {"IDR": {"idr0004.csv": {"count": 100}}, "JAX": {}...
  let zarrSources = [];
  let totalZarrs = 0;
  let totalBytes = 0;
  let showSourceColumn = false;
  let organismIdsByName = {};
  let imagingModalityIdsByName = {};
  let dimensionFilter = "0";
  let sourceFilter = "";
  let collectionFilter = "";
  let organismFilter = "";
  let imagingModalityFilter = "";
  let textFilter = "";

  // The ngffTable is built as CSV files are loaded
  // it is NOT filtered
  ngffTable.subscribe((rows) => {
    tableRows = filterRows(rows);
    // NB: don't use filtered rows for sources
    zarrSources = ngffTable.getCsvSourceList();
    totalZarrs = rows.length;
    totalBytes = rows.reduce((acc, row) => {
      return acc + parseInt(row["written"]) || 0;
    }, 0);
  });

  organismStore.subscribe(orgOntology => {
    // iterate over orgOntology key, values
    let temp = {};
    for (const [orgId, name] of Object.entries(orgOntology)) {
      temp[name] = orgId;
    }
    organismIdsByName = temp;
  });

  imagingModalityStore.subscribe(orgOntology => {
    // iterate over orgOntology key, values
    let temp = {};
    for (const [orgId, name] of Object.entries(orgOntology)) {
      temp[name] = orgId;
    }
    imagingModalityIdsByName = temp;
  });

  $: showSourceColumn = tableRows.some((row) => row.source);

  // kick off loading the CSV to populate ngffTable...
  // This will recursively load other csv files if they are linked in the first one
  if (csvUrl) {
    loadCsv(csvUrl, ngffTable);
  }

  let sortedBy = "";
  let sortAscending = true;
  function handleSort(colname) {
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

  // Main filtering function
  function filterRows(rows) {
    if (dimensionFilter !== "0") {
      rows = rows.filter((row) => {
        return row.dim_count == dimensionFilter;
      });
    }
    if (collectionFilter !== "") {
      rows = rows.filter((row) => {
        return row.csv == collectionFilter;
      });
    } else if (sourceFilter !== "") {
      let childSrcs = ngffTable.getCsvSourceList(sourceFilter);
      let allSources = [sourceFilter, ...childSrcs.map((src) => src.source)];
      rows = rows.filter((row) => {
        return allSources.includes(row.source);
      });
    }
    if (organismFilter !== "") {
      rows = rows.filter((row) => {
        return row.organismId == organismFilter;
      });
    }
    if (imagingModalityFilter != "") {
      rows = rows.filter((row) => {
        return row.fbbiId == imagingModalityFilter;
      });
    }
    if (textFilter != "") {
      rows = rows.filter((row) => {
        return row.description?.includes(textFilter) || row.name?.includes(textFilter);
      });
    }
    return rows;
  }

  function filterSource(event) {
    sourceFilter = event.target.value;
    collectionFilter = "";
    tableRows = filterRows(ngffTable.getRows());
  }
  function filterDimensions(event) {
    dimensionFilter = event.target.value;
    tableRows = filterRows(ngffTable.getRows());
  }

  function filterCollection(event) {
    collectionFilter = event.target.value;
    tableRows = filterRows(ngffTable.getRows());
  }

  function filterOrganism(event) {
    organismFilter = event.target.value;
    tableRows = filterRows(ngffTable.getRows());
  }

  function filterImagingModality(event) {
    imagingModalityFilter = event.target.value;
    tableRows = filterRows(ngffTable.getRows());
  }

  function filterText(event) {
    console.log("filterText", event.target.value);
    textFilter = event.target.value;
    tableRows = filterRows(ngffTable.getRows());
  }

  function formatCsv(url) {
    return url.split("/").pop().replace(".csv", "").replace("_samples", "");
  }
</script>

<div class="app">
  <Nav />

  <main>
    <!-- <h1 class="title">OME 2024 NGFF Challenge</h1> -->

    <div class="summary">

      <h2>
        {totalZarrs} Zarr Images,
        {filesizeformat(totalBytes)}, from {zarrSources.length} sources:
      </h2>

      <div class="sources">
        {#each zarrSources as source}
          <SourcePanel {source} handleFilter={filterSource} />
        {/each}
        {#if sourceFilter !== ""}
          {#each ngffTable.getCsvSourceList(sourceFilter) as childSource}
            <div class="source">
              <label>
                <input
                  on:change={filterCollection}
                  type="radio"
                  name="collection"
                  value={childSource.url}
                />
                {childSource.source == sourceFilter
                  ? formatCsv(childSource.url)
                  : childSource.source} ({childSource.image_count})
              </label>
            </div>
          {/each}

          <div class="source clear">
            <label>
              <input
                on:change={filterSource}
                type="radio"
                name="source"
                value=""
              />
              &#10060 Clear Source Filter
            </label>
          </div>
        {/if}
      </div>

      <div class="filterRow">
        <input on:input={filterText} placeholder="Filter by Name or Description" name="textFilter"/>
        <div class="filters">
          <div style="white-space: nowrap;">Filter by:</div>
          <select on:change={filterDimensions}>
            <option value="0">{dimensionFilter !== "0" ? "All Dimensions" : "Dimension Count"}</option>
            <option value="2">2D</option>
            <option value="3">3D</option>
            <option value="4">4D</option>
            <option value="5">5D</option>
          </select>

          <select on:change={filterOrganism}>
            <option value="">{organismFilter == "" ? "Organism" : "All Organisms"}</option>
            {#each Object.keys(organismIdsByName).sort() as name}
              <option value={organismIdsByName[name]}>{name}</option>
            {/each}
          </select>

          <select on:change={filterImagingModality}>
            <option value="">{organismFilter == "" ? "Imaging Modality" : "All Modalities"}</option>
            {#each Object.keys(imagingModalityIdsByName).sort() as name}
              <option value={imagingModalityIdsByName[name]}>{name}</option>
            {/each}
          </select>

        </div>
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

    <div class="imageListContainer">
      <h3 style="margin-left: 15px">Showing {tableRows.length} zarrs</h3>
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
    </div>
  </main>
</div>

<style>

  .filterRow {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 100px;
  }

  .filterRow input {
    height: 32px;
    width: 300px;
    flex: auto 1 1;
    border: solid grey 1px;
    border-radius: 16px;
    padding: 10px;
    font-size: 20px;
    background-color: #bbb;
  }

  @media (max-width: 800px) {
    .filterRow {
      flex-direction: column;
      gap: 0;
    }
    .filterRow input {
      width: 100%;
    }
  }
  select {
    display: block;
    width: 150px;
    height: 30px;
    padding: 2px;
    font-size: 1rem;
    line-height: 1.5;
    appearance: none;
    background-color: #bbb;
    border: 1px solid #dee2e6;
    border-radius: 0.375rem;
  }

  .source:has(input:checked) {
    border: solid #ccc 2px;
    background-color: #333;
  }
  .clear {
    background-color: #333;
  }
  .imageListContainer {
    border: solid #333 2px;
    max-width: 700px;
    margin: auto;
  }
  .sources {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
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
  .source label {
    display: block;
    position: relative;
    padding: 5px;
    cursor: pointer;
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
  .filters {
    display: flex;
    flex-direction: row;
    gap: 10px;
    margin: 5px 0;
  }
  main {
    background-color: black;
    flex: auto 1 1;
    overflow: scroll;
    color: white;
    width: 100%;
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
    top: 0;
    background-color: black;
    z-index: 20;
    padding: 10px;
  }
</style>
