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
    const marketStateCardEl = document.getElementById('market-state-card');
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
    let predictionChart = null;
    let currentData = null; // Store last API response for chart usage

    // --- 3. Initial Setup ---
    dateInput.value = defaultDate;

    // Trigger initial load
    setTimeout(() => {
        form.dispatchEvent(new Event('submit'));
    }, 100);

    // --- 4. Event Listeners ---

    // 4.1 Navigation
    const tabs = {
        'nav-oracle': 'view-oracle',
        'nav-planner': 'view-planner',
        'nav-wallet': 'view-wallet'
    };

    Object.keys(tabs).forEach(tabId => {
        document.getElementById(tabId).addEventListener('click', () => {
            // Update Tab UI
            Object.keys(tabs).forEach(id => {
                const btn = document.getElementById(id);
                btn.classList.remove('text-white', 'border-b-2', 'border-primary');
                btn.classList.add('text-slate-400');
            });
            const activeBtn = document.getElementById(tabId);
            activeBtn.classList.remove('text-slate-400');
            activeBtn.classList.add('text-white', 'border-b-2', 'border-primary');

            // Toggle Views
            Object.values(tabs).forEach(viewId => {
                document.getElementById(viewId).classList.add('hidden');
            });
            document.getElementById(tabs[tabId]).classList.remove('hidden');
        });
    });

    // 4.2 Crop Selection
    const cropSelector = document.getElementById('crop-selector');
    const cropTitle = document.getElementById('crop-title');
    const modalCropName = document.getElementById('modal-crop-name');

    cropSelector.addEventListener('change', (e) => {
        const val = e.target.value;
        cropTitle.textContent = `${val} Price Oracle`;
        if (modalCropName) modalCropName.textContent = val;
        form.dispatchEvent(new Event('submit'));
    });

    // 4.3 Interactive Chart Modal
    const modalGraph = document.getElementById('modal-graph');
    const btnCloseGraph = document.getElementById('btn-close-graph');
    const overlayGraph = document.getElementById('close-modal-graph');

    // Open Modal when Forecast Card is clicked
    finalPriceEl.closest('.glass-card').addEventListener('click', (e) => {
        // Don't open if clicking sub-buttons
        if (e.target.closest('button')) return;

        modalGraph.classList.remove('hidden');
        modalGraph.classList.add('flex');
        updateChart();
    });

    [btnCloseGraph, overlayGraph].forEach(el => {
        el.addEventListener('click', () => {
            modalGraph.classList.add('hidden');
            modalGraph.classList.remove('flex');
        });
    });

    // 4.4 Disaster Modal
    const modalDisaster = document.getElementById('modal-disaster');
    const btnOpenDisaster = document.getElementById('btn-open-disaster');
    const btnCloseDisaster = document.getElementById('btn-close-disaster');
    const overlayDisaster = document.getElementById('close-modal-disaster');

    btnOpenDisaster.addEventListener('click', () => {
        modalDisaster.classList.remove('hidden');
        modalDisaster.classList.add('flex');
    });

    [btnCloseDisaster, overlayDisaster].forEach(el => {
        el.addEventListener('click', () => {
            modalDisaster.classList.add('hidden');
            modalDisaster.classList.remove('flex');
        });
    });

    // 4.5 Planner Sub-Tabs
    const tabRotation = document.getElementById('tab-rotation');
    const tabSimple = document.getElementById('tab-simple');
    const viewRotation = document.getElementById('planner-rotation');
    const viewSimple = document.getElementById('planner-simple');

    if (tabRotation && tabSimple) {
        tabRotation.addEventListener('click', () => {
            tabRotation.className = "px-6 py-2 rounded-lg text-sm font-bold transition-all bg-primary text-white shadow-glow-primary";
            tabSimple.className = "px-6 py-2 rounded-lg text-sm font-bold transition-all text-slate-400 hover:text-white";
            viewRotation.classList.remove('hidden');
            viewSimple.classList.add('hidden');
        });

        tabSimple.addEventListener('click', () => {
            tabSimple.className = "px-6 py-2 rounded-lg text-sm font-bold transition-all bg-primary text-white shadow-glow-primary";
            tabRotation.className = "px-6 py-2 rounded-lg text-sm font-bold transition-all text-slate-400 hover:text-white";
            viewSimple.classList.remove('hidden');
            viewRotation.classList.add('hidden');
        });
    }

    // 4.6 Simple Planner Logic
    const waitTimeSelector = document.getElementById('simple-wait-time');
    const waitDisplay = document.getElementById('simple-wait-display');
    const simpleCropResult = document.getElementById('simple-crop-result');

    if (waitTimeSelector) {
        waitTimeSelector.addEventListener('change', (e) => {
            const val = e.target.value;
            waitDisplay.textContent = val + " Term";

            // Mock logic for "best crop to plant" based on wait time
            const results = {
                'Short': 'Spinach (Quick-Grow)',
                'Medium': 'Potato (Hybrid)',
                'Long': 'Sugar Cane (Premium)'
            };
            simpleCropResult.textContent = results[val] || 'Mixed Grains';
        });
    }

    // 4.7 Wallet & Upload Simulation
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');
    const saveWalletBtn = document.getElementById('save-wallet-btn');
    const walletStatus = document.getElementById('wallet-status');

    if (dropZone) {
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                uploadStatus.classList.remove('hidden');
                setTimeout(() => uploadStatus.classList.add('hidden'), 3000);
            }
        });
    }

    if (saveWalletBtn) {
        saveWalletBtn.addEventListener('click', () => {
            saveWalletBtn.disabled = true;
            saveWalletBtn.innerText = 'Syncing...';
            setTimeout(() => {
                saveWalletBtn.disabled = false;
                saveWalletBtn.innerText = 'Update Security Protocol';
                walletStatus.classList.remove('hidden');
                setTimeout(() => walletStatus.classList.add('hidden'), 3000);
            }, 1000);
        });
    }

    // 4.6 Existing Controls Logic (Updated to move to separate inputs)
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
            const res = await fetch('http://127.0.0.1:8001/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("API Error");
            const data = await res.json();

            updateUI(data);
            currentData = data; // For chart

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

    // Helper: Update Chart
    function updateChart() {
        if (!currentData || !window.Chart) return;

        if (!currentData || !currentData.forecast_trend || !window.Chart) return;

        const ctx = document.getElementById('predictionChart').getContext('2d');

        // Use the real forecast series from API
        const series = currentData.forecast_trend;

        // Extract Labels (Dates) and Data (Prices)
        const labels = series.map(item => {
            const d = new Date(item.date);
            return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
        });

        const points = series.map(item => item.price);

        if (predictionChart) {
            predictionChart.destroy();
        }

        predictionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Price Projection (₹)',
                    data: points,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 4,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#3b82f6',
                    pointRadius: 2,
                    pointHoverRadius: 6,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: {
                            color: 'rgba(255,255,255,0.5)',
                            callback: function (value) { return '₹' + value; }
                        },
                        // Dynamic scaling
                        grace: '10%'
                    },
                    x: {
                        grid: { display: false },
                        ticks: {
                            color: 'rgba(255,255,255,0.5)',
                            maxTicksLimit: 6,
                            maxRotation: 0
                        }
                    }
                }
            }
        });
    }

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
        if (data.status_message.includes("Warning") || data.status_message.includes("CRITICAL")) {
            statusDot.className = "w-2 h-2 rounded-full bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)] dot";
            marketStateEl.className = "text-sm font-medium text-rose-400";
            if (marketStateCardEl) {
                marketStateCardEl.textContent = data.status_message;
                marketStateCardEl.className = "text-sm font-medium text-rose-400";
            }
        } else {
            statusDot.className = "w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)] dot";
            marketStateEl.className = "text-sm font-medium text-emerald-400";
            if (marketStateCardEl) {
                marketStateCardEl.textContent = data.status_message;
                marketStateCardEl.className = "text-sm font-medium text-emerald-400";
            }
        }
        statusMsgEl.textContent = 'System Online';

        // 5. Confidence
        if (confidenceEl) {
            const score = data.confidence_score || 0;
            let color = "text-emerald-400";
            let icon = "verified_user";

            if (score > 20) {
                color = "text-emerald-400";
            } else if (score > 10) {
                color = "text-yellow-400";
                icon = "gpp_maybe";
            } else {
                color = "text-rose-400";
                icon = "gpp_bad";
            }

            confidenceEl.innerHTML = `
                <div class="w-full">
                    <div class="flex justify-between items-center mb-1">
                        <span class="flex items-center gap-2 ${color}">
                            <span class="material-icons-round text-sm">${icon}</span> Confidence
                        </span>
                        <span class="${color} font-bold">${score}%</span>
                    </div>
                    <div class="w-full bg-slate-700/50 h-1.5 rounded-full overflow-hidden">
                        <div class="${color.replace('text', 'bg')} h-full transition-all duration-1000" style="width: ${Math.min(score * 3, 100)}%"></div>
                    </div>
                    <div class="text-[10px] text-slate-500 mt-1 text-right">Based on ensemble agreement</div>
                </div>
            `;
        }

        // 6. Blockchain
        if (data.polygon_tx_hash) {
            txHashEl.textContent = data.polygon_tx_hash;
            txHashEl.classList.add('text-white');
            setTimeout(() => txHashEl.classList.remove('text-white'), 500);
        }

        // 7. Explainability (Decomposition)
        if (data.decomposition) {
            const d = data.decomposition;

            // Helper to set text and bar
            const setExpl = (id, val, maxVal = 500, inverse = false) => {
                const elText = document.getElementById(`expl-${id}`);
                const elBar = document.getElementById(`bar-${id}`);
                if (!elText) return;

                const sign = val > 0 ? '+' : '';
                elText.innerText = `${sign}₹${val.toFixed(0)}`;

                if (elBar) {
                    // Normalize width (0-100%)
                    const w = Math.min(Math.abs(val) / maxVal * 100, 100);
                    elBar.style.width = `${w}%`;
                }
            };

            if (document.getElementById('expl-trend')) {
                document.getElementById('expl-trend').innerText = `₹${d.trend.toFixed(2)}`;
            }

            setExpl('season', d.seasonality, 5);
            setExpl('transport', d.transport_impact, 2);
            setExpl('ndvi', d.ndvi_impact, 2);
            setExpl('panic', d.panic_impact, 5);
            setExpl('diesel', d.diesel_impact, 5);
            setExpl('subsidy', d.subsidy_impact, 10);
            setExpl('market', d.market_impact, 10);
        }
    }
});
