<script>
  import { onMount } from "svelte";
  import * as zarr from "zarrita";
  import { slice } from "@zarrita/indexing";
  import { loadMultiscales} from "./tableStore";
  import {
    renderTo8bitArray,
    getMinMaxValues,
    getDefaultVisibilities,
    hexToRGB,
    getDefaultColors,
  } from "./util";

  const MAX_LENGTH = 100;

  // source is e.g. https://s3.embassy.ebi.ac.uk/idr/zarr/v0.4/6001240.zarr
  export let source;
  // if attrs is not provided, we load it from the source
  export let attrs = undefined;
  // if the lowest resolution is above this size (squared), we don't try to load thumbnails
  export let max_size = 512;

  let canvas;
  let cssWidth = 100;
  let cssHeight = 100;
  let width = 100;
  let height = 100;

  async function loadThumbnail() {
    let paths = attrs.multiscales[0].datasets.map((d) => d.path);
    let axes = attrs.multiscales[0].axes.map((a) => a.name);

    let path = paths.at(-1);
    // const store = await openArray({ store: source + "/" + path, mode: "r" });

    const store = new zarr.FetchStore(source + "/" + path);
    const arr = await zarr.open(store, { kind: "array" });

    let chDim = axes.indexOf("c");

    let shape = arr.shape;
    if (shape.at(-1) * shape.at(-2) > max_size * max_size) {
      console.log("Lowest resolution too large for Thumbnail: ", shape, source);
      return;
    }

    let dims = shape.length;
    let ch = arr.chunks;

    let channel_count = shape[chDim];
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
          return slice(0, dimSize);
        }
        // z
        if (axes[index] == "z") {
          return parseInt((dimSize / 2) + "");
        }
        if (axes[index] == "t") {
          return parseInt((dimSize / 2) + "");
        }
        return 0;
      });
      return zarr.get(arr, slices);
    });

    let ndChunks = await Promise.all(promises);
    let minMaxValues = ndChunks.map((ch) => getMinMaxValues(ch));
    let rbgData = renderTo8bitArray(ndChunks, minMaxValues, colors);

    width = shape.at(-1);
    height = shape.at(-2);
    let scale = width / MAX_LENGTH;
    if (height > width) {
      scale = height / MAX_LENGTH;
    }
    scale = Math.max(1, scale);

    cssWidth = width / scale;
    cssHeight = height / scale;

    // wait for the canvas to be ready (after setting the dimensions)
    setTimeout(() => {
      const ctx = canvas.getContext("2d");
      ctx.putImageData(new ImageData(rbgData, width, height), 0, 0);
    }, 100);
  }

  onMount(async () => {
    if (attrs == undefined) {
      let img = await loadMultiscales(source);
      attrs = img[0];
      // update source to point to the IMAGE within the plate/bioformats2raw layout
      source = img[1];
    }
    loadThumbnail();
  });
</script>

<canvas
  style="width: {cssWidth}px; background-color: lightgrey"
  bind:this={canvas}
  height={height}
  width={width}
/>
