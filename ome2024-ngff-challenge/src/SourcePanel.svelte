<script>
  import { getSourceIcon, filesizeformat } from "./util";

  export let source;
  export let handleFilter;
</script>

<div class="source">
  <label>
    <img
      title={source.url}
      class="sourceLogo"
      alt="Source logo"
      src={getSourceIcon(source.source)}
    />
    <div>
      {source.source}
      <br />
      <span title="{source.child_csv.length} collections"
        >({filesizeformat(source.bytes)})</span
      ><input
        on:change={handleFilter}
        class="source"
        type="radio"
        name="source"
        value={source.source}
      />
      <div class="tooltip">
        {#if source.plate_count }{source.plate_count} plates{/if}
        {source.image_count} images
      </div>
    </div>
  </label>

  <!-- This "clear" is hidden until the input above is checked..
   Then it is shown over the whole panel, so that if the panel is clicked again, it clears the filter -->
  <label class="clear">
    <input
      on:change={handleFilter}
      type="radio"
      name="source"
      value=""
    />
    <span title="Clear filter">
      &times;
    </span>
    </label>
</div>

<style>
  .source:has(input.source:checked) {
    border: solid #ccc 1px;
    background-color: var(--selected-background);
  }
  .source {
    border: solid var(--border-color) 1px;
    float: left;
    position: relative;
    padding: 3px;
    border-radius: 5px;
    cursor: pointer;
  }
  .source label {
    display: flex;
    flex-direction: row;
    position: relative;
    padding: 5px;
    cursor: pointer;
    gap: 5px;
    line-height: normal;
  }
  .sourceLogo {
    /* min-width: 24px; */
    height: 32px;
    margin: 2px;
    background-color: #fff;
    padding: 2px;
    border-radius: 4px;
  }
  input[type="radio"] {
    visibility: hidden;
    width: 0;
    margin: 0;
  }
  .source .clear {
    display: none;
    position: absolute;
    inset: 0;
    background-color: transparent;
    opacity: 0.5;
  }
  .source:has(input.source:checked) .clear {
    display: block;
    text-align: right;
  }

  .tooltip {
    display: none;
    top: 100%;
    position: absolute;
    background-color: #f9f9f9;
    border: 1px solid #ccc;
    border-radius: 5px;
    padding: 5px;
    z-index: 1;
  }
  .source:hover .tooltip {
    display: block;
  }
</style>
