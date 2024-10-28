<div>
  <h2>Introduction</h2>
  <p>
    The <a href="https://forum.image.sc/t/ome2024-ngff-challenge/97363">2024 OME-NGFF Challenge</a>
    was conceived at the
    <a href="https://www.openmicroscopy.org/events/ome-community-meeting-2024/">
      OME Annual Community Meeting</a>
    in Dundee in May 2024. The stated goals of Challenge were:
  </p>

  <ul>
    <li>
      Advance the status of OME-Zarr specification proposals —
      <a href="https://ngff.openmicroscopy.org/rfc/">Requests for Comment (RFC)</a> —
      especially the adoption of the Zarr V3 specification
    </li>
    <li>
      by collecting the URLs of converted examples of OME-Zarr from multiple modalities, use cases, and
      institutions, all hosted by each participant themselves
    </li>
    <li>
      in order to test the level of maturity of OME-Zarr conversion tools, image viewers,
      and metadata in general.
    </li>
  </ul>
  <p>
    The inspiration for the Challenge came from presentations at the OME Meeting
    that demonstrated the level of adoption of OME-Zarr and the relative ease of
    conversion for some community members, but highlighted the often poor findability of the data
    and the need for driving the OME-Zarr specification towards version 1.0.
  <p>
    A lofty goal of 1 Petabyte (PB) of data was set, mostly to make clear the scale of what <em>could be</em>.
  </p>
  <p>
    Work on the challenge started in earnest in July 2024. All progress is
    tracked in the <a href="https://github.com/ome/ome2024-ngff-challenge">ome2024-ngff-challenge</a>
    repository. It was agreed that the deadline for submission would be such that the results
    of the OME-NGFF Challenge could be presented at the
    <a href="https://globalbioimaging.org/exchange-of-experience/exchange-of-experience-ix">
      2024 Global BioImaging Meeting</a>.
  </p>

  <h2>Process</h2>
  <p>
    The Challenge was run via a series of virtual meetings open to all which were coordinated on the
    Image.sc Forums, with all
    <a href="https://hackmd.io/3emKqKQsT_2U35vLepzDEQ">notes and lists of participants</a>
    available. Initial meetings including that at OME2024 focused on defining the scope of
    changes that would be made to the OME-Zarr format. A Python-based tool to convert data
    to this format was built. Submissions were then collected in simple CSV files with a Zarr
    URL per row.
  </p>

  <h2>Results</h2>
  <p>
    At the outset, it was unclear how much OME-Zarr data was available, if it
    could be converted to Zarr V3, and how many organisations would participate.
    In the end, we are pleased with the more than 500 Terabytes of data which
    have been made available, across a wide range of modalities.
  </p>
  <p>
    To make the collection as accessible as possible, the
  <a href="https://ome.github.io/ome2024-ngff-challenge">OME-NGFF Challenge Viewer</a>,
    was built which uses a CSV with locations of
    datasets to enable collection statistics, browsing of thumbnails, and opening 
    the datasets with the OME NGFF Validator, for metadata
    validation and viewing. Please let us know on image.sc or GitHub if you have any issues
    or ideas.
  </p>
  <p>
    Looking back, perhaps the most rewording outcome of the Challenge is that with a remarkably
    modest investment of time and cloud resources, we have almost inadvertently prototyped
    a federated bioimage data system based on OME-Zarr. To our knowledge, this
    is the largest federated bioimage data collection ever assembled.
  </p>
</div>

<style>
  div {
    margin: 15px;
  }
</style>
