import Papa from "papaparse";

// singleton table store
import { ngffTable } from "./tableStore";

export function loadCsv(csvUrl) {
  console.log("loadCsv", csvUrl);

  Papa.parse(csvUrl, {
    header: false,
    download: true,
    complete: function (results) {
      console.log("Finished:", results.data);
      // We add the zarr URLs to the table and load any child CSVs
      // Each row in the table is a dict. {'url': 'https://path/to/data.zarr'}
      let zarrUrlRows = results.data
        .filter((row) => row[0].includes(".zarr"))
        .map((row) => {
          return { url: row[0] };
        });
      let childCsvRows = results.data.filter((row) => row[0].includes(".csv"));
      ngffTable.addRows(zarrUrlRows);
      // recursively load child CSVs
      childCsvRows.forEach((childCsvUrl) => {
        loadCsv(childCsvUrl[0]);
      });
    },
  });
}

export function filesizeformat(bytes) {
  /*
  Formats the value like a 'human-readable' file size (i.e. 13 KB, 4.1 MB,
  102 bytes, etc).*/

  if (!bytes) return "";

  const round = 2;

  if (bytes < 1024) {
    return bytes + " B";
  } else if (bytes < 1024 * 1024) {
    return (bytes / 1024).toFixed(round) + " KB";
  } else if (bytes < 1024 * 1024 * 1024) {
    return (bytes / (1024 * 1024)).toFixed(round) + " MB";
  } else if (bytes < 1024 * 1024 * 1024 * 1024) {
    return (bytes / (1024 * 1024 * 1024)).toFixed(round) + " GB";
  } else if (bytes < 1024 * 1024 * 1024 * 1024 * 1024) {
    return (bytes / (1024 * 1024 * 1024 * 1024)).toFixed(round) + " TB";
  } else {
    return (bytes / (1024 * 1024 * 1024 * 1024 * 1024)).toFixed(round) + " PB";
  }
}
