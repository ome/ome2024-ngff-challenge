<script>
  import VirtualList from "svelte-tiny-virtual-list";
  import ZarrListItem from "./ZarrListItem.svelte";

  export let tableRows;
  export let textFilter;

  function getItemKey(index) {
    return tableRows[index].url;
  }

	$: innerHeight = 0;

  let pageScrollY = 0;
  let prevScrollOffset = 0;

  function afterScroll(event) {
    // When the virtual list scrolls down or up...
    let deltaScroll = event.detail.offset - prevScrollOffset;

    // We also scroll the whole page down to show the list container...
    if (pageScrollY < 300 && deltaScroll > 0) {
      // pageScrollY += deltaScroll;
    } else if (deltaScroll < 0 && pageScrollY > 0) {
      pageScrollY += deltaScroll;
    }

    prevScrollOffset = event.detail.offset;
  }
</script>


<svelte:window bind:innerHeight bind:scrollY={pageScrollY} />

<div style:height="{innerHeight}px" class="imageListContainer">
  <VirtualList
    width="100%"
    height={innerHeight}
    itemCount={tableRows.length}
    itemSize={160}
    getKey={getItemKey}
    on:afterScroll={afterScroll}
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
    overflow: hidden;
  }

  .row {
    background-color: black;
    padding: 10px;
    color: white;
  }
</style>
