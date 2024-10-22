import { writable, get } from "svelte/store";
import { getJson } from "./util";

class Organism {
  constructor() {
    this.store = writable({});
  }

  async lookupOntologyTerm(taxonId) {
    // taxonId e.g. NCBI:txid9606
    let id = taxonId.replace("NCBI:txid", "");
    const orgJson = await getJson(
      `https://rest.ensembl.org/taxonomy/id/${id}?content-type=application/json`,
    );
    return orgJson.name || taxonId;
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
          this.lookupOntologyTerm(organismId).then((name) => {
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

class ImagingModality extends Organism {
  constructor() {
    super();
  }

  async lookupOntologyTerm(fbbiId) {
    // fbbiId e.g. obo:FBbi_00000246
    // http://purl.obolibrary.org/obo/FBbi_00000246
    // https://www.ebi.ac.uk/ols4/api/ontologies/fbbi/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FFBbi_00000246
    const fbbi_id = fbbiId.replace("obo:", "");
    const methodJson = await getJson(
      `https://www.ebi.ac.uk/ols4/api/ontologies/fbbi/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F${fbbi_id}`,
    );
    return methodJson.label || fbbiId;
  }
}

export const organismStore = new Organism();

export const imagingModalityStore = new ImagingModality();
