<script>
  export let toggleAscending;
  export let sortAscending;
</script>

<button on:click={() => toggleAscending()}>
  <span class="acc" class:strong={sortAscending}>^</span>
  <span class="dec" class:strong={!sortAscending}>^</span>
</button>

<style>
  button {
    background-color: var(--light-background);
    border: solid var(--border-color) 1px;
    border-radius: 5px;
    text-wrap: none;
    white-space: nowrap;
    position: relative;
    padding: 9px 10px 11px 10px;
    outline: none;
    margin: 0;
    height: 35px;
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
