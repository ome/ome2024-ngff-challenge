<script>
  import { onMount } from "svelte";
  import { loadMultiscales } from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";

  export let rowData;

  console.log("ThumbLoader", rowData);

  let imgAttrs;
  let imgUrl;
  let plateAttrs;

  let thumbDatasetIndex;
  let thumbAspectRatio = 1;
  // If we have shape info
  if (rowData.size_x && rowData.size_y) {
    let longestSide = Math.max(rowData.size_x, rowData.size_y);
    // We want max target size of e.g. 256 pixels
    thumbDatasetIndex = 0;
    while (longestSide > 1024) {
      thumbDatasetIndex += 1;
      longestSide = longestSide / 2;
    }
    thumbAspectRatio = rowData.size_x / rowData.size_y;
  } else {
    thumbDatasetIndex = undefined;
    thumbAspectRatio = 1;
  }

  onMount(async () => {
    let img = await loadMultiscales(rowData.url);
    imgAttrs = img[0];
    imgUrl = img[1];
    plateAttrs = img[2]; // optional
  });
</script>

{#if imgAttrs}
  <Thumbnail
    source={imgUrl}
    attrs={imgAttrs}
    cssSize={512}
    max_size={2000}
    {thumbDatasetIndex}
    {thumbAspectRatio}
  />
{/if}
