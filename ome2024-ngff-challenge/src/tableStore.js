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
      console.log(`----> Failed to load ${url}/zarr.json`, error);
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
    rows = rows.map((row) => {
      if (row.written) {
        row.written = parseFloat(row.written);
      }
      if (row.shape) {
        let shape = row.shape.split(",").map((dim) => parseInt(dim));
        let dim_names;
        if (row.dimension_names) {
          // e.g "t,c,z,y,x"
          dim_names = row.dimension_names.split(",");
        } else if (shape.length == 5) {
          dim_names = ["t", "c", "z", "y", "x"];
        }
        if (dim_names && dim_names.length == shape.length) {
          dim_names.forEach((dim, idx) => (row["size_" + dim] = shape[idx]));
        }
      }
      return row;
    });
    console.log("addRows", rows);

    this.store.update((table) => {
      table.push(...rows);
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
        const arrayData = await fetch(`${msUrl}/${path}/zarr.json`)
          .then((response) => response.json())
          .catch((error) => {
            console.log(
              `----> Failed to parse ${msUrl}/${path}/zarr.json`,
              error,
            );
          });
        shape = arrayData?.shape;
        // written = arrayData?.attributes?._ome2024_ngff_challenge_stats?.written;
      }
    } else {
      console.log("No multiscales found");
      load_failed = true;
      shape = [0];
    }
    // The data that is added to the Table
    // const total_written = written * (well_count ? well_count * field_count : 1);
    this.populateRow(zarrUrl, {
      image_attrs,
      image_url,
      shape,
      // written,
      well_count,
      field_count,
      // total_written,
      load_failed,
      loaded, // always true - just means we tried to load the data
    });
  }

  // async loadRocrateJson(zarrUrl) {
  //   await fetch(`${zarrUrl}/ro-crate-metadata.json`)
  //     .then((response) => {
  //       console.log("loadMultiscales response", response.status);
  //       if (response.status === 404) {
  //         throw new Error(`${zarrUrl}/ro-crate-metadata.json not found`);
  //       }
  //       return response.json();
  //     })
  //     .then((jsonData) => {
  //       // parse ro-crate json...
  //       let biosample = jsonData["@graph"].find(
  //         (item) => item["@type"] === "biosample",
  //       );
  //       let organism_id = biosample?.organism_classification?.["@id"];
  //       let image_acquisition = jsonData["@graph"].find(
  //         (item) => item["@type"] === "image_acquisition",
  //       );
  //       let fbbi_id = image_acquisition?.fbbi_id?.["@id"];

  //       // I guess we could store more JSON data in the table, but let's keep columns to strings/IDs for now...
  //       this.populateRow(zarrUrl, {
  //         organism_id,
  //         fbbi_id,
  //         rocrate_loaded: true,
  //       });
  //     })
  //     .catch((error) => {
  //       console.log("Failed to load ro-crate-metadata.json", error);
  //     });
  // }

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

  compareRows(a, b, isNumber = false) {
    let aVal = a[this.sortColumn];
    let bVal = b[this.sortColumn];

    // try to make it fast by not checking for undefined etc
    if (isNumber) {
      return this.sortAscending ? aVal - bVal : -bVal - aVal;
    }

    if (aVal === undefined) {
      aVal = "";
    }
    if (bVal === undefined) {
      bVal = "";
    }

    let comp = 0;
    // TODO: handle specific column names, e.g. shape
    if (isNumber) {
      comp = aVal - bVal;
    } else {
      comp = aVal.localeCompare(bVal);
    }
    return this.sortAscending ? comp : -comp;
  }

  sortTable(colName, ascending = true) {
    this.sortColumn = colName;
    this.sortAscending = ascending;
    let isNumber = this.isColumnNumeric(colName);
    console.log(
      "sortTable",
      colName,
      "ascending",
      ascending,
      "isNumber",
      isNumber,
    );
    this.store.update((table) => {
      table.sort((a, b) => this.compareRows(a, b, isNumber));
      return table;
    });
  }

  isColumnNumeric(colName) {
    // return true if first non-empty value is a number
    let rows = get(this.store);
    for (let row of rows) {
      let val = row[colName];
      if (val !== undefined && val !== "") {
        return !isNaN(val);
      }
    }
  }

  emptyTable() {
    this.store.set([]);
  }

  subscribe(run) {
    return this.store.subscribe(run);
  }
}

export const ngffTable = new NgffTable();
