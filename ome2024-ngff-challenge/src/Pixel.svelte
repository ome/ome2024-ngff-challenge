
<script>

  import { fade } from 'svelte/transition';

  function getRandomInt(max) {
    return Math.floor(Math.random() * max);
  }

  let innerWidth = 0;
  let innerHeight = 0;
  let x = 0;
  let y = 0;
  let show = false;
  let duration = getRandomInt(5000);

  function update() {
    x = getRandomInt(innerWidth / 20) * 20;
    y = getRandomInt(innerHeight / 20) * 20;
    show = true;
  }

  function fadeOut() {
    duration = 2000 + getRandomInt(5000);
    setTimeout(() => {
      show = false;
    }, duration);
  }

  setTimeout(update, getRandomInt(10000));
</script>

<svelte:window bind:innerWidth bind:innerHeight />

{#if show}
  <div transition:fade={{ duration: 5000 }}
    on:introend={fadeOut}
    on:outroend={update}
    style:left="{x}px" style:top="{y}px" class="pixel"></div>
{/if}

<style>
  .pixel {
    height: 20px;
    width: 20px;
    background-color: rgb(227, 227, 227);
    position: absolute;
    z-index: 0;
  }
</style>
