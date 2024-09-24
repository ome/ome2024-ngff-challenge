<script>
  import { ngffTable } from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";

  let tableRows = [];

  ngffTable.subscribe((rows) => {
    tableRows = rows;
  });
</script>

<div class="gallery">
  {#each tableRows as row (row.url)}
   <div class="item">
    {#if row.image_attrs}
      <Thumbnail attrs={row.image_attrs} source={row.image_url}></Thumbnail>
    {/if}
    {#if row.csv_row_count && row.csv}
      {row.csv_row_count} {row.well_count ? "plates" : "images"}
    {/if}
    </div>
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
