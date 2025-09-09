<script>
  import { onMount } from "svelte";
  import { filesizeformat } from "./util";
  import { loadMultiscales, ngffTable } from "./tableStore";
  import Thumbnail from "./Thumbnail.svelte";
  import { onDestroy } from "svelte";
  import copyImage from "/copy.png";
  import checkImage from "/check.png";
  export let rowData;
  export let textFilter;
  export let sortedBy = undefined;

  let imgAttrs;
  let imgUrl;
  let plateAttrs;

  let thumbDatasetIndex;
  let thumbAspectRatio = 1;
  const controller = new AbortController();
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

  function csvUrl(rowData) {
    let currentUrl = window.location.origin + window.location.pathname;
    return currentUrl + "?csv=" + rowData.csv;
  }

  function handleThumbClick() {
    console.log("Clicked on thumbnail");
    ngffTable.setSelectedRow(rowData);
  }

  function formatUrlToName(url) {
    if (textFilter && url.toLowerCase().includes(textFilter.toLowerCase())) {
      const MAX_LENGTH = 50;
      // find first occurrence of textFilter in url and highlight it
      let urlLc = url.toLowerCase();
      let filterLc = textFilter.toLowerCase();
      let startMatch = urlLc.indexOf(filterLc);
      // let endMatch = start + filterLc.length;
      let start = Math.max(0, Math.min(startMatch, url.length - MAX_LENGTH));

      let result = url.substring(start, startMatch);
      result += "<mark>";
      result += url.substring(startMatch, startMatch + filterLc.length);
      result += "</mark>";
      result += url.substring(startMatch + filterLc.length);
      return result;
    }
    return url.split("/").pop();
  }

  onMount(async () => {
    let zarrUrl = rowData.url;
    // If we know the path to first series, add it
    if (rowData.series0 !== undefined) {
      zarrUrl += "/" + rowData.series0;
    }
    let img = await loadMultiscales(zarrUrl, controller.signal);
    imgAttrs = img[0];
    imgUrl = img[1];
    plateAttrs = img[2]; // optional
  });

  onDestroy(() => {
    // Doesn't seem to abort fetching of chunks
    controller.abort();
  });

  $: description = (textFilter != "" && rowData.description?.toLowerCase().includes(textFilter.toLowerCase())) ? rowData.description : "";

  let isShaking = false;
  // Adapted from https://github.com/IDR/ome-ngff-samples/blob/main/index.md
  function copyTextToClipboard(text) {
    var textArea = document.createElement("textarea");
    // Place in the top-left corner of screen regardless of scroll position.
    textArea.style.position = 'fixed';
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    let successful = false;
    try {
      successful = document.execCommand("copy");
    } catch (err) {
      console.log("Oops, unable to copy");
    }
    document.body.removeChild(textArea);

    if (successful) {
      // trigger shake for 1s
      isShaking = true;
      setTimeout(() => (isShaking = false), 1000);
    }
};
</script>

<div class="zarr-list-item">
  <div class="thumbWrapper" on:click={handleThumbClick}>
    {#if imgAttrs}
      <Thumbnail source={imgUrl} attrs={imgAttrs} max_size={2000} {thumbDatasetIndex} {thumbAspectRatio}/>
    {/if}
  </div>
  <div>
    <div title="{rowData.url}"><strong>{@html formatUrlToName(rowData.url)} </strong>

  </div>
    <div class={textFilter == "" ? "hideOnSmall" : ""}>
      <!-- If we're not filtering by text (name/description) then hide the name on small screen -->
      {@html rowData.name ? rowData.name.replaceAll(textFilter, `<mark>${textFilter}</mark>`) : ""}
    </div>
    <div>{@html description.replaceAll(textFilter, `<mark>${textFilter}</mark>`)}</div>
    {#if rowData.source }
      <div>
        <span class="hideOnSmall">Data</span>
        {#if rowData.csv}
          <span class="hideOnSmall">from collection</span>
          <a title="Show collection in a new tab" href={csvUrl(rowData)} target="_blank">{rowData.csv?.split("/").pop().replace(".csv", "")}</a>
        {/if}
        <span class="hideOnSmall">provided by</span> <strong style="color:grey">{rowData.source}</strong>.
      </div>
    {/if}
    <div>
      <button
    class="no_border"
    class:shake={isShaking}
    title="Copy S3 URL to clipboard"
    on:click={(event) => copyTextToClipboard(rowData.url)
    }
    >
    <img class="icon" src={copyImage} />    
    </button>

      <a title="Validate NGFF with 'ome-ngff-validator' in new browser tab" target="_blank"
                    href="https://ome.github.io/ome-ngff-validator/?source={rowData.url}">
                    <img class="icon" style="opacity: 0.5" src={checkImage}/></a>

    {#if rowData.origin }
      Browse <a
        title="Link to original data: {rowData.origin}"
        href={rowData.origin}
        target="_blank"
        >Original data</a>.
    {/if}
    </div>
    <div>
      Image size:
      {#each ["t", "c", "z", "y", "x"] as dim}
        {#if rowData[`size_${dim}`] !== undefined}
          {dim.toUpperCase()}:{rowData[`size_${dim}`]} &nbsp;
        {/if}
      {/each}
    </div>
    {#if sortedBy == "chunk_pixels" }
      <div>Chunk shape: {rowData.chunks}</div>
    {:else if sortedBy == "shard_pixels" }
      <div>Shard shape: {rowData.shards}</div>
    {:else}
      <div>Data size: {filesizeformat(rowData.written)}</div>
    {/if}
  </div>
</div>

<style>
  .thumbWrapper {
    width: 120px;
    height: 120px;
    cursor: pointer;
  }
  .zarr-list-item {
    padding: 10px;
    display: flex;
    flex-direction: row;
    align-items: start;
    gap: 10px;
    background-color: var(--background-color);
  }
  @media (max-width: 800px) {
    /* On small screen, hide name & description */
    .hideOnSmall {
      display: none;
    }
  }

    .no_border {
    border: none;
    background: none;
    padding: 0;
    }

   .shake {
        animation: 0.1s linear 0s infinite alternate seesaw;
    }

    @keyframes seesaw { from { transform: rotate(-0.05turn) } to { transform: rotate(0.05turn); }  }

</style>
