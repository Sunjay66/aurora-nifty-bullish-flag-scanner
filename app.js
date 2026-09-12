let scannerData = null;
let currentRows = [];

async function loadScanner() {

    try {

        const response = await fetch("data/scanner.json");

        if (!response.ok) {
            throw new Error("Unable to load scanner.json");
        }

        scannerData = await response.json();

        currentRows = scannerData.current_structures || [];

        updateSummary();
        renderTable();
        updateGeneratedTime();

    } catch (error) {

        console.error(error);

        document.getElementById("resultsBody").innerHTML =
            `<tr>
                <td colspan="11">
                    Unable to load Aurora scanner data.
                </td>
            </tr>`;
    }
}


function updateSummary() {

    const summary = scannerData.summary || {};

    document.getElementById("totalStructures").textContent =
        summary.total_production_structures ?? "—";

    document.getElementById("breakouts").textContent =
        summary.current_breakouts ?? "—";

    document.getElementById("activeFlags").textContent =
        summary.current_active_flags ?? "—";

    const scored = currentRows.filter(
        row => row.Aurora_Flag_Score_80 !== null &&
               row.Aurora_Flag_Score_80 !== undefined
    );

    if (scored.length > 0) {

        const highest = Math.max(
            ...scored.map(
                row => Number(row.Aurora_Flag_Score_80)
            )
        );

        document.getElementById("highestScore").textContent =
            `${highest.toFixed(0)} / 80`;

    } else {

        document.getElementById("highestScore").textContent = "—";
    }
}


function scoreClass(score) {

    if (score >= 60) {
        return "score-high";
    }

    if (score >= 30) {
        return "score-mid";
    }

    return "score-low";
}


function statusClass(status) {

    if (status === "BREAKOUT") {
        return "status status-breakout";
    }

    return "status status-active";
}


function renderTable() {

    const statusFilter =
        document.getElementById("statusFilter").value;

    const scoreFilter =
        Number(document.getElementById("scoreFilter").value);

    let rows = currentRows.filter(row => {

        const statusMatch =
            statusFilter === "ALL" ||
            row.Status === statusFilter;

        const score =
            row.Aurora_Flag_Score_80;

        const scoreMatch =
            scoreFilter === 0 ||
            (score !== null &&
             score !== undefined &&
             Number(score) >= scoreFilter);

        return statusMatch && scoreMatch;
    });


    rows.sort((a, b) => {

        const scoreA =
            a.Aurora_Flag_Score_80 ?? -1;

        const scoreB =
            b.Aurora_Flag_Score_80 ?? -1;

        return Number(scoreB) - Number(scoreA);
    });


    const body =
        document.getElementById("resultsBody");

    const empty =
        document.getElementById("emptyState");

    body.innerHTML = "";


    rows.forEach((row, index) => {

        const score =
            row.Aurora_Flag_Score_80;

        const scoreText =
            score === null ||
            score === undefined
                ? "—"
                : `${Number(score).toFixed(0)}`;

        const tr =
            document.createElement("tr");

        tr.innerHTML = `
            <td>${index + 1}</td>

            <td class="stock">
                ${row.Stock ?? "—"}
            </td>

            <td>
                <span class="${statusClass(row.Status)}">
                    ${row.Status ?? "—"}
                </span>
            </td>

            <td class="score ${
                score !== null &&
                score !== undefined
                    ? scoreClass(Number(score))
                    : ""
            }">
                ${scoreText}
            </td>

            <td>
                ${row.Flag_Structure_Score ?? "—"}
            </td>

            <td>
                ${row.EMA_Health_Score ?? "—"}
            </td>

            <td>
                ${row.Relative_Strength_Score ?? "—"}
            </td>

            <td>
                ${row.Volume_Profile_Score ?? "—"}
            </td>

            <td>
                ${row.Location_Score ?? "—"}
            </td>

            <td>
                ${row.Trend_Alignment_Score ?? "—"}
            </td>

            <td>
                ${row.pole_end_date ?? "—"}
            </td>
        `;

        body.appendChild(tr);
    });


    empty.style.display =
        rows.length === 0
            ? "block"
            : "none";
}


function updateGeneratedTime() {

    const timestamp =
        scannerData.generated_at;

    if (!timestamp) {
        return;
    }

    document.getElementById("generatedAt").textContent =
        `Data generated ${timestamp}`;
}


document
    .getElementById("statusFilter")
    .addEventListener(
        "change",
        renderTable
    );

document
    .getElementById("scoreFilter")
    .addEventListener(
        "change",
        renderTable
    );


loadScanner();
