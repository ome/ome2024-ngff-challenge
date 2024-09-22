<script>
  import { ngffTable } from "./tableStore";

  import { filesizeformat, loadCsv, lookupImagingModality, lookupOrganism } from "./util";

  let showPlaceholder = false;

  // check for ?csv=url
  const params = new URLSearchParams(window.location.search);
  let csvUrl = params.get("csv");
  try {
    new URL(csvUrl);
  } catch (error) {
    showPlaceholder = true;
  }

  let tableRows = [];
  let organismLookup = {};
  let imagingModalityLookup = {};

  ngffTable.subscribe((rows) => {
    tableRows = rows;
  });

  // kick off loading the CSV...
  // This will recursively load other csv files if they are linked in the first one
  // and populate the ngffTable store
  if (csvUrl) {
    loadCsv(csvUrl);
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
    ngffTable.loadRocrateJson();
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

<main>
  <h1>OME 2024 NGFF Challenge</h1>

  {#if showPlaceholder}
    <p>
      Upload a CSV file of zarr URLs to get started:
      ?url=https://path/to/data.csv
    </p>
  {/if}

  <div class="summary">
    Totals:
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
            tableRows.reduce((acc, row) => acc + (row.total_written || 0), 0)
          )}</td
        >
        <td>
          {#if Object.keys(organismLookup).length === 0}
            <button on:click={handleLoadRocrate}>Load Ro-Crate metadata</button>
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
        <th>Url <button on:click={() => handleSort('url')}>sort {#if sortedBy == 'url'} {sortAscending ? "v" : "^"}{/if}</button></th>
        <th>Source</th>
        <th>Shape</th>
        <th>Wells <button on:click={() => handleSort('well_count')}>sort {#if sortedBy == 'well_count'} {sortAscending ? "v" : "^"} {/if}</button></th>
        <th>Images</th>
        <th>Image size <button on:click={() => handleSort('written')}>sort {#if sortedBy == 'written'} {sortAscending ? "v" : "^"} {/if}</button></th>
        <th>Total size <button on:click={() => handleSort('total_written')}>sort {#if sortedBy == 'total_written'} {sortAscending ? "v" : "^"} {/if}</button></th>
        <th>Organism</th>
        <th>Imaging</th>
      </tr>
    </thead>
    <tbody>
      {#each tableRows as row (row.url)}
        <tr>
          <td
            ><a
              href="https://deploy-preview-36--ome-ngff-validator.netlify.app/?source={row.url}"
              target="_blank">{linkText(row.url)}</a
            ></td
          >
          <td>{row.source || ""}</td>
          <td>{row.load_failed ? "x" : row.shape || ""}</td>
          <td>{row.well_count || ""}</td>
          <td>{row.well_count ? row.well_count * row.field_count : ""}</td>
          <td>{filesizeformat(row.written)}</td>
          <td>{filesizeformat(row.total_written)}</td>
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
  .summary {
    margin-bottom: 2em;
  }
  table {
    border-collapse: collapse;
    width: 100%;
  }
  td, th {
    border: lightgrey 1px solid;
    padding: 0.5em;
  }
  progress {
    width: 100%;
  }
  .stats {
    font-size: 48px;
  }

  button {
    font-size: 12px;
    background-color:aliceblue;
    border-radius: 5px;
    border-color: coral;
    vertical-align: middle;
    margin-bottom: 7px;
  }
</style>
