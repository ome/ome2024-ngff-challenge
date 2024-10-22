<script>
  import { onMount } from "svelte";
  import { ngffTable } from "./tableStore";
  import ThumbLoader from "./ThumbLoader.svelte";

  let popover;

  let rowData;
  let zarrUrl;

  ngffTable.subscribeSelectedRow((row) => {
    console.log("Showing preview for", row);
    if (row) {
      rowData = row;
      console.log("Showing Thumb preview for", row, rowData);
      zarrUrl = rowData.url;
      popover.showPopover();
    }
  });

  function hidePopover() {
    popover.hidePopover();
  }

  onMount(() => {
    console.log("Mounted popover", popover);
    if (popover) {
      popover.addEventListener("toggle", (event) => {
        if (event.newState === "open") {
          // console.log("Popover has been shown");
        } else {
          console.log("Popover has been hidden");
          ngffTable.setSelectedRow(null);
        }
      });
    }
  });
</script>

<div bind:this={popover} id="mypopover" popover>
  <button class="close" title="Close" on:click={hidePopover}>&times;</button>

  <div class="scrollable">
    <!-- key forces rerender when url changes -->
    {#key zarrUrl}
      {#if zarrUrl}
        <ThumbLoader {rowData} />
      {/if}
    {/key}

    {#if rowData}
      <table>
        {#each Object.entries(rowData) as [key, value]}
          <tr><td>{key}</td><td>{value}</td></tr>
        {/each}
      </table>
    {/if}
  </div>
</div>

<style>
  .close {
    position: absolute;
    right: 5px;
    top: 5px;
    z-index: 100;
    font-size: 2rem;
    padding: 2px 9px;
  }
  .scrollable {
    position: absolute;
    inset: 0;
    overflow: auto;
    height: 100%;
    background: white;
    z-index: 0;
    padding: 5px;
  }
  #mypopover {
    position: fixed;
    margin-right: 5px;
    margin-bottom: 5px;
    width: 50%;
    height: 75%;
    overflow: auto;
    box-shadow: 5px 4px 10px -5px #737373;
  }

  @media (max-width: 800px) {
    #mypopover {
      width: 100%;
    }
  }
</style>
