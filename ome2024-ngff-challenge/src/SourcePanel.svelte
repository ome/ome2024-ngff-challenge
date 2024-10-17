<script>
  import { getSourceIcon } from "./util";

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
    <br/>
    <span title="{source.child_csv.length} collections"
      >({source.total_count} images)</span
    ><input
    on:change={handleFilter}
    type="radio"
    name="source"
    value={source.source}
  />
  </div>
  </label>
</div>


<style>
  .source:has(input:checked) {
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

</style>
