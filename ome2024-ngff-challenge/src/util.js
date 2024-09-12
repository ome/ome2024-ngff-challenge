import Papa from "papaparse";

// singleton table store
import { ngffTable } from "./tableStore";

export function loadCsv(csvUrl) {
  console.log("loadCsv", csvUrl);

  Papa.parse(csvUrl, {
    header: false,
    download: true,
    skipEmptyLines: "greedy",
    complete: function (results) {
      console.log("Finished:", results.data);
      // We add the zarr URLs to the table and load any child CSVs
      // Each row in the table is a dict. {'url': 'https://path/to/data.zarr'}

      // Either we have single column with URLs or we have multiple columns
      let colNames = ["url"];
      let firstRow = results.data[0];
      if (firstRow.length > 1) {
        colNames = firstRow;
      }
      let dataRows = results.data.map((row) => {
        // return a dict with column names as keys
        let rowObj = {};
        for (let i = 0; i < colNames.length; i++) {
          rowObj[colNames[i]] = row[i];
        }
        return rowObj;
      });
      console.log("dataRows", dataRows);
      let zarrUrlRows = dataRows.filter((row) => row["url"].includes(".zarr"));
      let childCsvRows = dataRows.filter((row) => row["url"].includes(".csv"));
      ngffTable.addRows(zarrUrlRows);
      // recursively load child CSVs
      childCsvRows.forEach((childCsvUrl) => {
        loadCsv(childCsvUrl["url"]);
      });
    },
  });
}

export async function getJson(url) {
  return await fetch(url).then((rsp) => rsp.json());
}

export async function lookupOrganism(taxonId) {
  // taxonId e.g. NCBI:txid9606
  let id = taxonId.replace("NCBI:txid", "");
  const orgJson = await getJson(
    `https://rest.ensembl.org/taxonomy/id/${id}?content-type=application/json`,
  );
  return orgJson.name || taxonId;
}

export async function lookupImagingModality(fbbiId) {
  // fbbiId e.g. obo:FBbi_00000246
  // http://purl.obolibrary.org/obo/FBbi_00000246
  // https://www.ebi.ac.uk/ols4/api/ontologies/fbbi/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FFBbi_00000246
  const fbbi_id = fbbiId.replace("obo:", "");
  const methodJson = await getJson(
    `https://www.ebi.ac.uk/ols4/api/ontologies/fbbi/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F${fbbi_id}`,
  );
  return methodJson.label;
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
