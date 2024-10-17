import Papa from "papaparse";

import idrLogo from "/idr-mark.svg";
import nfdi4bioimage from "/nfdi4bioimage.png";

export const SAMPLES_HOME =
  "https://raw.githubusercontent.com/will-moore/ome2024-ngff-challenge/hierarchy_browser/samples/ngff_samples.csv";

// Map of source to favicon domain
let faviconDomains = {
  IDR: "https://idr.openmicroscopy.org",
  Webknossos: "https://scalableminds.com",
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
      ngffTable.addCsv(csvUrl, childCsvRows, zarrUrlRows.length);

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

export function renderTo8bitArray(ndChunks, minMaxValues, colors) {
  // Render chunks (array) into 2D 8-bit data for new ImageData(arr)
  // ndChunks is list of zarr arrays

  // assume all chunks are same shape
  const shape = ndChunks[0].shape;
  const height = shape[0];
  const width = shape[1];
  const pixels = height * width;

  if (!minMaxValues) {
    minMaxValues = ndChunks.map(getMinMaxValues);
  }

  // let rgb = [255, 255, 255];
  let start = performance.now();

  let rgba = new Uint8ClampedArray(4 * height * width).fill(0);
  let offset = 0;
  for (let y = 0; y < pixels; y++) {
    for (let p = 0; p < ndChunks.length; p++) {
      let rgb = colors[p];
      let data = ndChunks[p].data;
      let range = minMaxValues[p];
      let rawValue = data[y];
      let fraction = (rawValue - range[0]) / (range[1] - range[0]);
      // for red, green, blue,
      for (let i = 0; i < 3; i++) {
        // rgb[i] is 0-255...
        let v = (fraction * rgb[i]) << 0;
        // increase pixel intensity if value is higher
        rgba[offset * 4 + i] = Math.max(rgba[offset * 4 + i], v);
      }
    }
    rgba[offset * 4 + 3] = 255; // alpha
    offset += 1;
  }
  // if iterating pixels is fast, check histogram and boost contrast if needed
  // Thumbnails are less than 5 millisecs. 512x512 is 10-20 millisecs.
  if (performance.now() - start < 100) {
    let hist = getHistogram(rgba, 5);
    if (hist[4] < 1) {
      // If few pixels in top bin, boost contrast
      rgba = boostContrast(rgba, 2);
    }
  }
  return rgba;
}

function boostContrast(rgba, factor) {
  // Increase contrast by factor
  for (let pixel = 0; pixel < rgba.length / 4; pixel++) {
    for (let i = 0; i < 3; i++) {
      let v = rgba[pixel * 4 + i];
      v = Math.min(255, v * factor);
      rgba[pixel * 4 + i] = v;
    }
  }
  return rgba;
}

function getHistogram(uint8array, bins = 5) {
  // Create histogram from uint8array
  let hist = new Array(bins).fill(0);
  const binSize = 256 / bins;
  let pixelCount = uint8array.length / 4;
  for (let i = 0; i < pixelCount; i++) {
    let maxV = uint8array[i * 4];
    maxV = Math.max(uint8array[i * 4 + 1], maxV);
    maxV = Math.max(uint8array[i * 4 + 2], maxV);
    let bin = Math.floor(maxV / binSize);
    hist[bin] += 1;
  }
  // Normalize
  hist = hist.map((v) => (100 * v) / pixelCount);
  return hist;
}

export function getMinMaxValues(chunk2d) {
  const data = chunk2d.data;
  let maxV = 0;
  let minV = Infinity;
  let length = chunk2d.data.length;
  for (let y = 0; y < length; y++) {
    let rawValue = data[y];
    maxV = Math.max(maxV, rawValue);
    minV = Math.min(minV, rawValue);
  }
  return [minV, maxV];
}

export const MAX_CHANNELS = 4;
export const COLORS = {
  cyan: "#00FFFF",
  yellow: "#FFFF00",
  magenta: "#FF00FF",
  red: "#FF0000",
  green: "#00FF00",
  blue: "#0000FF",
  white: "#FFFFFF",
};
export const MAGENTA_GREEN = [COLORS.magenta, COLORS.green];
export const RGB = [COLORS.red, COLORS.green, COLORS.blue];
export const CYMRGB = Object.values(COLORS).slice(0, -2);

export function getDefaultVisibilities(n) {
  let visibilities;
  if (n <= MAX_CHANNELS) {
    // Default to all on if visibilities not specified and less than 6 channels.
    visibilities = Array(n).fill(true);
  } else {
    // If more than MAX_CHANNELS, only make first set on by default.
    visibilities = [
      ...Array(MAX_CHANNELS).fill(true),
      ...Array(n - MAX_CHANNELS).fill(false),
    ];
  }
  return visibilities;
}

export function getDefaultColors(n, visibilities) {
  let colors = [];
  if (n == 1) {
    colors = [COLORS.white];
  } else if (n == 2) {
    colors = MAGENTA_GREEN;
  } else if (n === 3) {
    colors = RGB;
  } else if (n <= MAX_CHANNELS) {
    colors = CYMRGB.slice(0, n);
  } else {
    // Default color for non-visible is white
    colors = Array(n).fill(COLORS.white);
    // Get visible indices
    const visibleIndices = visibilities.flatMap((bool, i) => (bool ? i : []));
    // Set visible indices to CYMRGB colors. visibleIndices.length === MAX_CHANNELS from above.
    for (const [i, visibleIndex] of visibleIndices.entries()) {
      colors[visibleIndex] = CYMRGB[i];
    }
  }
  return colors.map(hexToRGB);
}

export function hexToRGB(hex) {
  if (hex.startsWith("#")) hex = hex.slice(1);
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  return [r, g, b];
}
