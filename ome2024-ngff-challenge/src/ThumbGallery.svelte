<script>
  import { galleryTable, ngffTable } from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";
  import { loadCsv } from "./util";

  let tableRows = [];

  galleryTable.subscribe((rows) => {
    tableRows = rows;
  });

  // kick off loading the CSV...
  // This will load images and recursively load other child csv files - All displayed in table
  function handleThumbClick(row) {
    ngffTable.emptyTable();
    loadCsv(row.csv, ngffTable);
  }
</script>

<div class="gallery">
  {#each tableRows as row (row.url)}
    {#if row.csv_row_count && row.csv}
    <a on:click|preventDefault={() => handleThumbClick(row)} href="{window.location.origin}?csv={row.csv}">
    <div class="item">
      {#if row.image_attrs}
        <Thumbnail attrs={row.image_attrs} source={row.image_url}></Thumbnail>
      {/if}
      {row.csv_row_count} {row.well_count ? "plates" : "images"}
    </div>
  </a>
    {/if}
  {/each}
</div>

<style>
  .gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
    gap: 5px;
  }

  .item {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 100px;
    border: 1px solid #ccc;
    padding: 5px;
    border-radius: 5px;
  }
</style>
