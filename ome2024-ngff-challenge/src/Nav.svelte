<script>
  import omeMainNav from "/ome-main-nav.svg";
  import githubLogo from "/github-mark-white.svg";
</script>

<nav>
  <a class="logolink" href="/"><img alt="OME Logo" src={omeMainNav} /></a>
  <a href="/"><h2>2024 NGFF Challenge</h2></a>
  <div style="flex: 1"></div>

  <a href="/about/"> About </a>
  <a class="github" title="Open in GitHub" target="_blank" href="https://github.com/ome/ome2024-ngff-challenge/">
    <img alt="GitHub Logo" src={githubLogo} />
  </a>
</nav>

<style>
  nav {
    top: 0;
    left: 0;
    width: 100%;
    display: flex;
    flex-direction: row;
    margin: 0;
    padding: 5px 15px;
    background-color: #202428;
    z-index: 20;
    align-items: center;
    box-sizing: border-box;
    flex: auto 0 0;
    gap: 5px;
  }

  h2 {
    color: white;
    font-weight: 300;
    margin: 5px 15px;
  }
  a {
    color: white;
    text-decoration: none;
    display: block;
  }
  .logolink, img {
    height: 30px;
  }
  .github img, .github {
    height: 20px;
  }
  .github {
    margin: 0 10px;
  }
</style>
