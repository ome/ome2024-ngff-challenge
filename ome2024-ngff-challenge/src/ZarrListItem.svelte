<script>
  import { onMount } from "svelte";
  import { filesizeformat } from "./util";

  export let rowData;

  onMount(async () => {
    console.log("onMount", rowData.url);
  });
</script>

<div class="zarr-list-item">
  T:{rowData.size_t} C:{rowData.size_c} Z:{rowData.size_z} X:{rowData.size_x} Y:{rowData.size_y} Size: {filesizeformat(rowData.written)}

</div>


<style>
  .zarr-list-item {
    padding: 10px;
    color: royalblue;
  }
  </style>
