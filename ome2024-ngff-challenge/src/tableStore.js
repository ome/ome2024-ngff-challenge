import { writable, get } from "svelte/store";
import { range } from "./util.js";
const BATCH_SIZE = 5;

export async function loadMultiscales(url) {
  // return the json data that includes multiscales
  let zarrData = await fetch(`${url}/zarr.json`)
    .then((response) => {
      if (response.status === 404) {
        throw new Error(`${url}/zarr.json not found`);
      }
      return response.json();
    })
    .catch((error) => {
      return [undefined, url];
    });

  const attributes = zarrData?.attributes?.ome;
  if (!attributes) {
    return [undefined, url];
  }
  if (attributes.multiscales) {
    return [attributes, url];
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

    // [{source: "uni1",
    //  url: "http://...csv",
    //  image_count: 10,
    //  "child_csv": [{source: "uni2", url: "http://...csv"}]}
    // ]
    this.csvFiles = [];
  }

  getCsvSourceList(sourceName) {
    let child;
    if (!sourceName) {
      child = this.csvFiles[0];
    } else {
      for (let csv of this.csvFiles) {
        if (csv.source === sourceName) {
          child = csv;
          break;
        }
        for (let childCsv of csv.child_csv) {
          if (childCsv.source === sourceName) {
            child = childCsv;
            break;
          }
          for (let grandchildCsv of childCsv.child_csv) {
            if (grandchildCsv.source === sourceName) {
              child = grandchildCsv;
              break;
            }
          }
        }
      }
    }
    if (!child) {
      return [];
    }
    // lets summarise the image_count for each source
    let children = child.child_csv.map((src) => {
      let count = src.image_count || 0;
      for (let grandchild of src.child_csv) {
        // not recursive but OK for now
        count += grandchild.image_count || 0;
      }
      return { ...src, total_count: count };
    });
    return children;
  }

  addCsv(csvUrl, childCsvRows, zarrUrlRowCount) {
    // childCsvRows is [{source: "uni2", url: "http://...csv"}]
    // make shallow copy of childCsvRows
    childCsvRows = childCsvRows.map((row) => ({ ...row, child_csv: [] }));
    // find the child_csv with the same url
    let child;
    for (let csv of this.csvFiles) {
      if (csv.url === csvUrl) {
        child = csv;
        break;
      }
      for (let childCsv of csv.child_csv) {
        if (childCsv.url === csvUrl) {
          child = childCsv;
          break;
        }
        for (let grandchildCsv of childCsv.child_csv) {
          if (grandchildCsv.url === csvUrl) {
            child = grandchildCsv;
            break;
          }
        }
      }
    }
    if (child) {
      // add to the existing child
      child.image_count = zarrUrlRowCount;
      child.child_csv = childCsvRows;
    } else {
      child = {
        url: csvUrl,
        image_count: zarrUrlRowCount,
        child_csv: childCsvRows,
      };
      this.csvFiles.push(child);
    }
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
        // count the number of dimensions with size > 1
        row.dim_count = shape.reduce(
          (prev, curr) => prev + (curr > 1 ? 1 : 0),
          0,
        );
      }
      return row;
    });

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

    // Handle number...
    if (isNumber) {
      if (aVal === undefined) {
        aVal = 0;
      }
      if (bVal === undefined) {
        bVal = 0;
      }
      if (aVal < bVal) {
        return this.sortAscending ? -1 : 1;
      } else if (aVal > bVal) {
        return this.sortAscending ? 1 : -1;
      }
      return 0;
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

  getRows() {
    return get(this.store);
  }
}

export const ngffTable = new NgffTable();
