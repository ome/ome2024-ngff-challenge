<script>
  import { ngffTable } from "./tableStore";
  import { organismStore, imagingModalityStore } from "./ontologyStore";
  import ColumnSort from "./ColumnSort.svelte";
  import ImageList from "./ImageList.svelte";
  import PreviewPopup from "./PreviewPopup.svelte";
  import form_select_bg_img from "/selectCaret.svg";

  import { SAMPLES_HOME, filesizeformat, loadCsv } from "./util";
  import Nav from "./Nav.svelte";
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
  $: dimensionFilter = "";
  $: sourceFilter = "";
  $: collectionFilter = "";
  $: organismFilter = "";
  $: imagingModalityFilter = "";
  $: textFilter = "";

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

  organismStore.subscribe((orgOntology) => {
    // iterate over orgOntology key, values
    let temp = {};
    for (const [orgId, name] of Object.entries(orgOntology)) {
      temp[name] = orgId;
    }
    organismIdsByName = temp;
  });

  imagingModalityStore.subscribe((orgOntology) => {
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
  let sortAscending = false;
  function toggleSortAscending() {
    sortAscending = !sortAscending;
    ngffTable.sortTable(sortedBy, sortAscending);
  }
  function handleSort(event) {
    sortedBy = event.target.value;
    if (sortedBy === "") {
      ngffTable.sortTable("index", true);
    } else {
      ngffTable.sortTable(sortedBy, sortAscending);
    }
  }

  // Main filtering function
  function filterRows(rows) {
    if (dimensionFilter !== "") {
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
    if (textFilter && textFilter != "") {
      let txt = textFilter.toLowerCase();
      rows = rows.filter((row) => {
        return (
          row.url.toLowerCase().includes(txt) ||
          row.description?.toLowerCase().includes(txt) ||
          row.name?.toLowerCase().includes(txt)
        );
      });
    }
    return rows;
  }

  function filterSource(event) {
    sourceFilter = event.target.value || "";
    collectionFilter = "";
    console.log("filterSource", sourceFilter, collectionFilter);
    tableRows = filterRows(ngffTable.getRows());
  }
  function filterDimensions(event) {
    dimensionFilter = event.target.value || "";
    tableRows = filterRows(ngffTable.getRows());
  }

  function filterCollection(event) {
    collectionFilter = event.target.value || "";
    tableRows = filterRows(ngffTable.getRows());
  }

  function filterOrganism(event) {
    organismFilter = event.target.value || "";
    tableRows = filterRows(ngffTable.getRows());
  }

  function filterImagingModality(event) {
    imagingModalityFilter = event.target.value || "";
    tableRows = filterRows(ngffTable.getRows());
  }

  function filterText(event) {
    textFilter = event.target.value;
    tableRows = filterRows(ngffTable.getRows());
  }

  function formatCsv(url) {
    return url.split("/").pop().replace(".csv", "").replace("_samples", "");
  }
</script>


  <PreviewPopup />

  <main style="--form-select-bg-img: url('{form_select_bg_img}')">
    <!-- <h1 class="title">OME 2024 NGFF Challenge</h1> -->

    <div class="summary">
      <h3 style="text-align:center">
        {#if csvUrl == SAMPLES_HOME}
          The OME-NGFF project has collected
          <strong style="font-weight:600">{filesizeformat(totalBytes)}</strong>
          of public bioimage data in Zarr v3 format.
          {/if}
          <div style="font-size: 90%">
            Showing Collection:
            <a href="{csvUrl}">{csvUrl.split("/").pop()}</a>
            {#if csvUrl != SAMPLES_HOME}
              ({filesizeformat(totalBytes)})
              <span style="color:grey">&nbsp | &nbsp</span>
              <a href="{window.location.origin + window.location.pathname}">Show all collections</a>
            {/if}
          </div>
      </h3>

      <div class="textInputWrapper">
        <input
          bind:value={textFilter}
          on:input={filterText}
          placeholder="Filter by Name or Description"
          name="textFilter"
        />
        <button
          title="Clear Filter"
          style="visibility: {textFilter !== '' ? 'visible' : 'hidden'}"
          on:click={filterText}
          >&times;
        </button>
      </div>

      <div class="sources">
        {#each zarrSources as source}
          <SourcePanel {source} handleFilter={filterSource} />
        {/each}
      </div>
    </div>

    <!-- start left side-bar (moves to top for mobile) -->
    <div class="sidebarContainer">
      <div class="sidebar">
        <div class="filters">
          <div style="white-space: nowrap;">Filter by:</div>
          {#if sourceFilter !== "" && ngffTable.getCsvSourceList(sourceFilter).length > 0}
            <div class="selectWrapper">
              <select
                name="collection"
                bind:value={collectionFilter}
                on:change={filterCollection}
              >
                <option value="">Collection</option>
                {#each ngffTable.getCsvSourceList(sourceFilter) as childSource}
                  <option value={childSource.url}>
                    {childSource.source == sourceFilter
                      ? formatCsv(childSource.url)
                      : childSource.source} ({childSource.image_count})
                  </option>
                {/each}
              </select>
              <div>
                <button
                  title="Clear Filter"
                  style="visibility: {collectionFilter !== ''
                    ? 'visible'
                    : 'hidden'}"
                  on:click={filterCollection}
                  >&times;
                </button>
              </div>
            </div>
          {/if}

          <div class="selectWrapper">
            <select bind:value={dimensionFilter} on:change={filterDimensions}>
              <option value=""
                >{dimensionFilter !== ""
                  ? "All Dimensions"
                  : "Dimension Count"}</option
              >
              <hr />
              <option value="2">2D</option>
              <option value="3">3D</option>
              <option value="4">4D</option>
              <option value="5">5D</option>
            </select>
            <div>
              <button
                title="Clear Filter"
                style="visibility: {dimensionFilter !== ''
                  ? 'visible'
                  : 'hidden'}"
                on:click={filterDimensions}
                >&times;
              </button>
            </div>
          </div>

          <div class="selectWrapper">
            <select bind:value={organismFilter} on:change={filterOrganism}>
              <option value=""
                >{organismFilter == "" ? "Organism" : "All Organisms"}</option
              >
              <hr />
              {#each Object.keys(organismIdsByName).sort() as name}
                <option value={organismIdsByName[name]}>{name}</option>
              {/each}
            </select>
            <div>
              <button
                title="Clear Filter"
                style="visibility: {organismFilter !== ''
                  ? 'visible'
                  : 'hidden'}"
                on:click={filterOrganism}
                >&times;
              </button>
            </div>
          </div>

          <div class="selectWrapper">
            <select
              bind:value={imagingModalityFilter}
              on:change={filterImagingModality}
            >
              <option value=""
                >{imagingModalityFilter == ""
                  ? "Imaging Modality"
                  : "All Modalities"}</option
              >
              <hr />
              {#each Object.keys(imagingModalityIdsByName).sort() as name (name)}
                <option value={imagingModalityIdsByName[name]}>{name}</option>
              {/each}
            </select>
            <div>
              <button
                title="Clear Filter"
                style="visibility: {imagingModalityFilter !== ''
                  ? 'visible'
                  : 'hidden'}"
                on:click={filterImagingModality}
                >&times;
              </button>
            </div>
          </div>

          <div class="clear"></div>

          <div>Sort by:</div>
          <div class="selectWrapper">
            <select
              on:change={handleSort}
            >
              <option value="">--</option
              >
              <hr />
              {#each ["x", "y", "z", "c", "t"] as dim}
                <option value="size_{dim}">Size: {dim.toUpperCase()}</option>
              {/each}
              <hr />
              <option value="written">Data Size (bytes)</option>
              <option value="chunk_pixels">Chunk Size (pixels)</option>
              <option value="shard_pixels">Shard Size (pixels)</option>
            </select>
            <div>
              <ColumnSort
                toggleAscending={toggleSortAscending}
                sortAscending={sortAscending} />
            </div>
          </div>
        </div>
      </div>

      <div class="results">
        <h3 style="margin-left: 15px">Showing {tableRows.length} out of {totalZarrs} images</h3>
        <ImageList {tableRows} {textFilter} {sortedBy} />
      </div>
    </div>
  </main>

<style>
  .sidebarContainer {
    display: flex;
    flex-direction: row;
  }

  .sidebar {
    flex: 250px 0 0;
    padding: 10px;
  }
  .results {
    flex: auto 1 1;
    position: relative;
  }

  input[name="textFilter"] {
    width: 100%;
    flex: auto 1 1;
    border: solid var(--border-color) 1px;
    border-radius: 16px;
    padding: 8px 8px 6px 12px;
    font-size: 1rem;
    background-color: var(--light-background);
    position: relative;
    display: block;
  }
  /* Add a X over the input */
  input[name="textFilter"]::before {
    content: "Where is this going?";
    width: 200px;
    height: 200px;
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    display: block;
  }

  @media (max-width: 800px) {
    .sidebarContainer {
      flex-direction: column;
    }
  }
  select {
    display: block;
    width: 100%;
    padding: 0.3rem 2.25rem 0.3rem 0.75rem;
    font-size: 1rem;
    line-height: 1.5;
    appearance: none;
    background-color: var(--light-background);
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    margin: 3px 0;
    float: left;
    background-image: var(--form-select-bg-img);
    background-repeat: no-repeat;
    background-position: right 0.75rem center;
    background-size: 16px 12px;
  }

  .selectWrapper {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 5px;
  }
  .selectWrapper > select {
    flex: auto 1 1;
  }
  .selectWrapper > div {
    flex: 0 0 20px;
    cursor: pointer;
  }
  .selectWrapper button, .textInputWrapper button {
    background: transparent;
    border: none;
    padding: 2px;
    font-size: 24px;
  }
  .textInputWrapper {
    position: relative;
    max-width: 600px;
    margin: 0 auto 10px auto;
  }
  .textInputWrapper button {
    position: absolute;
    right: 7px;
    top: -1px;
  }

  .sources {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 5px;
    max-width: 1330px;
    margin: 0 auto;
  }
  .filters {
    gap: 10px;
    margin: 5px 0;
  }
  main {
    flex: auto 1 1;
    overflow: scroll;
    width: 100%;
    display: flex;
    flex-direction: column;
    margin: auto;
  }

  .summary {
    z-index: 20;
    padding: 0 10px 10px 10px;
    flex: auto 0 0;
    position: relative;
  }
  .results h3 {
    margin: 10px;
  }
</style>
