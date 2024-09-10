<script>
  import { ngffTable } from "./tableStore";

  import { filesizeformat, loadCsv } from "./util";

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
    return url.replace(
      "https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/",
      ""
    );
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
        <th>per Image</th>
        <th>total</th>
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
  td {
    border: lightgrey 1px solid;
    padding: 0.5em;
  }
  .stats {
    font-size: 48px;
  }
</style>
