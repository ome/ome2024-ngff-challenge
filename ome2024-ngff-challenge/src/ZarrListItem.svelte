<script>
  import { onMount } from "svelte";
  import { filesizeformat } from "./util";
  import { loadMultiscales } from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";
  import omeLogo from '/ome-logomark.svg';
  import vizarrLogo from '/vizarr_logo.png';

  export let rowData;
  export let textFilter;

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
    while (longestSide > 256) {
      thumbDatasetIndex += 1;
      longestSide = longestSide / 2;
    }
    thumbAspectRatio = rowData.size_x / rowData.size_y;
  }

  onMount(async () => {
    let img = await loadMultiscales(rowData.url);
    imgAttrs = img[0];
    imgUrl = img[1];
    plateAttrs = img[2]; // optional

  });

  $: description = (textFilter != "" && rowData.description?.includes(textFilter)) ? rowData.description : "";
</script>

<div class="zarr-list-item">
  <div class="thumbWrapper">
    {#if imgAttrs}
      <Thumbnail source={imgUrl} attrs={imgAttrs} max_size={2000} {thumbDatasetIndex} {thumbAspectRatio}/>
    {/if}
  </div>
  <table>
    {#each ["t", "c", "z", "y", "x"] as dim}
      {#if rowData[`size_${dim}`] !== undefined}
        <tr><td>{dim.toUpperCase()}</td><td>{rowData[`size_${dim}`]}</td></tr>
      {/if}
    {/each}
    <tr><td>Size</td><td style="white-space: nowrap">{filesizeformat(rowData.written)}</td></tr>
  </table>
  <div>
    <div>{@html rowData.name ? rowData.name.replaceAll(textFilter, `<mark>${textFilter}</mark>`) : ""}</div>
    <div>{@html description.replaceAll(textFilter, `<mark>${textFilter}</mark>`)}</div>
    {#if rowData.origin }
      <div><a
        title="Link to original data: {rowData.origin}"
        href={rowData.origin}
        target="_blank"
        >Original data
      </a></div>
    {/if}
    <a
      title="Validator: {rowData.url}"
      href="https://deploy-preview-36--ome-ngff-validator.netlify.app/?source={rowData.url}"
      target="_blank"
      ><img alt="OME logo" class="link_logo" src={omeLogo} />
    </a>
  </div>
</div>

<style>
  .thumbWrapper {
    width: 120px;
    height: 120px;
  }
  .zarr-list-item {
    padding: 10px;
    color: lightgray;
    display: flex;
    flex-direction: row;
    align-items: start;
    gap: 10px;
  }
  table {
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
