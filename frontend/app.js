document.addEventListener("DOMContentLoaded", () => {
    const API_BASE = "http://localhost:8000";

    // 1. Facts Management
    const factForm = document.getElementById("fact-form");
    const refreshFactsBtn = document.getElementById("refresh-facts-btn");
    const factsContainer = document.getElementById("facts-container");

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
                headers: { "Content-Type": "application/json" },
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

    // 2. Job & Requirements Management
    const jobForm = document.getElementById("job-form");
    const jobResult = document.getElementById("job-result");
    const requirementsContainer = document.getElementById("requirements-container");

    jobForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const title = document.getElementById("job-title").value.trim();
        const company = document.getElementById("job-company").value.trim();
        const description = document.getElementById("job-text").value.trim();

        jobResult.innerHTML = "<p>Creating job and extracting requirements...</p>";
        requirementsContainer.innerHTML = "";

        try {
            // Create Job
            const jobRes = await fetch(`${API_BASE}/jobs`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, company, description })
            });

            if (!jobRes.ok) {
                const errData = await jobRes.json();
                throw new Error(errData.detail || jobRes.statusText);
            }

            const job = await jobRes.json();
            jobResult.innerHTML = `<p style="color: green;">Job created! ID: <strong>${escapeHtml(job.id)}</strong></p>`;
            
            // Auto fill snapshot job ID
            document.getElementById("snapshot-job-id").value = job.id;

            // Extract / Batch requirements
            const reqRes = await fetch(`${API_BASE}/requirements/batch`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_id: job.id, jd_text: description })
            });

            if (!reqRes.ok) {
                throw new Error("Failed to extract requirements");
            }

            const requirements = await reqRes.json();
            renderRequirements(requirements);
            fetchProposals();
        } catch (error) {
            jobResult.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        }
    });

    function renderRequirements(reqs) {
        if (!reqs || reqs.length === 0) {
            requirementsContainer.innerHTML = "<p>No requirements extracted.</p>";
            return;
        }

        let html = "<h4>Extracted Requirements & Evidence Map:</h4>";
        reqs.forEach(req => {
            html += `
                <div class="requirement-item">
                    <strong>${escapeHtml(req.req_id)}</strong> (${escapeHtml(req.category)} - Match: <strong>${escapeHtml(req.match_category)}</strong>)<br>
                    <span>${escapeHtml(req.requirement_text)}</span><br>
                    <small>Evidence IDs: ${req.matched_fact_ids ? escapeHtml(JSON.stringify(req.matched_fact_ids)) : "None"}</small>
                </div>
            `;
        });
        requirementsContainer.innerHTML = html;
    }

    // 3. Proposals & Stretch Panel Review
    const refreshProposalsBtn = document.getElementById("refresh-proposals-btn");
    const proposalsContainer = document.getElementById("proposals-container");
    const stretchContainer = document.getElementById("stretch-container");

    async function fetchProposals() {
        proposalsContainer.innerHTML = "<p>Loading proposals...</p>";
        stretchContainer.innerHTML = "<p>Loading stretch items...</p>";
        try {
            const response = await fetch(`${API_BASE}/proposals`);
            if (!response.ok) {
                throw new Error("Failed to load proposals");
            }
            const proposals = await response.json();
            renderProposals(proposals);
        } catch (error) {
            proposalsContainer.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            stretchContainer.innerHTML = `<p style="color: red;">Error loading stretch items</p>`;
        }
    }

    function renderProposals(proposals) {
        if (!proposals || proposals.length === 0) {
            proposalsContainer.innerHTML = "<p>No proposals found.</p>";
            stretchContainer.innerHTML = "<p>No stretch items found.</p>";
            return;
        }

        proposalsContainer.innerHTML = "";
        stretchContainer.innerHTML = "";

        let stretchCount = 0;

        proposals.forEach(prop => {
            const item = document.createElement("div");
            item.className = "proposal-item";
            const statusBadge = prop.status || "proposed";

            item.innerHTML = `
                <div class="fact-header">
                    <span>Proposal: ${escapeHtml(prop.proposal_id)} (Job: ${escapeHtml(prop.job_id)})</span>
                    <span class="badge ${statusBadge}">${escapeHtml(prop.status)}</span>
                </div>
                <div class="proposal-body">
                    <strong>Target:</strong> ${escapeHtml(prop.target)}<br>
                    <strong>Original:</strong> ${escapeHtml(prop.original_text || "N/A")}<br>
                    <strong>Proposed:</strong> ${escapeHtml(prop.proposed_text)}<br>
                    <small>Rationale: ${escapeHtml(prop.rationale)} | Risk: ${escapeHtml(prop.risk_level)} | Is Stretch: ${prop.is_stretch ? "Yes" : "No"}</small>
                </div>
                <div class="controls mt-15">
                    <button onclick="updateProposalStatus('${prop.proposal_id}', 'approved', ${prop.is_stretch})">Approve</button>
                    <button style="background-color: #dc2626;" onclick="updateProposalStatus('${prop.proposal_id}', 'rejected', ${prop.is_stretch})">Reject</button>
                </div>
            `;
            proposalsContainer.appendChild(item);

            // Stretch Panel filter
            if (prop.is_stretch) {
                stretchCount++;
                const stretchItem = document.createElement("div");
                stretchItem.className = "fact-item";
                stretchItem.innerHTML = `
                    <div class="fact-header">
                        <span>Stretch Item (${escapeHtml(prop.risk_level)})</span>
                        <span class="badge user_stretch">Stretch</span>
                    </div>
                    <div class="fact-body">${escapeHtml(prop.proposed_text)}</div>
                    <div class="controls mt-15">
                        <button onclick="updateProposalStatus('${prop.proposal_id}', 'approved', true)">Accept Stretch</button>
                        <button style="background-color: #dc2626;" onclick="updateProposalStatus('${prop.proposal_id}', 'rejected', true)">Reject Stretch</button>
                    </div>
                `;
                stretchContainer.appendChild(stretchItem);
            }
        });

        if (stretchCount === 0) {
            stretchContainer.innerHTML = "<p>No stretch suggestions with risk labels R0-R2 requiring review.</p>";
        }

        // Auto fill snapshot proposal ID if available
        if (proposals.length > 0) {
            document.getElementById("snapshot-proposal-id").value = proposals[0].proposal_id;
        }
    }

    window.updateProposalStatus = async function(proposalId, status, isStretch) {
        try {
            const response = await fetch(`${API_BASE}/proposals/${proposalId}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status, actor: "user", is_stretch: isStretch })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Failed to update proposal status");
            }

            alert(`Proposal ${proposalId} status updated to ${status}`);
            fetchProposals();
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    };

    refreshProposalsBtn.addEventListener("click", fetchProposals);

    // 4. Snapshot Export
    const snapshotForm = document.getElementById("snapshot-form");
    const snapshotResult = document.getElementById("snapshot-result");

    snapshotForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const jobId = document.getElementById("snapshot-job-id").value.trim();
        const proposalId = document.getElementById("snapshot-proposal-id").value.trim();

        snapshotResult.innerHTML = "<p>Exporting ready snapshot...</p>";

        try {
            const response = await fetch(`${API_BASE}/applications/snapshots`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ job_id: jobId, proposal_id: proposalId })
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Failed to export snapshot");
            }

            const snapshot = await response.json();
            snapshotResult.innerHTML = `
                <div style="background: #d1fae5; padding: 10px; border-radius: 4px; color: #065f46;">
                    <strong>Snapshot Exported Successfully!</strong><br>
                    Content Hash: <code>${escapeHtml(snapshot.content_hash)}</code><br>
                    Generated At: ${escapeHtml(snapshot.generated_at)}
                </div>
            `;
        } catch (error) {
            snapshotResult.innerHTML = `<p style="color: red;">Error: ${escapeHtml(error.message)}</p>`;
        }
    });

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&")
            .replace(/</g, "<")
            .replace(/>/g, ">")
            .replace(/"/g, """)
            .replace(/'/g, "&#039;");
    }

    // Initial loads
    fetchFacts();
    fetchProposals();
});
