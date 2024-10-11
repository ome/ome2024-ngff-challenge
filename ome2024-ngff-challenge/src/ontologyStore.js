import { writable, get } from "svelte/store";
import { lookupOrganism } from "./util";

class Organism {
  constructor() {
    this.store = writable({});
  }

  addTerms(oganismIds) {
    // add Ontology terms to the store, looking up terms if not found
    let storeDict = get(this.store);

    const uniqeIds = [...new Set(oganismIds)];
    uniqeIds.forEach((organismId) => {
      if (!organismId) {
        return;
      }
      if (!storeDict[organismId]) {
        // placeholder to avoid making duplicate requests at once
        storeDict[organismId] = "Loading...";

        // To avoid "limit of 15 requests per second" spread over a
        // couple of seconds...
        setTimeout(() => {
          lookupOrganism(organismId).then((name) => {
            this.addEntry(organismId, name);
          });
        }, Math.random() * 5000);
      }
    });
  }

  addEntry(ogansimId, name) {
    this.store.update((lookup) => {
      lookup[ogansimId] = name;
      return lookup;
    });
  }

  subscribe(run) {
    return this.store.subscribe(run);
  }
}

export const organismStore = new Organism();
