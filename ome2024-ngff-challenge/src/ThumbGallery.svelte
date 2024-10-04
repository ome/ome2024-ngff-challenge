<script>
  import { scale } from "svelte/transition";
  import Header from "./Header.svelte";
  import { ngffTable } from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";
  import { SAMPLES_HOME, loadCsv } from "./util";


  export let csvUrl;

  let tableRows = [];
  let maxThumbSize = 512;

  // Map of source to favicon domain
  let faviconDomains = {
    "IDR": "https://idr.openmicroscopy.org",
    "Webknossos": "https://scalableminds.com",
    "JAX": "http://jax.org",
    "BioImage Archive": "https://www.ebi.ac.uk"
  }

  let unsubscribe = ngffTable.subscribe((rows) => {
    tableRows = rows;
    // If we don't have too many rows, we can afford to show larger thumbnails
    if (rows.length < 100) {
      maxThumbSize = 2048;
    } else {
      maxThumbSize = 512;
    }
  });

  function csvShortName(row) {
    return row.csv.split("/").at(-1);
  }

  // kick off loading the CSV...
  // This will load images and recursively load other child csv files - All displayed in table
  function handleThumbClick(csv_url) {
    // If we're loading any page other than HOME page,
    // we need to unsubscribe from the table store so the gallery doesn't update
    console.log("handleThumbClick", csv_url, SAMPLES_HOME);
    if (csv_url !== SAMPLES_HOME) {
      unsubscribe();
    }
    ngffTable.emptyTable();
    csvUrl = csv_url;
    loadCsv(csvUrl, ngffTable);
  }

  function getSourceIcon(source) {
    if (source === "IDR") {
      return "/idr-mark.svg";
    }
    let domain = faviconDomains[source];
    if (!domain) {
      return null;
    }
    return `https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=${domain}&size=24`;
  }
</script>

<Header {tableRows}></Header>

<div class="gallery">
  {#each tableRows as row (row.url)}
    {#if row.csv_row_count && row.csv}
      <a
        on:click|preventDefault={() => handleThumbClick(row.csv)}
        href="{window.location.origin}?csv={row.csv}"
      >
        <div class="item">
          {#if row.image_attrs}
            <Thumbnail attrs={row.image_attrs} source={row.image_url} max_size={maxThumbSize}
            ></Thumbnail>
          {/if}
          {#if getSourceIcon(row.source)}
          <img alt="Icon from {row.source}" class="source_icon" src="{getSourceIcon(row.source)}">
          {/if}
          {#if row.source}
            <span class="source">{row.source}:</span>
          {/if}
          {row.csv_row_count}
          {row.well_count ? "plates" : "images"}

          <div class="hoverInfo">
            {csvShortName(row)}
          </div>
        </div>
      </a>
    {/if}
  {/each}
</div>

<p>
  Loading samples from <a href={csvUrl}>{csvUrl}</a>
</p>

{#if csvUrl !== SAMPLES_HOME}
  <p transition:scale={{ duration: 500, delay: 0, opacity: 0.5, start: 0.5 }}>
    <a
      on:click|preventDefault={() => handleThumbClick(SAMPLES_HOME)}
      class="home"
      title="Show ALL samples"
      href="{window.location.origin}?csv={SAMPLES_HOME}">&lt; Show all samples</a
    >
  </p>
{/if}

<style>
  .home {
    display: inline-block;
    background-color: rgb(241, 188, 13);
    border-radius: 10px;
    padding: 5px 10px;
    color: black;
  }
  .gallery {
    position: relative;
    z-index: 10;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
    gap: 5px;
  }

  .item {
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 100px;
    border: 1px solid #ccc;
    padding: 5px;
    border-radius: 5px;
    background-color: white;
    color: black;
    -webkit-box-shadow: 7px 6px 20px -8px rgba(115,115,115,1);
    -moz-box-shadow: 7px 6px 20px -8px rgba(115,115,115,1);
    box-shadow: 7px 6px 20px -8px rgba(115,115,115,1);
  }

  .source_icon {
    width: 24px;
    height: 24px;
    margin: 2px;
    position: absolute;
    background-color: white;
    padding: 2px;
    border-radius: 3px;
    top: 6px;
    left: 6px;
  }
  .source {
    color: #666;
  }

  .hoverInfo {
    display: none;
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: rgba(0, 0, 0, 0.8);
    color: white;
    font-size: 0.8em;
    justify-content: center;
    align-items: center;
    padding: 5px;
    width: fit-content;
    z-index: 999;
    border-radius: 5px;
  }
  .item:hover .hoverInfo {
    display: block;
  }
</style>
