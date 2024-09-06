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
        // Each row in the table is a dict. {'url': 'https://path/to/data.zarr'}
        let zarrUrlRows = results.data.filter((row) => row[0].includes(".zarr")).map(row => {return {url: row[0]}});
        let childCsvRows = results.data.filter((row) => row[0].includes(".csv"));
        ngffTable.addRows(zarrUrlRows);
        // recursively load child CSVs
        childCsvRows.forEach((childCsvUrl) => {
          loadCsv(childCsvUrl[0]);
        });
      },
    });
  }

  // kick off loading the CSV...
  if (csvUrl) {
    loadCsv(csvUrl);
  }

  function filesizeformat (bytes) {
    /*
    Formats the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB,
    102 bytes, etc).*/

    if (!bytes) return '';

    const round = 2;

    if (bytes < 1024) {
        return bytes + ' B';
    } else if (bytes < (1024*1024)) {
        return (bytes / 1024).toFixed(round) + ' KB';
    } else if (bytes < (1024*1024*1024)) {
        return (bytes / (1024*1024)).toFixed(round) + ' MB';
    } else if (bytes < (1024*1024*1024*1024)) {
        return (bytes / (1024*1024*1024)).toFixed(round) + ' GB';
    } else if (bytes < (1024*1024*1024*1024*1024)) {
        return (bytes / (1024*1024*1024*1024)).toFixed(round) + ' TB';
    } else {
        return (bytes / (1024*1024*1024*1024*1024)).toFixed(round) + ' PB';
    }
  };

  function linkText(url) {
    return url.replace("https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/", "");
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
        <th></th>
        <th></th>
        <th></th>
        <th></th>
        <th colspan="2">Bytes written</th>
      </tr>
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
          <td><a href="https://deploy-preview-36--ome-ngff-validator.netlify.app/?source={row.url}" target="_blank">{linkText(row.url)}</a></td>
          <td>{row.shape || ""}</td>
          <td>{row.well_count || ""}</td>
          <td>{row.well_count ? row.well_count * row.field_count : ""}</td>
          <td>{filesizeformat(row.written)}</td>
          <td>{filesizeformat(row.written * (row.well_count ? row.well_count * row.field_count : 1))}</td>
        </tr>
      {/each}
    </tbody>
</main>

<style>

</style>
