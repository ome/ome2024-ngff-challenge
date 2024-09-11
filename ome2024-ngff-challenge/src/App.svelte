<script>
  import { ngffTable } from "./tableStore";

  import { filesizeformat, loadCsv, lookupOrganism } from "./util";

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
  </div>

  <table>
    <thead>
      <tr>
        <th>Url</th>
        <th>Shape</th>
        <th>Wells</th>
        <th>Images</th>
        <th>Image size</th>
        <th>Total size</th>
        <th>Organism</th>
        <th>Imaging</th>
      </tr>
    </thead>
    <tbody>
      {#each tableRows as row}
        <tr>
          <td
            ><a
              href="https://deploy-preview-36--ome-ngff-validator.netlify.app/?source={row.url}"
              target="_blank">{linkText(row.url)}</a
            ></td
          >
          <td>{row.shape || ""}</td>
          <td>{row.well_count || ""}</td>
          <td>{row.well_count ? row.well_count * row.field_count : ""}</td>
          <td>{filesizeformat(row.written)}</td>
          <td>{filesizeformat(row.total_written)}</td>
          <td title="{row.organism_id || ''}">
            {#if row.organism_id}
              {organismLookup[row.organism_id] || loadOrganism(row.organism_id)}
            {/if}
          </td>
          <td>{row.fbbi_id || ""}</td>
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
