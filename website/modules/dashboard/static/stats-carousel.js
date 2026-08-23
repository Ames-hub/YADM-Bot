const statsRow = document.getElementById("stats-row");

// TODO: If anyone knows how to fix this so it fits perfectly on the carousel, that'd be great. Right now its "Good enough."
statsRow.addEventListener("wheel", (event) => {
    event.preventDefault();

    statsRow.scrollBy({
        top: event.deltaY > 0 ? 200 : -200,
        behavior: "smooth"
    });
}, { passive: false });