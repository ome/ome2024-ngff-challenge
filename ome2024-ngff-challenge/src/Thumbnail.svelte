<script>
  import { onMount, onDestroy } from "svelte";
  import * as zarr from "zarrita";
  import * as omezarr from "ome-zarr.js";

  // source is e.g. https://s3.embassy.ebi.ac.uk/idr/zarr/v0.4/6001240.zarr
  export let source;
  export let attrs;
  export let thumbDatasetIndex = undefined;
  export let thumbAspectRatio = 1;
  export let cssSize = 120;
  // if the lowest resolution is above this size (squared), we don't try to load thumbnails
  export let max_size = 512;

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
   // transparent gif is used as placeholder
  let imgSrc = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

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

    let shape = arr.shape;
    if (shape.at(-1) * shape.at(-2) > max_size * max_size) {
      console.log("Lowest resolution too large for Thumbnail: ", shape, source);
      return;
    }

    let src = await omezarr.renderImage(arr, attrs.multiscales[0].axes, attrs.omero);
    imgSrc = src;
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
  <img src={imgSrc} alt="Thumbnail" style="width: {cssWidth}px; height:{cssHeight}px;" />
</div>

<style>
  .canvasWrapper {
    position: relative;
  }
  img {
    box-shadow: 5px 4px 10px -5px #737373;
    background: lightgrey;
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
