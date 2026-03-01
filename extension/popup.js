const fillBtn = document.getElementById('fillBtn');
const micBtn = document.getElementById('micBtn');
const statusDiv = document.getElementById('status');
const aiDataDiv = document.getElementById('aiData');
const spinner = document.getElementById('spinner');
const payBtn = document.getElementById('payBtn');
const pdfBtn = document.getElementById('pdfBtn');
const waBtn = document.getElementById('waBtn');
const actionButtons = document.getElementById('actionButtons');
const agentPdfBtn = document.getElementById('agentPdfBtn');

let currentPaymentLink = "";
let currentText = "";

function showSpinner() {
    spinner.style.display = "block";
}

function hideSpinner() {
    spinner.style.display = "none";
}

async function processText(text) {

    showSpinner();
    statusDiv.innerText = "AI Processing...";

    try {

        // CALL UNIFIED ENDPOINT
        const response = await fetch('http://127.0.0.1:8000/tbo/ai-search-trip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });

        if (!response.ok) {
            throw new Error("Backend HTTP error: " + response.status);
        }

        const data = await response.json();
        currentText = text;

        if (data.PaymentLink) {
            currentPaymentLink = data.PaymentLink;
            actionButtons.style.display = "block";
        }

        console.log("FULL BACKEND RESPONSE:", data);

        // SAFE AI extraction
        let ai = {};

        if (data && data.AI_Extracted) {
            ai = data.AI_Extracted;
        }

        if (!ai || Object.keys(ai).length === 0) {

            aiDataDiv.innerHTML = `
                <div style="color:red;">
                    Backend returned empty AI extraction.<br>
                    Check FastAPI terminal.
                </div>
            `;

            statusDiv.innerText = "Backend Error";
            hideSpinner();
            return;
        }

        // ===============================
        // FLIGHT DISPLAY
        // ===============================

        let flightsHTML = "";

        if (data.TopFlights && Array.isArray(data.TopFlights) && data.TopFlights.length > 0) {

            flightsHTML += `
                <hr>
                <div class="badge">Top Commission Flights</div>
            `;

            data.TopFlights.forEach((flight, index) => {

                flightsHTML += `
                    <div style="
                        background:#f0f9ff;
                        padding:8px;
                        border-radius:6px;
                        margin-top:6px;
                        border-left:4px solid #3b82f6;
                    ">
                        <div class="highlight">
                            ${index + 1}. ${flight.Airline || "Unknown Airline"}
                        </div>

                        <div>
                            Price: ₹${flight.SellingPrice ?? "N/A"}
                        </div>

                        <div style="color:blue;">
                            Commission: ₹${flight.Commission ?? "0"}
                            (${flight.CommissionPercent ?? "0"}%)
                        </div>
                    </div>
                `;
            });
        }

        // ===============================
        // HOTEL DISPLAY
        // ===============================

        let hotelsHTML = "";

        if (data.TopHotels && Array.isArray(data.TopHotels) && data.TopHotels.length > 0) {

            hotelsHTML += `
                <hr>
                <div class="badge">Top Commission Hotels</div>
            `;

            data.TopHotels.forEach((hotel, index) => {

                hotelsHTML += `
                    <div style="
                        background:#f8fafc;
                        padding:8px;
                        border-radius:6px;
                        margin-top:6px;
                        border-left:4px solid #22c55e;
                    ">

                        <div class="highlight">
                            ${index + 1}. ${hotel.HotelName || "Unknown Hotel"}
                        </div>

                        <div>
                            Room: ${hotel.RoomName || "Standard Room"}
                        </div>

                        <div>
                            Price: ₹${hotel.SellingPrice ?? "N/A"}
                        </div>

                        <div style="color:green;">
                            Commission: ₹${hotel.Commission ?? "0"}
                            (${hotel.CommissionPercent ?? "0"}%)
                        </div>

                    </div>
                `;
            });
        }

        // ===============================
        // MAIN DISPLAY
        // ===============================

        aiDataDiv.innerHTML = `

            <div>
                <strong>Destination:</strong>
                ${ai.destination || "Missing"}
            </div>

            <div>
                <strong>Check-in:</strong>
                ${ai.checkin || "Missing"}
            </div>

            <div>
                <strong>Check-out:</strong>
                ${ai.checkout || "Missing"}
            </div>

            <div>
                <strong>Travelers:</strong>
                ${ai.travelers ?? "Missing"}
            </div>

            <div>
                <strong>Budget:</strong>
                ₹${ai.budget ?? "N/A"}
            </div>

            <hr>

            <div>
                <strong>Confidence:</strong>
                ${ai.confidence_score ?? 0}%
            </div>

            ${
                ai.alert
                ? `<div style="color:red;">
                    <strong>Alert:</strong> ${ai.alert}
                   </div>`
                : ""
            }

            <hr>

            <div style="
                background:#f3f4f6;
                padding:10px;
                border-radius:8px;
            ">
                <strong>AI Travel Insights:</strong><br>
                ${ai.ai_summary || "No insights generated."}
            </div>

            ${
                ai.memory_insight
                ? `<div style="margin-top:8px;">
                    <strong>Memory Insight:</strong><br>
                    ${ai.memory_insight}
                   </div>`
                : ""
            }

            ${flightsHTML}

            ${hotelsHTML}

            <hr>

            <div style="background:#ecfeff;padding:8px;border-radius:6px;margin-top:6px;">
            <strong>Total Trip Price:</strong>
            ₹${data.TotalTripPrice ?? "N/A"}
            </div>

            <div style="background:#f0fdf4;padding:8px;border-radius:6px;margin-top:6px;">
            <strong>Total Commission:</strong>
            ₹${data.TotalCommission ?? "N/A"}
            </div>

            ${
            data.PaymentLink
            ?
            `<div style="margin-top:8px;">
            <strong>Payment Link:</strong><br>
            <a href="${data.PaymentLink}" target="_blank">
            ${data.PaymentLink}
            </a>
            </div>`
            :
            ""
            }

        `;

        // AUTOFILL
        const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true
        });

        if (tab) {

            chrome.tabs.sendMessage(tab.id, {
                action: "autoFillDirect",
                data: ai
            });

        }

        statusDiv.innerText = "Autofill Completed ✅";

        hideSpinner();

    }
    catch (err) {

        console.error("POPUP ERROR:", err);

        aiDataDiv.innerHTML = `
            <div style="color:red; padding:10px;">
                ❌ Backend connection failed<br><br>
                Please ensure FastAPI server is running.<br><br>
                Error: ${err.message}
            </div>
        `;

        statusDiv.innerText = "Backend Error ❌";

        hideSpinner();
    }
}


// ===============================
// TEXT BUTTON
// ===============================

fillBtn.addEventListener('click', () => {

    const text = prompt("Enter booking request:");

    if (text && text.trim().length > 0) {
        processText(text.trim());
    }
});


// ===============================
// VOICE BUTTON
// ===============================

micBtn.addEventListener('click', () => {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        statusDiv.innerText = "Speech recognition not supported.";

        return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = 'en-US';

    recognition.onstart = () => {

        statusDiv.innerText = "Listening...";
    };

    recognition.onresult = (event) => {

        const text = event.results[0][0].transcript;

        processText(text);
    };

    recognition.onerror = (event) => {

        statusDiv.innerText = "Mic error: " + event.error;
    };

    recognition.start();
});


// ===============================
// PAY BUTTON
// ===============================

payBtn.addEventListener('click', () => {

    if (!currentPaymentLink) {

        alert("Payment link not available");

        return;
    }

    chrome.windows.create({
    url: data.WhatsAppLink,
    type: "popup",
    width: 500,
    height: 700
});

});


// ===============================
// PDF BUTTON
// ===============================

pdfBtn.addEventListener('click', async () => {

    if (!currentText) {

        alert("No booking request found");
        return;

    }

    try {

        const response = await fetch(
            'http://127.0.0.1:8000/generate-user-pdf',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: currentText
                })
            }
        );

        if (!response.ok) {

            alert("Backend PDF generation failed");
            return;

        }

        const data = await response.json();

        if (!data.pdf_file) {

            alert("PDF file path missing");
            return;

        }

        const pdfUrl =
            "http://127.0.0.1:8000/" + data.pdf_file;

        console.log("Downloading PDF:", pdfUrl);

        chrome.downloads.download({

            url: pdfUrl,

            filename: data.pdf_file.split("/").pop(),

            saveAs: true

        });

    }
    catch (err) {

        console.error(err);

        alert("PDF download failed");

    }

});

// ===============================
// WHATSAPP BUTTON
// ===============================

waBtn.addEventListener('click', async () => {

    if (!currentText) {

        alert("No booking request found");

        return;
    }

    try {

        const response = await fetch(
            'http://127.0.0.1:8000/send-whatsapp-quote',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: currentText
                })
            }
        );

        const data = await response.json();

        if (data.WhatsAppLink) {

            chrome.windows.create({
    url: data.WhatsAppLink,
    type: "popup",
    focused: false,
    width: 500,
    height: 700
});

        }

    } catch (e) {

        alert("WhatsApp failed");

    }

});


agentPdfBtn.addEventListener('click', async () => {

    if (!currentText) {

        alert("No booking request found");

        return;
    }

    try {

        const response = await fetch(
            'http://127.0.0.1:8000/generate-agent-pdf',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    text: currentText
                })
            }
        );

        const data = await response.json();

        if (data.pdf_file) {

            chrome.downloads.download({
                url: "http://127.0.0.1:8000/" + data.pdf_file,
                filename: data.pdf_file.split("/").pop(),
                saveAs: true
            });

        }

    } catch (e) {

        alert("Agent PDF generation failed");

    }

});

const dashboardBtn =
    document.getElementById("dashboardBtn");

dashboardBtn.addEventListener(
    "click",
    () => {

        chrome.tabs.create({

            url: "http://127.0.0.1:8000/dashboard"

        });

});