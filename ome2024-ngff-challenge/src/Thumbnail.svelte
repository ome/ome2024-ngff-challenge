<script>
  import { onMount, onDestroy } from "svelte";
  import * as omezarr from "ome-zarr.js";

  // source is e.g. https://livingobjects.ebi.ac.uk/idr/zarr/v0.4/idr0062A/6001240.zarr
  export let source;
  export let attrs;
  export let thumbDatasetIndex = undefined;
  export let thumbAspectRatio = 1;
  export let cssSize = 120;
  // if the lowest resolution is above this size (squared), we don't try to load thumbnails
  export let max_size = 512;

  let canvas;
  let width = cssSize;
  let height = cssSize;
  if (thumbAspectRatio > 1) {
    height = width / thumbAspectRatio;
  } else if (thumbAspectRatio < 1) {
    width = height * thumbAspectRatio;
  }
  let cssWidth = width;
  let cssHeight = height;
  let showSpinner = true;
  let imgSrc;

  const controller = new AbortController();

  async function loadThumbnail() {
    let paths = attrs.multiscales[0].datasets.map((d) => d.path);

    // By default, we use the smallest thumbnail path (last dataset)
    let dsIndex = -1;
    if (thumbDatasetIndex != undefined) {
      dsIndex = Math.min(thumbDatasetIndex, paths.length - 1);
    }

    let ngffImg = await omezarr.NgffImage.load(source, {
      attrs: {ome: attrs},
      datasetIndex: dsIndex,
      signal: controller.signal});
    imgSrc = await ngffImg.render({arrayPathOrIndex: dsIndex, maxSize: max_size, signal: controller.signal});
    showSpinner = false;
  }

  onMount(() => {
    loadThumbnail();
  });

  onDestroy(() => {
    controller.abort();
  });
</script>

<!-- Need a wrapper to show spinner -->
<div class="canvasWrapper" style="width: {cssWidth}px; height:{cssHeight}px;" class:spinner={showSpinner}>
{#if imgSrc}
  <img
  alt="Thumbnail"
  style="width: {cssWidth}px; height:{cssHeight}px; background-color: lightgrey"
  src={imgSrc}
/>
{/if}
</div>

<style>
  .canvasWrapper {
    position: relative;
    background-color: lightgrey;
    box-shadow: 5px 4px 10px -5px #737373;
  }

  @keyframes spinner {
    to {
      transform: rotate(360deg);
    }
  }

  .spinner:after {
    content: "";
    box-sizing: border-box;
    position: absolute;
    top: 50%;
    left: 50%;
    width: 40px;
    height: 40px;
    margin-top: -20px;
    margin-left: -20px;
    border-radius: 50%;
    border: 5px solid rgba(180, 180, 180, 0.6);
    border-top-color: rgba(0, 0, 0, 0.6);
    animation: spinner 0.6s linear infinite;
  }
</style>
