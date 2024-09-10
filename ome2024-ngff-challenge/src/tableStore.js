import { writable, get } from "svelte/store";

async function loadMultiscales(url) {
  let zarrData = await fetch(`${url}/zarr.json`).then((response) =>
    response.json(),
  );

  const attributes = zarrData?.attributes?.ome;
  if (!attributes) {
    return undefined;
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
      rows.forEach((row) => {
        this.loadNgffMetadata(row.url);
      });
      table.push(...rows);
      return table;
    });
  }

  populateRow(zarrUrl, rowValues) {
    this.store.update((table) => {
      table = table.map((row) => {
        if (row.url === zarrUrl) {
          row = { url: zarrUrl, ...rowValues };
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
      return;
    }
    // The data that is added to the Table
    const total_written = written * (well_count ? well_count * field_count : 1);
    this.populateRow(zarrUrl, {
      shape,
      written,
      well_count,
      field_count,
      total_written,
    });
  }

  subscribe(run) {
    return this.store.subscribe(run);
  }
}

export const ngffTable = new NgffTable();
