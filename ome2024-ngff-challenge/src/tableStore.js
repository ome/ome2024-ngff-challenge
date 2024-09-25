import { writable, get } from "svelte/store";
import { range } from "./util.js";
const BATCH_SIZE = 5;

async function loadMultiscales(url) {
  let zarrData = await fetch(`${url}/zarr.json`)
    .then((response) => {
      console.log("loadMultiscales response", response.status);
      if (response.status === 404) {
        throw new Error(`${url}/zarr.json not found`);
      }
      return response.json();
    })
    .catch((error) => {
      console.log("----> Failed to load zarr.json", error);
      return [undefined, url];
    });

  const attributes = zarrData?.attributes?.ome;
  if (!attributes) {
    return [undefined, url];
  }
  if (attributes.multiscales) {
    return [attributes.multiscales, url];
  } else if (attributes.plate) {
    let well = attributes.plate.wells[0];
    // assume the first image in the well is under "/0"
    let imgPath = `${url}/${well.path}/0`;
    let [msData, msUrl] = await loadMultiscales(imgPath);
    return [msData, msUrl, attributes.plate];
  } else if (attributes["bioformats2raw.layout"]) {
    let bf2rawUrl = `${url}/0`;
    return await loadMultiscales(bf2rawUrl);
  }
}

class NgffTable {
  constructor() {
    this.store = writable([]);
  }

  addRows(rows) {
    // Each row is a dict {"url": "http...zarr"}
    this.store.update((table) => {
      table.push(...rows);
      // Load metadata for each row - 5 at a time
      async function loadMetadata(rows) {
        for (let i = 0; i < rows.length; i = i + BATCH_SIZE) {
          let promises = range(i, Math.min(i + BATCH_SIZE, rows.length)).map(
            (j) => {
              return this.loadNgffMetadata(rows[j].url);
            },
          );
          await Promise.all(promises);
        }
      }
      loadMetadata.bind(this)(rows);
      return table;
    });
  }

  populateRow(zarrUrl, rowValues) {
    this.store.update((table) => {
      table = table.map((row) => {
        if (row.url === zarrUrl) {
          row = { ...row, ...rowValues };
          console.log("populateRow", rowValues, row);
        }
        return row;
      });
      return table;
    });
  }

  async loadNgffMetadata(zarrUrl) {
    const [multiscales, msUrl, plate] = await loadMultiscales(zarrUrl);
    let shape = [];
    let written = 0;
    let well_count = 0;
    let field_count = 0;
    let load_failed = false;
    let loaded = true;
    // TODO: include 'omero' attrs for rendering settings
    let image_attrs = { multiscales };
    let image_url = msUrl;
    if (plate) {
      well_count = plate.wells.length;
      field_count = plate.field_count || 1;
    }
    if (multiscales) {
      // only consider the first multiscale and load highest resolution dataset
      const dataset = multiscales[0]?.datasets[0];
      const path = dataset?.path;
      if (path) {
        const arrayData = await fetch(`${msUrl}/${path}/zarr.json`).then(
          (response) => response.json(),
        );
        shape = arrayData?.shape;
        written = arrayData?.attributes?._ome2024_ngff_challenge_stats?.written;
      }
    } else {
      console.log("No multiscales found");
      load_failed = true;
      shape = [0];
    }
    // The data that is added to the Table
    const total_written = written * (well_count ? well_count * field_count : 1);
    this.populateRow(zarrUrl, {
      image_attrs,
      image_url,
      shape,
      written,
      well_count,
      field_count,
      total_written,
      load_failed,
      loaded, // always true - just means we tried to load the data
    });
  }

  async loadRocrateJson(zarrUrl) {
    await fetch(`${zarrUrl}/ro-crate-metadata.json`)
      .then((response) => {
        console.log("loadMultiscales response", response.status);
        if (response.status === 404) {
          throw new Error(`${zarrUrl}/ro-crate-metadata.json not found`);
        }
        return response.json();
      })
      .then((jsonData) => {
        // parse ro-crate json...
        let biosample = jsonData["@graph"].find(
          (item) => item["@type"] === "biosample",
        );
        let organism_id = biosample?.organism_classification?.["@id"];
        let image_acquisition = jsonData["@graph"].find(
          (item) => item["@type"] === "image_acquisition",
        );
        let fbbi_id = image_acquisition?.fbbi_id?.["@id"];

        // I guess we could store more JSON data in the table, but let's keep columns to strings/IDs for now...
        this.populateRow(zarrUrl, {
          organism_id,
          fbbi_id,
          rocrate_loaded: true,
        });
      })
      .catch((error) => {
        console.log("Failed to load ro-crate-metadata.json", error);
      });
  }

  async loadRocrateJsonAllRows() {
    let rows = get(this.store);
    for (let i = 0; i < rows.length; i = i + BATCH_SIZE) {
      let promises = range(i, Math.min(i + BATCH_SIZE, rows.length)).map(
        (j) => {
          return this.loadRocrateJson(rows[j].url);
        },
      );
      await Promise.all(promises);
    }
  }

  compareRows(a, b) {
    let aVal = a[this.sortColumn];
    let bVal = b[this.sortColumn];
    if (aVal === undefined) {
      aVal = "";
    }
    if (bVal === undefined) {
      bVal = "";
    }

    let comp = 0;
    // TODO: handle specific column names, e.g. shape
    if (typeof aVal === "number") {
      comp = aVal - bVal;
    } else {
      comp = aVal.localeCompare(bVal);
    }
    return this.sortAscending ? comp : -comp;
  }

  sortTable(colName, ascending = true) {
    this.sortColumn = colName;
    this.sortAscending = ascending;
    this.store.update((table) => {
      table.sort((a, b) => this.compareRows(a, b));
      return table;
    });
  }

  emptyTable() {
    this.store.set([]);
  }

  subscribe(run) {
    return this.store.subscribe(run);
  }
}

export const ngffTable = new NgffTable();
