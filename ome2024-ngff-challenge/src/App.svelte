<script>
  import VirtualList from 'svelte-tiny-virtual-list';

  import { ngffTable } from "./tableStore";
  import ThumbGallery from "./ThumbGallery.svelte";
  import Thumbnail from "./Thumbnail.svelte";
  import ColumnSort from "./ColumnSort.svelte";

  import {
    SAMPLES_HOME,
    filesizeformat,
    loadCsv,
    lookupImagingModality,
    lookupOrganism,
  } from "./util";
  import Nav from "./Nav.svelte";
  import ZarrListItem from './ZarrListItem.svelte';

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
  let showSourceColumn = false;
  let organismLookup = {};
  let imagingModalityLookup = {};

  // The ngffTable is loaded initially - for gallery at top of page...
  // Also updated when a gallery item is clicked to show the table of images
  ngffTable.subscribe((rows) => {
    tableRows = rows;
  });

  $: showSourceColumn = tableRows.some((row) => row.source);
  $: showOriginColumn = tableRows.some((row) => row.origin);
  $: showPlateColumns = tableRows.some((row) => row.well_count);
  $: showLoadRoCrateButton = !tableRows.some((row) => row.rocrate_loaded);

  // kick off loading the CSV to populate ngffTable...
  // This will recursively load other csv files if they are linked in the first one
  if (csvUrl) {
    loadCsv(csvUrl, ngffTable);
  }

  function linkText(url) {
    let truncated = url.replace(
      "https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/",
      ""
    );
    if (truncated.length > 50) {
      truncated = truncated.slice(0, 20) + "..." + truncated.slice(-20);
    }
    return truncated;
  }

  function handleLoadRocrate() {
    ngffTable.loadRocrateJsonAllRows();
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

</script>

<div class="app">
  <Nav />

  <main>
    <h1 class="title">OME 2024 NGFF Challenge</h1>

    <ThumbGallery {csvUrl} />

    <div class="summary">
      <p>
        {tableRows.length} Zarrs,
        {filesizeformat(
          tableRows.reduce((acc, row) => {
            return acc + parseInt(row["written"]) || 0;
          }, 0)
        )},
        <span title={Object.values(organismLookup).join(",")}>
          {Object.keys(organismLookup).length} organisms
        </span>
      </p>
      <div>
        Filter:
        <button>IDR</button>
        <button>JAX</button>
        <button>EBI</button>
        <button>Webknossos</button>
      </div>
      <div><ColumnSort
              col_label={"Url"}
              col_name={"url"}
              {handleSort}
              {sortedBy}
              {sortAscending}
            />
          {#if showSourceColumn}
            <ColumnSort
                col_label={"Source"}
                col_name={"source"}
                {handleSort}
                {sortedBy}
                {sortAscending}
              />
          {/if}
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


<VirtualList width="100%" height={600} itemCount={tableRows.length} itemSize={150} getKey={getItemKey}>
	<div slot="item" let:index let:style {style} class="row">
		Row: #{index} URL: {tableRows[index].url}
    <ZarrListItem rowData={tableRows[index]} />
	</div>
</VirtualList>

  </main>
</div>

<style>
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
  table {
    border-collapse: collapse;
    width: 100%;
    background-color: white;
    position: relative;
    z-index: 0;
    -webkit-box-shadow: 7px 6px 20px -8px rgba(115, 115, 115, 1);
    -moz-box-shadow: 7px 6px 20px -8px rgba(115, 115, 115, 1);
    box-shadow: 7px 6px 20px -8px rgba(115, 115, 115, 1);
  }
  @media (prefers-color-scheme: dark) {
    table {
      background-color: #333;
    }
  }

  td,
  th {
    border: lightgrey 1px solid;
    padding: 0.5em;
    text-align: center;
  }
  progress {
    width: 100%;
  }
  .stats {
    font-size: 48px;
  }
</style>
