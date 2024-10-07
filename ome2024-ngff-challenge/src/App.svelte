<script>
  import { ngffTable } from "./tableStore";
  import ThumbGallery from "./ThumbGallery.svelte";
  import Thumbnail from "./Thumbnail.svelte";
  import Pixel from "./Pixel.svelte";
  import ColumnSort from "./ColumnSort.svelte";

  import { SAMPLES_HOME, filesizeformat, loadCsv, lookupImagingModality, lookupOrganism } from "./util";
  import Nav from "./Nav.svelte";


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
      imagingModalityLookup = { ...imagingModalityLookup, [fbbiId]: imagingModality };
    });
    return fbbiId;
  }

  let sortedBy = "";
  let sortAscending = true;
  function handleSort(colname) {
    console.log("handleSort", colname, 'sortedBy', sortedBy);
    if (sortedBy === colname) {
      sortAscending = !sortAscending;
    } else {
      sortAscending = true;
    }
    sortedBy = colname;
    ngffTable.sortTable(colname, sortAscending);
  }
</script>

<Pixel/><Pixel/><Pixel/><Pixel/><Pixel/>
<Pixel/><Pixel/><Pixel/><Pixel/><Pixel/>

<Nav/>

<main>
  <h1 class="title">OME 2024 NGFF Challenge</h1>

  <ThumbGallery {csvUrl} />

  <div class="summary">
    <table>
      <tr>
        <td>Zarr Samples (URLs)</td>
        <td>Images</td>
        <td>Bytes written</td>
        <td>Organisms</td>
      </tr>
      <tr class="stats">
        <td>{tableRows.length}</td>
        <td
          >{tableRows.reduce(
            (acc, row) =>
              acc + (row.well_count ? row.well_count * row.field_count : 1),
            0
          )}</td
        >
        <td
          >{filesizeformat(
            tableRows.reduce((acc, row) => {
              return acc + parseInt(row["written"]) || 0;
            }, 0)
          )}</td
        >
        <td>
          {#if showLoadRoCrateButton}
            <button class="loadrocrate" on:click={handleLoadRocrate}>Load Ro-Crate metadata</button>
          {:else}
            {Object.keys(organismLookup).length}
          {/if}
        </td>
      </tr>
    </table>

    <progress value={tableRows.filter(row => row.loaded).length} max={tableRows.length}></progress>
  </div>

  <table>
    <thead>
      <tr>
        <th>Thumb</th>
        <th><ColumnSort col_label={"Url"} col_name={"url"} {handleSort} {sortedBy} {sortAscending}/></th>
        {#if showSourceColumn}
          <th><ColumnSort col_label={"Source"} col_name={"source"} {handleSort} {sortedBy} {sortAscending}/></th>
        {/if}
        {#if showOriginColumn}
          <th>Data Origin</th>
        {/if}
        <th>Shape</th>
        <th><ColumnSort col_label={"X"} col_name={"size_x"} {handleSort} {sortedBy} {sortAscending}/></th>
        <th><ColumnSort col_label={"Y"} col_name={"size_y"} {handleSort} {sortedBy} {sortAscending}/></th>
        <th><ColumnSort col_label={"Z"} col_name={"size_z"} {handleSort} {sortedBy} {sortAscending}/></th>
        <th><ColumnSort col_label={"C"} col_name={"size_c"} {handleSort} {sortedBy} {sortAscending}/></th>
        <th><ColumnSort col_label={"T"} col_name={"size_t"} {handleSort} {sortedBy} {sortAscending}/></th>
        <th><ColumnSort col_label={"Data size"} col_name={"written"} {handleSort} {sortedBy} {sortAscending}/></th>
        {#if showPlateColumns}
          <th><ColumnSort col_label={"Wells"} col_name={"well_count"} {handleSort} {sortedBy} {sortAscending}/></th>
          <th>Images</th>
        {/if}
        <th>Organism</th>
        <th>Imaging</th>
      </tr>
    </thead>
    <tbody>
      {#each tableRows as row (row.url)}
        <tr>
          <td>

          </td>
          <td
            >
            {#if row.csv_row_count && row.csv}
              <a
                href="{window.location.origin}?csv={row.csv}"
                target="_blank"
                >{row.csv.split("/").pop()} ({row.csv_row_count})</a
              >
            {:else}
              <a
                href="https://deploy-preview-36--ome-ngff-validator.netlify.app/?source={row.url}"
                target="_blank">{linkText(row.url)}</a
              >
            {/if}
            </td
          >
          {#if showSourceColumn}
            <td>{row.source || ""}</td>
          {/if}
          {#if showOriginColumn}
            <td>
              {#if row.origin}<a href={row.origin} target="_blank">...{row.origin.slice(-10)}</a>{/if}
            </td>
          {/if}
          <td>{row.shape || ""}</td>
          <td>{row.size_x || ""}</td>
          <td>{row.size_y || ""}</td>
          <td>{row.size_z || ""}</td>
          <td>{row.size_c || ""}</td>
          <td>{row.size_t || ""}</td>
          <td>{filesizeformat(row.written)}</td>
          {#if showPlateColumns}
            <td>{row.well_count || ""}</td>
            <td>{row.well_count ? row.well_count * row.field_count : ""}</td>
          {/if}
          <td title="{row.organism_id || ''}">
            {#if row.organism_id}
              {organismLookup[row.organism_id] || loadOrganism(row.organism_id)}
            {/if}
          </td>
          <td title="{row.fbbi_id || ''}">
            {#if row.fbbi_id}
              {organismLookup[row.fbbi_id] || loadImagingModality(row.fbbi_id)}
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</main>

<style>

  .title {
    z-index: 10;
    position: relative;
    margin-bottom: 10px;
  }
  .summary {
    margin-bottom: 2em;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    background-color: white;
    position: relative;
    z-index: 10;
    -webkit-box-shadow: 7px 6px 20px -8px rgba(115,115,115,1);
    -moz-box-shadow: 7px 6px 20px -8px rgba(115,115,115,1);
    box-shadow: 7px 6px 20px -8px rgba(115,115,115,1);
  }
  @media (prefers-color-scheme: dark) {
    table {
      background-color: #333;
    }
  }

  td, th {
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

  .loadrocrate {
    font-size: 12px;
    background-color:aliceblue;
    border-radius: 5px;
    border-color: coral;
    vertical-align: middle;
    margin-bottom: 7px;
    color: #222;
  }
</style>
