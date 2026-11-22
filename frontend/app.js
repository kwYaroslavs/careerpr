document.addEventListener("DOMContentLoaded", () => {
    const factForm = document.getElementById("fact-form");
    const refreshFactsBtn = document.getElementById("refresh-facts-btn");
    const factsContainer = document.getElementById("facts-container");

    const API_BASE = "http://localhost:8000";

    async function fetchFacts() {
        factsContainer.innerHTML = "<p>Loading facts...</p>";
        try {
            const response = await fetch(`${API_BASE}/facts`);
            if (!response.ok) {
                throw new Error(`Failed to load facts: ${response.statusText}`);
            }
            const facts = await response.json();
            renderFacts(facts);
        } catch (error) {
            factsContainer.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        }
    }

    function renderFacts(facts) {
        if (!facts || facts.length === 0) {
            factsContainer.innerHTML = "<p>No facts found in Fact Base.</p>";
            return;
        }

        factsContainer.innerHTML = "";
        facts.forEach(fact => {
            const item = document.createElement("div");
            item.className = "fact-item";

            const badgeClass = fact.verification_status || "unverified";

            item.innerHTML = `
                <div class="fact-header">
                    <span>${escapeHtml(fact.id)}</span>
                    <span class="badge ${badgeClass}">${escapeHtml(fact.verification_status)}</span>
                </div>
                <div class="fact-body">${escapeHtml(fact.text)}</div>
                <div class="fact-meta">
                    Category: ${escapeHtml(fact.category)} | Risk: ${escapeHtml(fact.risk_tier)} | Evidence: ${escapeHtml(fact.evidence_ref || "None")}
                </div>
            `;
            factsContainer.appendChild(item);
        });
    }

    factForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const payload = {
            id: document.getElementById("fact-id").value.trim(),
            text: document.getElementById("fact-text").value.trim(),
            category: document.getElementById("fact-category").value.trim(),
            risk_tier: document.getElementById("fact-risk").value,
            verification_status: document.getElementById("fact-verification").value,
            evidence_ref: document.getElementById("fact-evidence").value.trim() || null
        };

        try {
            const response = await fetch(`${API_BASE}/facts`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || response.statusText);
            }

            alert("Fact successfully created!");
            factForm.reset();
            fetchFacts();
        } catch (error) {
            alert(`Failed to create fact: ${error.message}`);
        }
    });

    refreshFactsBtn.addEventListener("click", fetchFacts);

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&")
            .replace(/</g, "<")
            .replace(/>/g, ">")
            .replace(/"/g, """)
            .replace(/'/g, "&#039;");
    }

    // Initial load
    fetchFacts();
});
