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

  onMount(async () => {
    let img = await loadMultiscales(rowData.url);
    imgAttrs = img[0];
    imgUrl = img[1];
    plateAttrs = img[2]; // optional
  });

  $: description = (textFilter != "" && rowData.description?.includes(textFilter)) ? rowData.description : "";
</script>

<div class="zarr-list-item">
  <div>
    {#if imgAttrs}
      <Thumbnail source={imgUrl} attrs={imgAttrs} max_size={2000} />
    {/if}
  </div>
  <table>
    {#each ["t", "c", "z", "y", "x"] as dim}
      {#if rowData[`size_${dim}`] !== undefined}
        <tr><td>{dim.toUpperCase()}</td><td>{rowData[`size_${dim}`]}</td></tr>
      {/if}
    {/each}
    <tr><td>Size</td><td>{filesizeformat(rowData.written)}</td></tr>
  </table>
  <div>
    <div>{@html rowData.name ? rowData.name.replaceAll(textFilter, `<mark>${textFilter}</mark>`) : ""}</div>
    <div>{@html description.replaceAll(textFilter, `<mark>${textFilter}</mark>`)}</div>
    {#if rowData.origin }
      <div>Original data: <a
        title="Link to original data: {rowData.origin}"
        href={rowData.origin}
        target="_blank"
        >...{rowData.origin.slice(-30)}
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
