(() => {
  const content = document.getElementById("privacy-policy");
  if (!content) return;
  fetch("/static/privacy.md", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error("Privacy policy unavailable.");
      return response.text();
    })
    .then((text) => { content.textContent = text; })
    .catch(() => { content.textContent = "Privacy policy unavailable. Please try again later."; });
})();
