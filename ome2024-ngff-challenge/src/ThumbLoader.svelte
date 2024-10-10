<script>
    import { onMount } from "svelte";
    import { loadMultiscales } from "./tableStore";
    import Thumbnail from "./Thumbnail.svelte";

    export let source;

    let imgAttrs;
    let imgUrl;
    let plateAttrs;

    onMount(async () => {
      let img = await loadMultiscales(source);
      imgAttrs = img[0];
      imgUrl = img[1];
      plateAttrs = img[2]; // optional
    });
  </script>

  {#if imgAttrs}
  <Thumbnail source={imgUrl} attrs={imgAttrs} max_size={2000} />
  {/if}
