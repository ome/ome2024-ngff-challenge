
<script>
  import Main from "./Main.svelte";
  import Nav from "./Nav.svelte";
  import About from "./About.svelte";

  let base = import.meta.env.BASE_URL;

  console.log('base', base);

  let pathname = window.location.pathname;
</script>

<div class="app">
  <!-- base element used to define relative links -->
  <base href="{base}" />

  <Nav />

  {#if pathname.endsWith("/about/")}
    <About />
  {:else}
    <Main />
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
