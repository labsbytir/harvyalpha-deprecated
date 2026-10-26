(() => {
  const content = document.getElementById("policy-doc") || document.getElementById("privacy-policy");
  if (!content) return;
  const source = content.dataset.doc || "/static/privacy.md";
  fetch(source, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error("Document unavailable.");
      return response.text();
    })
    .then((text) => { content.textContent = text; })
    .catch(() => { content.textContent = "Document unavailable. Please try again later."; });
})();
