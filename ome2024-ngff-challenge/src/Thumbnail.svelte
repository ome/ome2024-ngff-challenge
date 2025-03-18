<script>
  import { onMount, onDestroy } from "svelte";
  import * as zarr from "zarrita";
  import {
    renderTo8bitArray,
    getMinMaxValues,
    getDefaultVisibilities,
    hexToRGB,
    getDefaultColors,
  } from "./util";

  // source is e.g. https://s3.embassy.ebi.ac.uk/idr/zarr/v0.4/6001240.zarr
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

  const controller = new AbortController();

  async function loadThumbnail() {
    let paths = attrs.multiscales[0].datasets.map((d) => d.path);
    let axes = attrs.multiscales[0].axes.map((a) => a.name);

    // By default, we use the smallest thumbnail path (last dataset)
    let path = paths.at(-1);
    if (thumbDatasetIndex != undefined && thumbDatasetIndex < paths.length) {
      // but if we have a valid dataset index, use that...
      path = paths[thumbDatasetIndex];
    }

    const store = new zarr.FetchStore(source + "/" + path);
    const arr = await zarr.open.v3(store, { kind: "array" });

    let chDim = axes.indexOf("c");

    let shape = arr.shape;
    if (shape.at(-1) * shape.at(-2) > max_size * max_size) {
      console.log("Lowest resolution too large for Thumbnail: ", shape, source);
      return;
    }

    let dims = shape.length;

    let channel_count = shape[chDim] || 1;
    let visibilities;
    let colors;
    if (attrs?.omero?.channels) {
      visibilities = attrs.omero.channels.map((ch) => ch.active);
      colors = attrs.omero.channels.map((ch) => hexToRGB(ch.color));
    } else {
      visibilities = getDefaultVisibilities(channel_count);
      colors = getDefaultColors(channel_count, visibilities);
    }
    // filter for active channels
    colors = colors.filter((col, idx) => visibilities[idx]);

    let activeChannels = visibilities.reduce((prev, active, index) => {
      if (active) prev.push(index);
      return prev;
    }, []);

    let promises = activeChannels.map((chIndex) => {
      let slices = shape.map((dimSize, index) => {
        // channel
        if (index == chDim) return chIndex;
        // x and y
        if (index >= dims - 2) {
          return zarr.slice(0, dimSize);
        }
        // z
        if (axes[index] == "z") {
          return parseInt(dimSize / 2 + "");
        }
        if (axes[index] == "t") {
          return parseInt(dimSize / 2 + "");
        }
        return 0;
      });
      return zarr.get(arr, slices, { opts: { signal: controller.signal } });
    });

    let ndChunks = await Promise.all(promises);
    let minMaxValues = ndChunks.map((ch) => getMinMaxValues(ch));
    let rbgData = renderTo8bitArray(ndChunks, minMaxValues, colors);

    width = shape.at(-1);
    height = shape.at(-2);
    let scale = width / cssSize;
    if (height > width) {
      scale = height / cssSize;
    }

    cssWidth = width / scale;
    cssHeight = height / scale;

    // wait for the canvas to be ready (after setting the dimensions)
    setTimeout(() => {
      const ctx = canvas.getContext("2d");
      showSpinner = false;
      ctx.putImageData(new ImageData(rbgData, width, height), 0, 0);
    }, 100);
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
<canvas
  style="width: {cssWidth}px; height:{cssHeight}px; background-color: lightgrey"
  bind:this={canvas}
  {height}
  {width}
/></div>

<style>
  .canvasWrapper {
    position: relative;
  }
  canvas {
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
