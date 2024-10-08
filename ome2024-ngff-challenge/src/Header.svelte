<script>

  export let tableRows = [];

  $: zarr_url_count = tableRows.reduce(
    (acc, row) => acc + (row.csv_row_count || 0),
    0
  );
  $: csv_file_count = tableRows.reduce(
    (acc, row) => acc + (row.csv_row_count ? 1 : 0),
    0
  );
</script>

{#if zarr_url_count > 0}
  <h2>
    {zarr_url_count} zarrs in {csv_file_count} collections
  </h2>
{/if}
