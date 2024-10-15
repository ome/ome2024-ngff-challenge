<script>
  export let col_name;
  export let col_label;
  export let handleSort;
  export let sortedBy;
  export let sortAscending;
</script>

<button on:click={() => handleSort(col_name)}>
  {col_label}

  <span class="acc" class:strong={sortedBy==col_name && sortAscending}>^</span>
  <span class="dec" class:strong={sortedBy==col_name && !sortAscending}>^</span>

</button>

<style>
  button {
    background-color: var(--light-background);
    border: none;
    text-wrap: none;
    white-space: nowrap;
    position: relative;
    padding-right: 20px;
    padding-left: 5px;
    outline: none;
    margin: 0;
    border-radius: 0;
  }
  button:focus-visible {
   outline: 4px solid gold;
}
  span {
    color: lightgrey;
    display: inline-block;
    position: absolute;
    right: 5px;
    top: 50%;
    margin-top: -10px;
  }
  .strong {
    font-weight: bold;
    color: black;
  }
  .acc {
    transform: rotate(180deg);
    margin-top: -5px;
  }
</style>
