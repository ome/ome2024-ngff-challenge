import { writable, get } from "svelte/store";

class NgffTable {
  constructor() {
    this.store = writable([]);
  }

  addRows(rows) {
    this.store.update((table) => {
      rows.forEach((row) => {
        this.loadNgffMetadata(row[0]);
      });
      table.push(...rows);
      return table;
    });
  }

  populateRow(zarrUrl, version) {
    this.store.update((table) => {
      table = table.map((row) => {
        if (row[0] === zarrUrl) {
          row = [zarrUrl, version];
        }
        return row;
      });
      return table;
    });
  }

  async loadNgffMetadata(zarrUrl) {
    let zarrData = await fetch(`${zarrUrl}/zarr.json`).then((response) =>
      response.json(),
    );
    console.log(zarrData);
    const version = zarrData?.attributes?.ome?.version;
    this.populateRow(zarrUrl, version);
  }

  subscribe(run) {
    return this.store.subscribe(run);
  }
}

export const ngffTable = new NgffTable();
