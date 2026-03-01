try {

// ===============================
// 1️⃣ PORTAL SCHEMA CONFIG
// ===============================

const portalSchemas = {
    test: {
        match: () => document.querySelector('#ss'),
        fields: {
            destination: '#ss',
            checkin: '#date-input'
        }
    },
    booking: {
        match: () => window.location.hostname.includes("booking.com"),
        fields: {
            destination: 'input[name="ss"]',
            checkin: 'input[type="date"]'
        }
    },
    expedia: {
        match: () => window.location.hostname.includes("expedia.com"),
        fields: {
            destination: '[data-stid="location-field-leg1-origin-menu-trigger"] input',
            checkin: 'input[type="date"]'
        }
    }
};

function detectPortal() {
    for (let key in portalSchemas) {
        try {
            if (portalSchemas[key].match()) {
                return portalSchemas[key];
            }
        } catch (e) {}
    }
    return null;
}

// ===============================
// 2️⃣ INPUT TRIGGER ENGINE
// ===============================

function triggerInput(element, value) {
    const lastValue = element.value;
    element.value = value;

    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    element.dispatchEvent(new Event('blur', { bubbles: true }));

    const tracker = element._valueTracker;
    if (tracker) tracker.setValue(lastValue);
}

// ===============================
// 3️⃣ DYNAMIC AUTOFILL ENGINE
// ===============================

function fillFormFields(data) {

    const portal = detectPortal();
    if (!portal) {
        console.log("Portal not supported.");
        return false;
    }

    let filled = false;

    for (let field in portal.fields) {

        const selector = portal.fields[field];
        const element = document.querySelector(selector);

        if (!element || !data[field]) continue;

        if (element.type === "date") {
            const dateObj = new Date(data[field]);
            if (!isNaN(dateObj.getTime())) {
                element.valueAsDate = dateObj;
            } else {
                element.value = data[field];
            }
        } else {
            element.value = data[field];
        }

        triggerInput(element, element.value);
        filled = true;
    }

    return filled;
}

// ===============================
// 4️⃣ VERIFICATION OVERLAY (ONLY FOR MISSING DATA)
// ===============================

function showVerificationOverlay(data) {

    const existing = document.getElementById("voyagehack-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.id = "voyagehack-overlay";

    overlay.style.position = "fixed";
    overlay.style.top = "50%";
    overlay.style.left = "50%";
    overlay.style.transform = "translate(-50%, -50%)";
    overlay.style.background = "white";
    overlay.style.padding = "20px";
    overlay.style.width = "400px";
    overlay.style.zIndex = "999999";
    overlay.style.borderRadius = "12px";
    overlay.style.boxShadow = "0 10px 30px rgba(0,0,0,0.3)";
    overlay.style.fontFamily = "Segoe UI, sans-serif";

    overlay.innerHTML = `
        <h3>⚠ Missing Booking Details</h3>

        <div style="color:red;">
            Missing Fields: ${data.missing_fields.join(", ")}
        </div>

        <button id="vh-confirm" style="
            margin-top:12px;
            background:#22c55e;
            color:white;
            padding:10px;
            border:none;
            border-radius:6px;
            width:100%;">
            ✅ Confirm & Autofill Anyway
        </button>

        <button id="vh-cancel" style="
            margin-top:8px;
            background:#ef4444;
            color:white;
            padding:10px;
            border:none;
            border-radius:6px;
            width:100%;">
            ❌ Cancel
        </button>
    `;

    document.body.appendChild(overlay);

    document.getElementById("vh-confirm").onclick = () => {
        const success = fillFormFields(data);
        if (success) {
            setTimeout(() => overlay.remove(), 400);
        } else {
            alert("Autofill failed.");
        }
    };

    document.getElementById("vh-cancel").onclick = () => {
        overlay.remove();
    };
}

// ===============================
// 5️⃣ MESSAGE LISTENER
// ===============================

chrome.runtime.onMessage.addListener((request) => {

    if (request.action === "showVerification") {
        showVerificationOverlay(request.data);
    }

    if (request.action === "autoFillDirect") {
        fillFormFields(request.data);
    }

});

} catch (e) {
    console.error("VoyageHack Content Script Error:", e);
}