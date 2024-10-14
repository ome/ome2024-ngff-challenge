
<script>
  import omelogo from "/ome-main-nav.svg"
</script>

<nav>
  <img style="height: 30px" alt="OME Logo" src="{omelogo}"/>
  <h2>2024 NGFF Challenge</h2>

  <ul>
    <li>
      <a href="https://github.com/ome/ome2024-ngff-challenge/" target="_blank">
        About
    </li>
  </ul>
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
  }

  h2 {
    color: white;
    font-weight: 300;
    margin: 5px 15px;
  }

  ul {
    list-style: none;
    color: white;
    position: absolute;
    right: 0;
    top: 0;
    margin: 10px 15px;
  }

  li {
    float: right;
    list-style-type: none;
    margin: 0 10px;
  }
  a {
    color: white;
    text-decoration: none;
    line-height: 2.3;
  }

</style>
