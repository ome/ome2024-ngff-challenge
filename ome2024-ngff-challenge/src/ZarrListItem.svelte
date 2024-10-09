<script>
  import { onMount } from "svelte";
  import { filesizeformat } from "./util";
  import { loadMultiscales } from "./tableStore";
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
  <table style:float={listIndex % 2 == 0 ? "right" : "left"}>
    <tr><td>T</td><td>{rowData.size_t}</td></tr>
    <tr><td>C</td><td>{rowData.size_c}</td></tr>
    <tr><td>Z</td><td>{rowData.size_z}</td></tr>
    <tr><td>X</td><td>{rowData.size_x}</td></tr>
    <tr><td>Y</td><td>{rowData.size_y}</td></tr>
    <tr><td>Size</td><td>{filesizeformat(rowData.written)}</td></tr>
  </table>
  <div style:float={listIndex % 2 == 0 ? "right" : "left"}>
    <a
      title="Validator: {rowData.url}"
      href="https://deploy-preview-36--ome-ngff-validator.netlify.app/?source={rowData.url}"
      target="_blank"
      ><img alt="OME logo" class="link_logo" src="/ome-logomark.svg" />
    </a>
    <a
      title="Vizarr: {rowData.url}"
      href="https://hms-dbmi.github.io/vizarr/?source={rowData.url}"
      target="_blank"
      ><img alt="Vizarr logo" class="link_logo" src="/vizarr_logo.png" />
    </a>
  </div>
</div>

<style>
  .zarr-list-item {
    padding: 10px;
    color: lightgray;
  }
  table {
    float: left;
    margin-left: 10px;
  }
  td {
    padding: 1px;
    font-size: 80%;
    line-height: normal;
  }
  .link_logo {
    width: 24px;
    height: 24px;
    visibility: hidden;
  }
  .zarr-list-item:hover .link_logo {
    visibility: visible;
  }
</style>
