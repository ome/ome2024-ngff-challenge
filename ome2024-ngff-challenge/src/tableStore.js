import { writable, get } from "svelte/store";

class NgffTable {
  constructor() {
    this.store = writable([]);
  }

  addRows(rows) {
    this.store.update((table) => {
      table.push(...rows);
      return table;
    });
  }

  subscribe(run) {
    return this.store.subscribe(run);
  }
}

export const ngffTable = new NgffTable();
