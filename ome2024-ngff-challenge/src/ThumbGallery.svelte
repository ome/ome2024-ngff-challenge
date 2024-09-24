<script>
  import { galleryTable, ngffTable } from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";
  import { loadCsv } from "./util";

  let tableRows = [];

  galleryTable.subscribe((rows) => {
    tableRows = rows;
  });

  $: zarr_url_count = tableRows.reduce((acc, row) => acc + (row.csv_row_count || 0), 0);
  $: csv_file_count = tableRows.reduce((acc, row) => acc + (row.csv_row_count ? 1 : 0), 0);

  function csvShortName(row) {
    return row.csv.split("/").at(-1);
  }

  // kick off loading the CSV...
  // This will load images and recursively load other child csv files - All displayed in table
  function handleThumbClick(row) {
    ngffTable.emptyTable();
    loadCsv(row.csv, ngffTable);
  }
</script>

{#if zarr_url_count > 0}
<h2>
  {zarr_url_count} zarrs in {csv_file_count} collections
</h2>
{/if}
<div class="gallery">
  {#each tableRows as row (row.url)}
    {#if row.csv_row_count && row.csv}
    <a on:click|preventDefault={() => handleThumbClick(row)} href="{window.location.origin}?csv={row.csv}">
    <div class="item">
      {#if row.image_attrs}
        <Thumbnail attrs={row.image_attrs} source={row.image_url}></Thumbnail>
      {/if}
      {row.csv_row_count} {row.well_count ? "plates" : "images"}

      <div class="hoverInfo">
        {row.source || ""}
        {csvShortName(row)}
      </div>
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
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 100px;
    border: 1px solid #ccc;
    padding: 5px;
    border-radius: 5px;
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
