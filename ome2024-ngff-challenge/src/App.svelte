
<script>
  import Main from "./Main.svelte";
  import Nav from "./Nav.svelte";
  import About from "./About.svelte";


  let pathname = window.location.pathname;
</script>

<div class="app">
  <Nav />

{#if pathname === "/"}
  <Main />
{:else if pathname === "/about/"}
  <About />
{:else}
  <div>
    <h1>404</h1>
    <p>Page not found</p>
  </div>
{/if}

</div>

<style>
.app {
  margin: 0;
  padding: 0;
  inset: 0;
  display: flex;
  flex-direction: column;
}
</style>
