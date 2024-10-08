<script>
  import { onMount } from "svelte";
  import { filesizeformat } from "./util";
  import {loadMultiscales} from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";

  export let rowData;
  export let listIndex;

  let imgAttrs;
  let imgUrl;
  let plateAttrs;

  onMount(async () => {
    console.log("onMount", rowData.url);

    let img = await loadMultiscales(rowData.url);
    imgAttrs = img[0];
    imgUrl = img[1];
    plateAttrs = img[2]; // optional

  });
</script>

<div class="zarr-list-item">
  <div style:float={listIndex % 2 == 0 ? "right" : "left"}>
    {#if imgAttrs}
      <Thumbnail source={imgUrl} attrs={imgAttrs} max_size={2000} />
    {/if}
  </div>
  T:{rowData.size_t} C:{rowData.size_c} Z:{rowData.size_z} X:{rowData.size_x} Y:{rowData.size_y} Size: {filesizeformat(rowData.written)}

</div>


<style>
  .zarr-list-item {
    padding: 10px;
    color: royalblue;
  }
  </style>
