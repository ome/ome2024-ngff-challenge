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

  console.log("csvUrl", csvUrl);

  let tableRows = [];

  ngffTable.subscribe((rows) => {
    tableRows = rows;
  });

  if (csvUrl) {
      // load csv and use this for the left side of the table...
      Papa.parse(csvUrl, {
        header: false,
        download: true,
        complete: function (results) {
          console.log("Finished:", results.data);
          ngffTable.addRows(results.data);

          // test: add some rows after 5 seconds
          // setTimeout(() => {
          //   ngffTable.addRows(["row1", "row2", "row3"]);
          // }, 5000);
        },
      });
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
