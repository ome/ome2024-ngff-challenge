<script>
  import { onMount } from "svelte";
  import * as zarr from "zarrita";
  import { slice } from "@zarrita/indexing";
  import {
    renderTo8bitArray,
    getMinMaxValues,
    getDefaultVisibilities,
    hexToRGB,
    getDefaultColors,
    getJson,
  } from "./util";

  const chick =
    "https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/idr0066/ExpD_chicken_embryo_MIP.zarr";

  const cells = "https://uk1s3.embassy.ebi.ac.uk/ebi-ngff-challenge-2024/4ffaeed2-fa70-4907-820f-8a96ef683095.zarr";
  const idr0036 = "https://uk1s3.embassy.ebi.ac.uk/idr/share/ome2024-ngff-challenge/idr0036/20596.ome.zarr/A/1/0"
  const CANVAS_SIZE = 1524;

  let canvas;
  // let cssWidth = 100;
  // let cssHeight = 100;
  let width = 100;
  let height = 100;

  async function loadThumbnail(source, attrs, pathIndex, minMaxValues, x=0, y=0) {
    let paths = attrs.multiscales[0].datasets.map((d) => d.path);
    let axes = attrs.multiscales[0].axes.map((a) => a.name);

    let path = paths.at(pathIndex);
    // const store = await openArray({ store: source + "/" + path, mode: "r" });

    const store = new zarr.FetchStore(source + "/" + path);
    const arr = await zarr.open(store, { kind: "array" });

    let chDim = axes.indexOf("c");

    let shape = arr.shape;

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
    if (!minMaxValues) {
      minMaxValues = ndChunks.map((ch) => getMinMaxValues(ch));
    }

    let rbgData = renderTo8bitArray(ndChunks, minMaxValues, colors);

    width = shape.at(-1);
    height = shape.at(-2);
    // let scale = width / MAX_LENGTH;
    // if (height > width) {
    //   scale = height / MAX_LENGTH;
    // }
    // cssWidth = width / scale;
    // cssHeight = height / scale;

    // wait for the canvas to be ready (after setting the dimensions)
    setTimeout(() => {
      const ctx = canvas.getContext("2d");
      ctx.putImageData(new ImageData(rbgData, width, height), x, y);
    }, 10);

    return { width, height };
  }


  function delay(milliseconds){
    return new Promise(resolve => {
        setTimeout(resolve, milliseconds);
    });
  }

  async function load(source, mm, y){

    let attrs = await getJson(source + "/zarr.json");
    console.log("attrs", attrs);

    let x = 0;
    let {width, height} = await loadThumbnail(source, attrs.attributes.ome, -1, mm, x, y);

    x += width;
    // await delay(1000);
    let dims = await loadThumbnail(source, attrs.attributes.ome, -2, mm, x, y);

    x += dims.width;
    // await delay(1000);
    dims = await loadThumbnail(source, attrs.attributes.ome, -3, mm, x, y);

    x += dims.width;
    // await delay(1000);
    dims = await loadThumbnail(source, attrs.attributes.ome, -4, mm, x, y);
  };

  onMount(async() => {
    load(chick, [[0, 55]], 0);
    // load(cells, undefined, 200);
    load(idr0036, undefined, 200);
  });
</script>

<canvas
  width={CANVAS_SIZE}
  height={CANVAS_SIZE}
  style:width="{CANVAS_SIZE}px"
  style:height="{CANVAS_SIZE}px"
  bind:this={canvas}
/>

<style>
  canvas {
    position: fixed;
    width: 100%;
    height: 100%;
    background-color: black;
  }
</style>
