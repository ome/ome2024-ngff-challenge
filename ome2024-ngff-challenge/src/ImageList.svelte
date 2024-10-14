<script>
  import VirtualList from "svelte-tiny-virtual-list";
  import ZarrListItem from "./ZarrListItem.svelte";

  export let tableRows;
  export let textFilter;

  function getItemKey(index) {
    return tableRows[index].url;
  }
</script>

<div class="imageListContainer">
  <h3 style="margin-left: 15px">Showing {tableRows.length} zarrs</h3>
  <VirtualList
    width="100%"
    height={600}
    itemCount={tableRows.length}
    itemSize={220}
    getKey={getItemKey}
  >
    <div slot="item" let:index let:style {style} class="row">
      <ZarrListItem rowData={tableRows[index]} {textFilter} />
    </div>
  </VirtualList>
</div>

<style>
  .imageListContainer {
    border: solid #333 2px;
    width: 100%;
    margin: auto;
    flex: auto 1 1;
  }

  .row {
    background-color: black;
    padding: 10px;
    color: white;
  }
</style>
