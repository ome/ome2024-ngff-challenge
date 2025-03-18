import Papa from "papaparse";

import idrLogo from "/idr-mark.svg";
import nfdi4bioimage from "/nfdi4bioimage.png";
import ssbdLogo from "/ssbd-logo.png";

export const SAMPLES_HOME =
  "https://raw.githubusercontent.com/ome/ome2024-ngff-challenge/main/samples/ngff_samples.csv";

// Map of source to favicon domain
let faviconDomains = {
  IDR: "https://idr.openmicroscopy.org",
  Webknossos: "https://webknossos.org",
  JAX: "http://jax.org",
  "BioImage Archive": "https://www.ebi.ac.uk",
  Crick: "https://www.crick.ac.uk/",
  // Several sources from NFDI4Bioimage
  "University of Muenster": "https://nfdi4bioimage.de/",
  Göttingen: "https://nfdi4bioimage.de/",
  Jülich: "https://nfdi4bioimage.de/",
  NFDI4BIOIMAGE: "https://nfdi4bioimage.de/",
};

export function getSourceIcon(source) {
  if (source === "IDR") {
    return idrLogo;
  }
  if (source === "SSBD") {
    return ssbdLogo;
  }
  let domain = faviconDomains[source];
  if (!domain) {
    return null;
  }
  if (domain === "https://nfdi4bioimage.de/") {
    return nfdi4bioimage;
  }
  return `https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=${domain}&size=24`;
}

export function loadCsv(csvUrl, ngffTable, parentRow = {}) {
  // csvUrl = csvUrl + "?_=" + Date.now(); // prevent caching
  Papa.parse(csvUrl, {
    header: false,
    download: true,
    skipEmptyLines: "greedy",
    complete: function (results) {
      // We add the zarr URLs to the table and load any child CSVs
      // Each row in the table is a dict. {'url': 'https://path/to/data.zarr'}

      // Either we have single column with URLs or we have multiple columns
      let colNames = ["url"];
      let firstRow = results.data[0];
      if (firstRow.length > 1) {
        colNames = firstRow;
        results.data.shift(); // remove header row
      }
      let dataRows = results.data.map((row) => {
        // return a dict with column names as keys, overwriting parentRow
        let rowObj = { ...parentRow };
        for (let i = 0; i < colNames.length; i++) {
          rowObj[colNames[i]] = row[i];
        }
        return rowObj;
      });
      // we assume all urls except ".csv" are zarrs. (don't NEED to contain ".zarr")
      let zarrUrlRows = dataRows.filter((row) => !row["url"]?.endsWith(".csv"));
      // avoid duplicate urls
      let zarrRowsByUrl = {};
      zarrUrlRows.forEach((row) => {
        if (zarrRowsByUrl[row["url"]]) {
          console.warn("Removing duplicate URL:", row["url"]);
          return;
        }
        zarrRowsByUrl[row["url"]] = row;
      });
      zarrUrlRows = Object.values(zarrRowsByUrl);

      // recursively load child CSVs
      let childCsvRows = dataRows.filter((row) => row["url"]?.includes(".csv"));

      // register the csv in our hierarchy
      let plate_count = zarrUrlRows.reduce(
        (acc, row) => (row["wells"] ? acc + 1 : acc),
        0,
      );
      let bytes = zarrUrlRows.reduce(
        (acc, row) => acc + parseInt(row["written"] || 0),
        0,
      );
      let image_count = zarrUrlRows.length;
      if (plate_count > 0) {
        image_count = zarrUrlRows.reduce(
          (acc, row) => acc + parseInt(row["images"] || 1),
          0,
        );
      }
      ngffTable.addCsv(csvUrl, childCsvRows, image_count, plate_count, bytes);

      // add rows to the table - parsing strings to numbers etc...
      ngffTable.addRows(zarrUrlRows);

      childCsvRows.forEach((childCsvRow) => {
        let csvUrl = childCsvRow["url"];
        // childCsvRow["url"] = undefined;
        childCsvRow["csv"] = csvUrl;
        // Only load a single child CSV
        loadCsv(csvUrl, ngffTable, childCsvRow);
      });
    },
  });
}

export async function getJson(url) {
  return await fetch(url).then((rsp) => rsp.json());
}

export function getRandomInt(max) {
  return Math.floor(Math.random() * max);
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

export function range(start, end) {
  // range(5, 10) -> [5, 6, 7, 8, 9]
  return Array.from({ length: end - start }, (_, i) => i + start);
}
