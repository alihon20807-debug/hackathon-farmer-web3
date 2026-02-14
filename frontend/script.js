document.addEventListener('DOMContentLoaded', () => {
    // --- 1. DOM Elements ---
    const dieselInput = document.getElementById('diesel_tax');
    const subsidyInput = document.getElementById('subsidy_percent');
    const exportInput = document.getElementById('export_ban');
    const volatilityInput = document.getElementById('volatility_slider');
    const dateInput = document.getElementById('prediction_date');
    const form = document.getElementById('simulation-form');
    const quickSelectBtns = document.querySelectorAll('.quick-select');

    // Value Displays
    const dieselVal = document.getElementById('diesel-val');
    const subsidyVal = document.getElementById('subsidy-val');
    const panicVal = document.getElementById('panic-val');

    // Results
    const finalPriceEl = document.getElementById('final-price');
    const trendArrow = document.getElementById('trend-arrow');
    const baselinePriceEl = document.getElementById('baseline-price');
    const statusMsgEl = document.getElementById('status-message');
    const marketStateEl = document.getElementById('market-state');
    const statusDot = document.getElementById('status-dot');
    const txHashEl = document.getElementById('tx-hash');
    const dateDisplayEl = document.getElementById('prediction-date-display');
    const confidenceEl = document.getElementById('confidence-display');

    // Comparison Elements
    const lockBtn = document.getElementById('lock-benchmark-btn');
    const compDisplay = document.getElementById('comparison-display');
    const compDeltaPrice = document.getElementById('comp-delta-price');
    const compDeltaPct = document.getElementById('comp-delta-pct');

    // --- 2. State ---
    let defaultDate = "2023-06-15";
    let selectedTargetDate = null; // null = use Ref+1 logic from backend
    let lockedBenchmark = null;

    // --- 3. Initial Setup ---
    dateInput.value = defaultDate;

    // Trigger initial load
    setTimeout(() => {
        form.dispatchEvent(new Event('submit'));
    }, 100);

    // --- 4. Event Listeners ---

    // Live Input Updates
    dieselInput.addEventListener('input', (e) => dieselVal.textContent = '₹' + e.target.value);
    subsidyInput.addEventListener('input', (e) => subsidyVal.textContent = e.target.value + '%');
    volatilityInput.addEventListener('input', (e) => panicVal.textContent = e.target.value);

    // Reference Date Change
    dateInput.addEventListener('change', () => {
        // Reset Quick Selects (since they are relative to input)
        quickSelectBtns.forEach(b => b.classList.remove('bg-white/20', 'text-white'));
        selectedTargetDate = null; // Reset explicit target
        form.dispatchEvent(new Event('submit')); // Auto-simulate
    });

    // Quick Select Buttons (+1 Day etc.)
    quickSelectBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Visual Toggle
            quickSelectBtns.forEach(b => b.classList.remove('bg-white/20', 'text-white'));
            btn.classList.add('bg-white/20', 'text-white');

            // Logic: Parse Date Input as Local Time
            const parts = dateInput.value.split('-');
            if (parts.length !== 3) return;
            const year = parseInt(parts[0]);
            const month = parseInt(parts[1]) - 1;
            const day = parseInt(parts[2]);
            const anchor = new Date(year, month, day);

            // Calculate Target
            let target = new Date(anchor);
            const period = btn.dataset.period;

            if (period === 'tomorrow') {
                target.setDate(anchor.getDate() + 1);
            } else if (period === 'next_week') {
                target.setDate(anchor.getDate() + 7);
            } else if (period === 'next_month') {
                target.setMonth(anchor.getMonth() + 1);
            }

            console.log(`DEBUG: Button Clicked - refDate=${dateInput.value}, Period=${period}, Target=${target.toDateString()}`);

            // Format YYYY-MM-DD
            const yyyy = target.getFullYear();
            const mm = String(target.getMonth() + 1).padStart(2, '0');
            const dd = String(target.getDate()).padStart(2, '0');
            selectedTargetDate = `${yyyy}-${mm}-${dd}`;

            console.log(`DEBUG: Explicit Target Set: ${selectedTargetDate}`);

            // Trigger Simulation
            form.dispatchEvent(new Event('submit'));
        });
    });

    // Lock Button
    lockBtn.addEventListener('click', () => {
        const text = finalPriceEl.innerText;
        if (text === '--' || text === '--.--') return;
        const price = parseFloat(text);

        if (lockedBenchmark === null) {
            // Lock
            lockedBenchmark = price;
            lockBtn.innerHTML = '<span class="material-icons-round text-sm">lock</span> Unlock';
            lockBtn.classList.add('bg-white/20', 'text-white');
            updateComparison(price);
        } else {
            // Unlock
            lockedBenchmark = null;
            lockBtn.innerHTML = '<span class="material-icons-round text-sm">lock_open</span> Lock vs';
            lockBtn.classList.remove('bg-white/20', 'text-white');
            compDisplay.classList.add('hidden');
        }
    });

    // --- 5. Core Logic ---

    // Form Submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Loading UI
        const submitBtn = form.querySelector('button[type="submit"]');
        const icon = submitBtn.querySelector('.material-icons-round');
        icon.innerText = 'sync';
        icon.classList.add('animate-spin');
        submitBtn.disabled = true;

        statusMsgEl.textContent = 'Simulating...';
        statusDot.className = 'w-2 h-2 rounded-full bg-yellow-400 shadow-[0_0_10px_rgba(250,204,21,0.5)] dot animate-pulse';

        // Payload
        const payload = {
            diesel_tax: parseFloat(dieselInput.value) || 0,
            subsidy_percent: parseFloat(subsidyInput.value) || 0,
            export_ban: exportInput.checked,
            volatility_slider: parseFloat(volatilityInput.value) || 0,
            reference_date: dateInput.value,
            target_date: selectedTargetDate
        };

        console.log("DEBUG: Sending Payload:", JSON.stringify(payload));

        try {
            const res = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("API Error");
            const data = await res.json();

            updateUI(data);

        } catch (err) {
            console.error(err);
            statusMsgEl.textContent = 'Connection Error';
            statusDot.className = 'w-2 h-2 rounded-full bg-red-500 dot';
        } finally {
            icon.innerText = 'refresh';
            icon.classList.remove('animate-spin');
            submitBtn.disabled = false;
        }
    });

    // Helper: Update Comparison Display
    function updateComparison(currentPrice) {
        if (lockedBenchmark === null) {
            compDisplay.classList.add('hidden');
            return;
        }
        compDisplay.classList.remove('hidden');

        const delta = currentPrice - lockedBenchmark;
        const pct = (lockedBenchmark !== 0) ? (delta / lockedBenchmark) * 100 : 0;

        const sign = delta >= 0 ? '+' : '';
        const colorClass = delta >= 0 ? 'text-emerald-400' : 'text-rose-400'; // Green = Higher (Farmer gain)

        compDeltaPrice.innerText = `${sign}₹${Math.abs(delta).toFixed(2)}`;
        compDeltaPrice.className = `font-bold ${colorClass}`;
        compDeltaPct.innerText = `(${sign}${Math.abs(pct).toFixed(2)}%)`;
    }

    // Helper: Update Main UI
    function updateUI(data) {
        // 1. Prices
        finalPriceEl.innerText = data.final_adjusted_price.toFixed(2);
        baselinePriceEl.innerText = data.baseline_prediction.toFixed(2);
        // Format Date to be readable (e.g. "Fri, Jun 16 2023")
        const d = new Date(data.prediction_date);
        dateDisplayEl.innerText = d.toDateString();

        // 2. Comparison
        if (lockedBenchmark !== null) {
            updateComparison(data.final_adjusted_price);
        }

        // 3. Color Coding (Card Border)
        // Find Card Container (Parent of finalPriceEl)
        const cardContainer = finalPriceEl.closest('.glass-card');
        if (cardContainer) {
            if (data.final_adjusted_price >= data.baseline_prediction) {
                // Rising (Green)
                cardContainer.classList.remove('border-red-500/30', 'bg-red-500/10');
                cardContainer.classList.add('border-emerald-500/30', 'bg-emerald-500/10');
                finalPriceEl.className = 'text-5xl font-bold text-emerald-400 mb-2 flex items-baseline gap-2';

                // Update Arrow
                if (trendArrow) {
                    trendArrow.innerText = 'trending_up';
                    trendArrow.classList.remove('text-white/10', 'text-red-400');
                    trendArrow.classList.add('text-emerald-400');
                }
            } else {
                // Falling (Red)
                cardContainer.classList.remove('border-emerald-500/30', 'bg-emerald-500/10');
                cardContainer.classList.add('border-red-500/30', 'bg-red-500/10');
                finalPriceEl.className = 'text-5xl font-bold text-red-400 mb-2 flex items-baseline gap-2';

                // Update Arrow
                if (trendArrow) {
                    trendArrow.innerText = 'trending_down';
                    trendArrow.classList.remove('text-white/10', 'text-emerald-400');
                    trendArrow.classList.add('text-red-400');
                }
            }
        }

        // 4. Status Message
        marketStateEl.textContent = data.status_message;
        if (data.status_message.includes("Warning")) {
            statusDot.className = "w-2 h-2 rounded-full bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)] dot";
            marketStateEl.className = "text-sm font-medium text-rose-400";
        } else {
            statusDot.className = "w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)] dot";
            marketStateEl.className = "text-sm font-medium text-emerald-400";
        }
        statusMsgEl.textContent = 'System Online';

        // 5. Confidence
        if (confidenceEl) {
            const score = data.confidence_score || 0;
            confidenceEl.innerHTML = `<span class="material-icons-round text-emerald-400">verified_user</span> Confidence: ±${score}%`;
        }

        // 6. Blockchain
        if (data.polygon_tx_hash) {
            txHashEl.textContent = data.polygon_tx_hash;
            txHashEl.classList.add('text-white');
            setTimeout(() => txHashEl.classList.remove('text-white'), 500);
        }
    }
});
