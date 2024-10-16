<script>
  import VirtualList from "svelte-tiny-virtual-list";
  import ZarrListItem from "./ZarrListItem.svelte";

  export let tableRows;
  export let textFilter;

  function getItemKey(index) {
    return tableRows[index].url;
  }

  let listContainer;
	$: innerHeight = 0;

  let pageScrollY = 0;
  let prevScrollOffset = 0;

  // To avoid having to scroll all the way back to the start before
  // you can access the controls above the list, we scroll the page
  // a bit... But only to show the first 20px above the list...
  function afterScroll(event) {
    let margin = 20;
    let scrollLimit = listContainer.offsetTop - margin;
    // When the virtual list scrolls back...
    let deltaScroll = event.detail.offset - prevScrollOffset;
    // We also scroll the whole page to show the list container...
    if (deltaScroll < 0 && pageScrollY > scrollLimit) {
      pageScrollY -= 1;
    }

    prevScrollOffset = event.detail.offset;
  }
</script>


<svelte:window bind:innerHeight bind:scrollY={pageScrollY} />

<!-- We make the scrollable viewport fill the full height of the page -->
<div bind:this={listContainer} style:height="{innerHeight}px" class="imageListContainer">
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
    border-top: solid var(--border-color) 1px;
    width: 100%;
    margin: auto;
    flex: auto 1 1;
    overflow: hidden;
  }

  .row {
    padding: 10px;
  }
</style>
