<script>

  import Papa from "papaparse";

  import {ngffTable} from "./tableStore";

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

  function loadCsv(csvUrl) {
    console.log("loadCsv", csvUrl);

    Papa.parse(csvUrl, {
      header: false,
      download: true,
      complete: function (results) {
        console.log("Finished:", results.data);
        // We add the zarr URLs to the table and load any child CSVs
        let zarrUrls = results.data.filter((row) => row[0].includes(".zarr"));
        let childCsvUrls = results.data.filter((row) => row[0].includes(".csv"));
        ngffTable.addRows(zarrUrls);
        // recursively load child CSVs
        childCsvUrls.forEach((childCsvUrl) => {
          loadCsv(childCsvUrl[0]);
        });
      },
    });
  }

  // kick off loading the CSV...
  if (csvUrl) {
    loadCsv(csvUrl);
  }
</script>

<main>
  <h1>OME 2024 NGFF Challenge</h1>

  {#if showPlaceholder}
    <p>Upload a CSV file of zarr URLs to get started: ?url=https://path/to/data.csv</p>
  {:else}
    Yey! You have a CSV file of zarr URLs. Let's get started!
  {/if}

  <table>
    <thead>
      <tr>
        <th>Column 1</th>
      </tr>
    </thead>
    <tbody>
      {#each tableRows as row}
        <tr>
          <td>{row}</td>
        </tr>
      {/each}
    </tbody>
</main>

<style>

</style>
