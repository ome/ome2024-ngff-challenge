import { writable, get } from "svelte/store";
import { getJson } from "./util";

class OntologyMetadataField {
  constructor() {
    this.store = writable({});
  }

  async lookupOntologyTerm(termId) {
    let numericId = "";
    let ontologyId = "";

    if (termId.includes("NCBITaxon") | termId.includes("NCBI:txid")){
      numericId = termId.replace("NCBI:txid", "");
      // cleanup variation
      numericId = numericId.replace("obo:NCBITaxon_", "");
      ontologyId = "NCBITaxon";
    };
    
    if (termId.includes("FBbi")) {
      numericId = termId.replace("obo:FBbi_", "");
      //cleanup variations like
      numericId = numericId.replace("obo:FBbi:", "");
      numericId = numericId.replace("FBbi:", "");
      ontologyId = "FBbi";
    };
    
    // Other ontologies have been used in the FBBI ID field, e.g. NCIT, OBI or MI
    if (termId.includes("NCIT_")){
      numericId = termId.replace("NCIT_", "");
      ontologyId = "NCIT";
    };

    if (termId.includes("obo:MI_")){
      numericId = termId.replace("obo:MI_", "");
      ontologyId = "MI";
    };

    if (termId.includes("obo:OBI_")){
      numericId = termId.replace("obo:OBI_", "");
      ontologyId = "OBI";
    };

    let curie = ontologyId + "_" + numericId;
    let lowerCaseOntologyId = ontologyId.toLowerCase();
    let olsURL = `https://www.ebi.ac.uk/ols4/api/ontologies/${lowerCaseOntologyId}/terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F${curie}`;
    const termLookupJson = await getJson(olsURL);
    return termLookupJson.label || termId;
  }

  addTerms(termIds) {
    // add Ontology terms to the store, looking up terms if not found
    let storeDict = get(this.store);

    const uniqueIds = [...new Set(termIds)];
    uniqueIds.forEach((termId) => {
      if (!termId) {
        return;
      }
      if (!storeDict[termId]) {
        // placeholder to avoid making duplicate requests at once
        storeDict[termId] = "Loading...";

        setTimeout(() => {
          this.lookupOntologyTerm(termId).then((name) => {
            this.addEntry(termId, name);
          });
        }, Math.random() * 5000);
      }
    });
  }

  addEntry(termId, name) {
    this.store.update((lookup) => {
      lookup[termId] = name;
      return lookup;
    });
  }

  subscribe(run) {
    return this.store.subscribe(run);
  }
}

export const organismStore = new OntologyMetadataField();
export const imagingModalityStore = new OntologyMetadataField();