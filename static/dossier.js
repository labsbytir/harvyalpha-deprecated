"use strict";
const root = document.querySelector("#dossier");
const artifactId = decodeURIComponent(location.pathname.split("/").filter(Boolean).pop() || "");
function node(tag, text) {
    const element = document.createElement(tag);
    if (text)
        element.textContent = text;
    return element;
}
function date(value) {
    if (!value)
        return "Date not provided";
    const parsed = typeof value === "number" ? new Date(value * 1000) : new Date(value);
    return Number.isNaN(parsed.valueOf()) ? String(value) : parsed.toLocaleString();
}
function originalLink(url) {
    if (!url || !/^https:\/\//i.test(url))
        return null;
    const link = node("a", "Open original source ↗");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.className = "p-link";
    return link;
}
const MASKED_EMAIL_RE = /\b[A-Za-z0-9._%+-]*\*\*\*[A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;
function formatTextWithEmailReveal(text, recordId) {
    const parts = [];
    let lastIndex = 0;
    let match;
    while ((match = MASKED_EMAIL_RE.exec(text)) !== null) {
        if (match.index > lastIndex) {
            parts.push(text.slice(lastIndex, match.index));
        }
        const wrap = node("span");
        wrap.className = "email-reveal-wrap";
        wrap.dataset.recordId = recordId;
        const maskedSpan = node("span", match[0]);
        maskedSpan.className = "masked-email";
        const btn = node("button", "View Email");
        btn.type = "button";
        btn.className = "btn-reveal-email";
        btn.dataset.recordId = recordId;
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            revealEmail(recordId, wrap, btn);
        });
        wrap.append(maskedSpan, btn);
        parts.push(wrap);
        lastIndex = match.index + match[0].length;
    }
    if (lastIndex < text.length) {
        parts.push(text.slice(lastIndex));
    }
    return parts.length ? parts : [text];
}
function pWithReveal(text, recordId) {
    const p = node("p");
    p.append(...formatTextWithEmailReveal(text, recordId));
    return p;
}
async function revealEmail(recordId, wrap, btn) {
    btn.disabled = true;
    btn.textContent = "Verifying...";
    try {
        let turnstileToken = "";
        const w = window;
        if (w.turnstile && typeof w.turnstile.getResponse === "function") {
            turnstileToken = w.turnstile.getResponse();
        }
        const res = await fetch(`/api/records/${encodeURIComponent(recordId)}/reveal`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ turnstileToken })
        });
        const data = await res.json();
        if (!res.ok) {
            btn.textContent = res.status === 429 ? (data.quota_exceeded ? "Quota Reached" : "Sign In") : "Error";
            btn.title = data.error || "Could not reveal email";
            if (res.status === 429 && !data.quota_exceeded) {
                btn.disabled = false;
                btn.onclick = (ev) => {
                    ev.preventDefault();
                    ev.stopPropagation();
                    const w = window;
                    if (typeof w.openAuthModal === "function")
                        w.openAuthModal();
                    else {
                        const trigger = document.getElementById("auth-nav-trigger");
                        if (trigger)
                            trigger.click();
                    }
                };
            }
            else {
                setTimeout(() => { btn.disabled = false; btn.textContent = "View Email"; }, 2500);
            }
            return;
        }
        const email = data.email || (data.emails && data.emails[0]);
        if (email) {
            const link = node("a", email);
            link.href = `mailto:${email}`;
            link.className = "revealed-email";
            wrap.replaceChildren(link);
        }
    }
    catch {
        btn.disabled = false;
        btn.textContent = "Error";
        setTimeout(() => { btn.textContent = "View Email"; }, 2000);
    }
}
function render(data) {
    if (!root)
        return;
    root.replaceChildren(node("a", "← BACK TO SEARCH"));
    root.firstElementChild.setAttribute("href", "/search/");
    root.firstElementChild.setAttribute("class", "nav-back");
    const { document: selected, profile, posts } = data;
    const title = node("h1", profile.title || selected.title || "Public record");
    const badge = node("span", (profile.source || selected.source || "public").toUpperCase());
    badge.className = "dossier-badge";
    const header = node("header");
    header.className = "dossier-header";
    header.append(title, badge, pWithReveal(profile.snippet || selected.snippet || "No profile summary was exposed.", profile.id || selected.id));
    root.append(header);
    if (selected.source === "posts") {
        const selectedCard = node("section");
        selectedCard.className = "dossier-card selected-post";
        selectedCard.append(node("h2", "Selected post"), pWithReveal(selected.body || selected.snippet || "No post text was exposed.", selected.id), node("time", date(selected.created_at)));
        const link = originalLink(selected.url);
        if (link)
            selectedCard.append(link);
        root.append(selectedCard);
    }
    const section = node("section");
    section.className = "dossier-card";
    section.append(node("h2", `Collected records (${posts.length})`));
    if (!posts.length)
        section.append(node("p", "No additional posts were indexed with this record."));
    for (const post of posts) {
        const item = node("article");
        item.className = "dossier-post";
        const view = node("a", post.title || post.snippet || "Open record");
        view.href = `/report/artifact/${encodeURIComponent(post.id)}`;
        item.append(view, node("time", date(post.created_at)));
        const link = originalLink(post.url);
        if (link)
            item.append(link);
        section.append(item);
    }
    root.append(section);
}
async function load() {
    if (!root || !artifactId)
        return;
    try {
        const isArtifact = location.pathname.includes("/report/artifact/");
        const dataUrl = isArtifact ? `/api/artifacts/${encodeURIComponent(artifactId)}` : root.dataset.reportJson;
        if (!dataUrl)
            throw new Error("Report data path is missing.");
        const response = await fetch(dataUrl);
        if (!response.ok)
            throw new Error(response.status === 404 ? "Record not found." : "Could not load record.");
        const data = await response.json();
        if (isArtifact)
            render(data);
        else
            renderExample(data);
    }
    catch (error) {
        root.replaceChildren(node("h1", "Record unavailable"), node("p", error instanceof Error ? error.message : "Could not load record."));
    }
}
function renderExample(data) {
    if (!root)
        return;
    root.replaceChildren();
    const back = node("a", "← BACK TO EXAMPLES");
    back.href = "/#examples";
    back.className = "nav-back";
    root.append(back);
    const target = data.target || { name: "Example" };
    const posts = data.posts || [];
    const header = node("header");
    header.className = "dossier-header";
    header.append(node("span", target.primary_surface || "PUBLIC SOURCES"), node("h1", target.name), node("p", target.title || "Public-source example"));
    if (target.surfaces?.length)
        header.append(node("p", `Surfaces: ${target.surfaces.join(" · ")}`));
    root.append(header);
    const metrics = data.telemetry;
    if (metrics) {
        const summary = node("section");
        summary.className = "dossier-card dossier-metrics";
        for (const [label, value] of Object.entries({
            "Posts captured": metrics.posts_captured ?? posts.length,
            "Reactions": metrics.aggregate_reactions ?? 0,
            "Shares": metrics.aggregate_shares ?? 0,
            "Comments": metrics.aggregate_comments ?? 0,
            "Outlinks": metrics.unique_outlinks ?? 0,
        })) {
            const card = node("div");
            card.append(node("strong", Number(value).toLocaleString()), node("span", label));
            summary.append(card);
        }
        root.append(summary);
    }
    const timeline = node("section");
    timeline.className = "dossier-card";
    timeline.append(node("h2", `Public posts (${posts.length})`));
    for (const [index, post] of posts.entries()) {
        const item = node("article");
        item.className = "dossier-post";
        const meta = [post.surface || post.type, post.created_at || post.timestamp ? date(post.created_at || post.timestamp) : ""].filter(Boolean).join(" · ");
        item.append(node("span", meta), node("p", post.text || "No text was exposed."));
        const link = originalLink(post.url);
        if (link)
            item.append(link);
        timeline.append(item);
    }
    root.append(timeline);
}
void load();
