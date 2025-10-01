<script>
  import { onMount } from "svelte";
  import { loadMultiscales } from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";

  export let rowData;

  let imgUrl;

  let thumbAspectRatio = 1;
  // If we have shape info
  if (rowData.size_x && rowData.size_y) {
    thumbAspectRatio = rowData.size_x / rowData.size_y;
  } else {
    thumbAspectRatio = 1;
  }

  onMount(async () => {
    // traverse Plate or bioformats2raw structure to find first image
    let img = await loadMultiscales(rowData.url);
    imgUrl = img[1];
  });
</script>

{#if imgUrl}
  <Thumbnail
    source={imgUrl}
    cssSize={512}
    max_size={2000}
    {thumbAspectRatio}
  />
{/if}
