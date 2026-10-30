// CareBridge AI — Client Application Logic
// Supports Multi-Format Uploads, OCR Review, Patient Verification,
// Daily Schedule, Browser Reminders, Voice Reading (TTS), and Family View.

document.addEventListener('DOMContentLoaded', () => {
    // Core Elements
    const summaryInput = document.getElementById('summary-input');
    const processBtn = document.getElementById('process-btn');
    const clearBtn = document.getElementById('clear-btn');
    const sampleSelector = document.getElementById('sample-selector');
    const fileUpload = document.getElementById('file-upload');
    const uploadFilenameDisplay = document.getElementById('upload-filename-display');
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultsArea = document.getElementById('results-area');
    const printFridgeBtn = document.getElementById('print-fridge-btn');

    // OCR Modal Elements
    const ocrReviewModal = document.getElementById('ocr-review-modal');
    const ocrMethodBadge = document.getElementById('ocr-method-badge');
    const ocrWarningsBox = document.getElementById('ocr-warnings-box');
    const ocrWarningsList = document.getElementById('ocr-warnings-list');
    const ocrPreviewTextarea = document.getElementById('ocr-preview-textarea');
    const btnCancelOcr = document.getElementById('btn-cancel-ocr');
    const btnConfirmOcr = document.getElementById('btn-confirm-ocr');

    // Accessibility & Header Tools
    const btnToggleLargeText = document.getElementById('btn-toggle-large-text');
    const btnToggleContrast = document.getElementById('btn-toggle-contrast');
    const btnToggleFamilyView = document.getElementById('btn-toggle-family-view');
    const familyViewSection = document.getElementById('family-view-section');
    const familyContentDisplay = document.getElementById('family-content-display');
    const familyLangEn = document.getElementById('family-lang-en');
    const familyLangTe = document.getElementById('family-lang-te');

    // Doctor Workflow & Verification
    const workflowStatusSelect = document.getElementById('workflow-status-select');
    const workflowBadge = document.getElementById('workflow-badge');
    const doctorReviewBadgeStatus = document.getElementById('doctor-review-badge-status');

    // Reminders Elements
    const btnToggleReminders = document.getElementById('btn-toggle-reminders');
    const btnTestReminder = document.getElementById('btn-test-reminder');

    // History Elements
    const sessionHistoryList = document.getElementById('session-history-list');
    const btnClearHistory = document.getElementById('btn-clear-history');

    // State Variables
    let currentResult = null;
    let familyLanguage = 'en';
    let remindersEnabled = false;

    // -------------------------------------------------------------
    // 1. Accessibility & Workflow Controls
    // -------------------------------------------------------------
    if (btnToggleLargeText) {
        btnToggleLargeText.addEventListener('click', () => {
            document.body.classList.toggle('large-text');
            const isActive = document.body.classList.contains('large-text');
            btnToggleLargeText.classList.toggle('btn-tool-accent', isActive);
        });
    }

    if (btnToggleContrast) {
        btnToggleContrast.addEventListener('click', () => {
            document.body.classList.toggle('high-contrast');
            const isActive = document.body.classList.contains('high-contrast');
            btnToggleContrast.classList.toggle('btn-tool-accent', isActive);
        });
    }

    if (btnToggleFamilyView) {
        btnToggleFamilyView.addEventListener('click', () => {
            if (!currentResult) {
                alert('Please process a discharge summary first to open Family View.');
                return;
            }
            familyViewSection.classList.toggle('hidden');
            const isVisible = !familyViewSection.classList.contains('hidden');
            btnToggleFamilyView.classList.toggle('btn-tool-accent', isVisible);
            if (isVisible) {
                renderFamilyView(currentResult, familyLanguage);
                familyViewSection.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    function syncDoctorWorkflow(status) {
        let badgeClass = 'badge badge-draft';
        let label = 'Doctor Review: PENDING';

        if (status === 'approved') {
            badgeClass = 'badge badge-success';
            label = 'Doctor Review: APPROVED';
        } else if (status === 'changes_requested') {
            badgeClass = 'badge badge-danger';
            label = 'Doctor Review: CHANGES REQUESTED';
        } else {
            badgeClass = 'badge badge-draft';
            label = 'Doctor Review: PENDING';
        }

        if (workflowBadge) {
            workflowBadge.className = badgeClass;
            workflowBadge.textContent = label;
        }
        if (doctorReviewBadgeStatus) {
            doctorReviewBadgeStatus.className = badgeClass;
            doctorReviewBadgeStatus.textContent = label;
        }
    }

    if (workflowStatusSelect) {
        workflowStatusSelect.addEventListener('change', (e) => {
            syncDoctorWorkflow(e.target.value);
        });
    }

    // -------------------------------------------------------------
    // 2. Preset Samples & Document Upload
    // -------------------------------------------------------------
    async function loadSampleOptions() {
        try {
            const resp = await fetch('/api/samples');
            if (resp.ok) {
                const samples = await resp.json();
                sampleSelector.innerHTML = '<option value="">-- Choose or paste discharge summary --</option>';
                samples.forEach(s => {
                    const opt = document.createElement('option');
                    opt.value = s.id;
                    opt.textContent = `${s.id} - ${s.preview.substring(0, 45)}...`;
                    sampleSelector.appendChild(opt);
                });
            }
        } catch (e) {
            console.warn('Could not load samples list:', e);
        }
    }
    loadSampleOptions();

    sampleSelector.addEventListener('change', async (e) => {
        const sid = e.target.value;
        if (!sid) return;
        try {
            const resp = await fetch(`/api/sample/${sid}`);
            if (resp.ok) {
                const data = await resp.json();
                summaryInput.value = data.text;
                if (uploadFilenameDisplay) uploadFilenameDisplay.textContent = `Preset: ${sid}`;
            }
        } catch (err) {
            console.error('Error loading sample:', err);
        }
    });

    // Multi-Format File Upload (.txt, .pdf, .png, .jpg, .jpeg)
    if (fileUpload) {
        fileUpload.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (uploadFilenameDisplay) uploadFilenameDisplay.textContent = file.name;

            // Direct client reading for simple TXT files
            if (file.name.toLowerCase().endsWith('.txt')) {
                const reader = new FileReader();
                reader.onload = (evt) => {
                    summaryInput.value = evt.target.result;
                };
                reader.readAsText(file);
                return;
            }

            // For PDF, PNG, JPG, JPEG: Send to server document reader/OCR
            const formData = new FormData();
            formData.append('file', file);

            loadingSpinner.classList.remove('hidden');
            loadingSpinner.querySelector('p').textContent = `Reading ${file.name} using document parser & OCR...`;

            try {
                const resp = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!resp.ok) {
                    const err = await resp.json();
                    alert(`Upload Error: ${err.error || 'Failed to read document'}`);
                    return;
                }

                const docData = await resp.json();

                // Show confirmation modal for verification before pipeline
                showOcrReviewModal(docData);

            } catch (err) {
                alert(`Upload failed: ${err.message}`);
            } finally {
                loadingSpinner.classList.add('hidden');
                loadingSpinner.querySelector('p').textContent = 'Auditing clinical abbreviations and compiling care plan...';
            }
        });
    }

    function showOcrReviewModal(docData) {
        ocrPreviewTextarea.value = docData.text || '';
        ocrMethodBadge.textContent = `Extracted via: ${docData.method || 'Document Reader'}`;

        if (docData.warnings && docData.warnings.length > 0) {
            ocrWarningsList.innerHTML = '';
            docData.warnings.forEach(w => {
                const li = document.createElement('li');
                li.textContent = w;
                ocrWarningsList.appendChild(li);
            });
            ocrWarningsBox.classList.remove('hidden');
        } else {
            ocrWarningsBox.classList.add('hidden');
        }

        ocrReviewModal.classList.remove('hidden');
    }

    if (btnCancelOcr) {
        btnCancelOcr.addEventListener('click', () => {
            ocrReviewModal.classList.add('hidden');
        });
    }

    if (btnConfirmOcr) {
        btnConfirmOcr.addEventListener('click', () => {
            const confirmedText = ocrPreviewTextarea.value.trim();
            if (!confirmedText) {
                alert('Text cannot be empty.');
                return;
            }
            summaryInput.value = confirmedText;
            ocrReviewModal.classList.add('hidden');
            // Trigger automatic pipeline processing
            processBtn.click();
        });
    }

    clearBtn.addEventListener('click', () => {
        summaryInput.value = '';
        resultsArea.classList.add('hidden');
        if (familyViewSection) familyViewSection.classList.add('hidden');
        currentResult = null;
        if (uploadFilenameDisplay) uploadFilenameDisplay.textContent = 'No file chosen';
    });

    // -------------------------------------------------------------
    // 3. Process Summary & Render Output
    // -------------------------------------------------------------
    processBtn.addEventListener('click', async () => {
        const text = summaryInput.value.trim();
        if (!text) {
            alert('Please paste or upload a discharge summary first.');
            return;
        }

        loadingSpinner.classList.remove('hidden');
        resultsArea.classList.add('hidden');

        try {
            const resp = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    summary_id: sampleSelector.value || 'USER-SUMMARY'
                })
            });

            if (!resp.ok) {
                const err = await resp.json();
                alert(`Error: ${err.error || 'Failed to process'}`);
                return;
            }

            const data = await resp.json();
            currentResult = data;
            currentResult._raw_source_text = text;

            renderResults(data);
            saveToSessionHistory(data);

            resultsArea.classList.remove('hidden');
            resultsArea.scrollIntoView({ behavior: 'smooth' });
        } catch (err) {
            alert(`Processing error: ${err.message}`);
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    });

    function renderResults(data) {
        // 1. Patient Verification Banner (3 States)
        renderPatientVerification(data.validation);

        // 2. Daily Medication Schedule (Morning / Afternoon / Night / As Needed)
        renderDailySchedule(data.medication_schedule, data.medicines);

        // 3. Active Medicines Table
        const medTableBody = document.querySelector('#medicines-table tbody');
        medTableBody.innerHTML = '';
        if (data.medicines && data.medicines.length > 0) {
            data.medicines.forEach(m => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="font-bold text-navy">${escapeHtml(m.name)}</td>
                    <td><span class="badge badge-dose">${escapeHtml(m.dose)}</span></td>
                    <td>${escapeHtml(m.frequency)}</td>
                    <td>${escapeHtml(m.timing)}</td>
                    <td>${escapeHtml(m.duration)}</td>
                    <td>${escapeHtml(m.how_to_take_plain)}</td>
                `;
                medTableBody.appendChild(row);
            });
        } else {
            medTableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No active medications found in summary.</td></tr>';
        }

        // 4. Discontinued / Stopped Medicines
        const stopContainer = document.getElementById('stop-medicines-list');
        stopContainer.innerHTML = '';
        if (data.stop_medicines && data.stop_medicines.length > 0) {
            data.stop_medicines.forEach(sm => {
                const item = document.createElement('div');
                item.className = 'stop-pill';
                item.innerHTML = `<strong>STOP: ${escapeHtml(sm.name)}</strong> <span>(${escapeHtml(sm.reason || 'Discontinued')})</span>`;
                stopContainer.appendChild(item);
            });
        } else {
            stopContainer.innerHTML = '<span class="text-muted">No medicines were marked for discontinuation. Continue only prescribed items.</span>';
        }

        // 5. Follow-ups
        const fuTableBody = document.querySelector('#followup-table tbody');
        fuTableBody.innerHTML = '';
        if (data.follow_ups && data.follow_ups.length > 0) {
            data.follow_ups.forEach(fu => {
                const r = document.createElement('tr');
                r.innerHTML = `
                    <td class="font-bold">${escapeHtml(fu.date)}</td>
                    <td>${escapeHtml(fu.with_whom)}</td>
                    <td>${escapeHtml(fu.purpose)}</td>
                `;
                fuTableBody.appendChild(r);
            });
        } else {
            fuTableBody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">Not specified in discharge summary. Please verify with your healthcare provider.</td></tr>';
        }

        // 6. Warning Signs, Diet, Activity
        renderList('warnings-list', data.warning_signs);
        renderList('diet-list', data.diet);
        renderList('activity-list', data.activity);

        // 7. English & Telugu Plans
        document.getElementById('english-care-plan').textContent = data.english_plan || '';
        document.getElementById('telugu-care-plan').textContent = data.telugu_plan || '';

        // 8. Readability
        if (data.readability) {
            document.getElementById('readability-grade').textContent = data.readability.score || 'N/A';
            document.getElementById('readability-desc').textContent = data.readability.reading_level || '';
            document.getElementById('readability-expl').textContent = data.readability.explanation || '';
        }

        // 9. Source Comparison & Traceability
        renderComparisonInspector(data);

        // 10. Family Fridge Sheet
        populateFridgeSheet(data, 'bilingual');

        // If Family View is already open, update it
        if (familyViewSection && !familyViewSection.classList.contains('hidden')) {
            renderFamilyView(data, familyLanguage);
        }
    }

    // -------------------------------------------------------------
    // 4. Patient-Friendly Verification Banner (Decoupled Technical & Clinical)
    // -------------------------------------------------------------
    function renderPatientVerification(val) {
        val = val || {};
        const bannerCard = document.querySelector('.patient-verification-card');
        const iconBox = document.getElementById('verification-icon-box');
        const titleEl = document.getElementById('patient-status-title');
        const descEl = document.getElementById('patient-status-desc');

        const overallStatus = val.overall_status || 'NEEDS_REVIEW';
        bannerCard.classList.remove('banner-pass', 'banner-fail', 'banner-incomplete');

        if (overallStatus === 'PASS') {
            bannerCard.classList.add('banner-pass');
            titleEl.textContent = 'TECHNICAL VALIDATION: PASS';
            descEl.textContent = 'All extracted medications, dosages, and dates are grounded in the source discharge summary.';
            iconBox.innerHTML = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
        } else if (overallStatus === 'FAIL') {
            bannerCard.classList.add('banner-fail');
            titleEl.textContent = 'TECHNICAL VALIDATION: FAIL';
            descEl.textContent = val.patient_message || 'A clinical safety concern was flagged (e.g. ungrounded drug or discontinued medicine conflict).';
            iconBox.innerHTML = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
        } else {
            bannerCard.classList.add('banner-incomplete');
            titleEl.textContent = 'TECHNICAL VALIDATION: NEEDS REVIEW';
            descEl.textContent = 'Some clinical dosages, relative dates, or instructions require doctor review. Do not assume all checks passed.';
            iconBox.innerHTML = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
        }

        // Sync doctor workflow badge status
        if (workflowStatusSelect) {
            syncDoctorWorkflow(workflowStatusSelect.value);
        }

        // Update Checklist Summary Pills
        const items = val.items || [];
        updateCheckPill('check-meds-pill', items.filter(i => i.check_name.includes('Medication')));
        updateCheckPill('check-stops-pill', items.filter(i => i.check_name.includes('Discontinued')));
        updateCheckPill('check-doses-pill', items.filter(i => i.check_name.includes('Dose')));
        updateCheckPill('check-dates-pill', items.filter(i => i.check_name.includes('Follow-Up')));

        // Technical Audit Details Table
        const checksBody = document.querySelector('#validation-table tbody');
        checksBody.innerHTML = '';
        if (val.items) {
            val.items.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td class="font-medium">${escapeHtml(item.check_name)}</td>
                    <td class="text-muted text-sm">${escapeHtml(item.source_value)}</td>
                    <td><span class="status-badge badge-${item.status.toLowerCase()}">${escapeHtml(item.status)}</span></td>
                    <td class="text-sm">${escapeHtml(item.explanation)}</td>
                `;
                checksBody.appendChild(tr);
            });
        }
    }

    function updateCheckPill(pillId, relatedItems) {
        const pill = document.getElementById(pillId);
        if (!pill) return;
        const icon = pill.querySelector('.check-pill-icon');

        if (!relatedItems || relatedItems.length === 0) {
            pill.className = 'check-summary-pill pill-pass';
            if (icon) icon.textContent = '✓';
            return;
        }

        const hasFail = relatedItems.some(i => i.status === 'FAIL');
        const hasReview = relatedItems.some(i => i.status === 'NEEDS_REVIEW');

        if (hasFail) {
            pill.className = 'check-summary-pill pill-fail';
            if (icon) icon.textContent = '✕';
        } else if (hasReview) {
            pill.className = 'check-summary-pill pill-review';
            if (icon) icon.textContent = '⚠️';
        } else {
            pill.className = 'check-summary-pill pill-pass';
            if (icon) icon.textContent = '✓';
        }
    }

    // -------------------------------------------------------------
    // 5. Daily Medication Schedule Slots
    // -------------------------------------------------------------
    function renderDailySchedule(sched, medicines) {
        sched = sched || { morning: [], afternoon: [], night: [], as_needed: [], unspecified: [] };

        renderSlot('slot-morning-items', sched.morning);
        renderSlot('slot-afternoon-items', sched.afternoon);
        renderSlot('slot-night-items', sched.night);
        renderSlot('slot-sos-items', sched.as_needed);

        const unspecCol = document.getElementById('slot-unspecified-col');
        if (sched.unspecified && sched.unspecified.length > 0) {
            if (unspecCol) unspecCol.classList.remove('hidden');
            renderSlot('slot-unspecified-items', sched.unspecified);
        } else {
            if (unspecCol) unspecCol.classList.add('hidden');
        }
    }

    function renderSlot(containerId, items) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = '';

        if (!items || items.length === 0) {
            el.innerHTML = '<div class="slot-empty">No medicines scheduled</div>';
            return;
        }

        items.forEach(it => {
            const card = document.createElement('div');
            card.className = 'slot-med-card';
            card.innerHTML = `
                <div class="slot-med-name">${escapeHtml(it.name)}</div>
                <div class="slot-med-dose">${escapeHtml(it.dose)}</div>
                <div class="slot-med-instr">${escapeHtml(it.timing || it.instruction)}</div>
            `;
            el.appendChild(card);
        });
    }

    // -------------------------------------------------------------
    // 6. Daily Browser Reminders (Opt-In)
    // -------------------------------------------------------------
    if (btnToggleReminders) {
        btnToggleReminders.addEventListener('click', async () => {
            if (!('Notification' in window)) {
                alert('Browser notifications are not supported in this browser.');
                return;
            }

            if (!remindersEnabled) {
                const perm = await Notification.requestPermission();
                if (perm === 'granted') {
                    remindersEnabled = true;
                    btnToggleReminders.textContent = 'Reminders: Active (Click to Disable)';
                    btnToggleReminders.classList.add('btn-primary');
                    btnToggleReminders.classList.remove('btn-outline');
                    if (btnTestReminder) btnTestReminder.classList.remove('hidden');
                    new Notification('CareBridge AI Reminders Active', {
                        body: 'Daily medication reminders are now active for your browser session.',
                        icon: '/static/favicon.ico'
                    });
                } else {
                    alert('Permission for notifications was denied. You can enable them in your browser site settings.');
                }
            } else {
                remindersEnabled = false;
                btnToggleReminders.textContent = 'Enable Browser Reminders';
                btnToggleReminders.classList.remove('btn-primary');
                btnToggleReminders.classList.add('btn-outline');
                if (btnTestReminder) btnTestReminder.classList.add('hidden');
            }
        });
    }

    if (btnTestReminder) {
        btnTestReminder.addEventListener('click', () => {
            if (Notification.permission === 'granted') {
                const firstMed = currentResult && currentResult.medicines && currentResult.medicines[0]
                    ? `${currentResult.medicines[0].name} (${currentResult.medicines[0].dose})`
                    : 'Scheduled Morning Medication';
                new Notification('CareBridge AI — Pill Reminder', {
                    body: `Time to take: ${firstMed}. Please refer to your CareBridge fridge sheet.`,
                    icon: '/static/favicon.ico'
                });
            }
        });
    }


    // -------------------------------------------------------------
    // 8. Family-Friendly Caregiver View
    // -------------------------------------------------------------
    function renderFamilyView(data, lang) {
        if (!familyContentDisplay || !data) return;
        familyContentDisplay.innerHTML = '';

        const isTe = lang === 'te';

        const wrapper = document.createElement('div');
        wrapper.className = isTe ? 'telugu-text' : '';

        // Heading
        const headerDiv = document.createElement('div');
        headerDiv.innerHTML = `
            <h3 class="font-bold text-navy" style="font-size: 1.5rem; margin-bottom: 0.5rem;">
                ${isTe ? 'రోగి సంరక్షణ గైడ్ (Family Care Plan)' : 'Home Caregiver Quick Guide'}
            </h3>
            <p class="text-muted" style="margin-bottom: 1.5rem;">
                ${isTe ? 'ఇంట్లో కుటుంబ సభ్యులు సులభంగా అర్థం చేసుకునే ముఖ్యమైన మందుల వివరాలు:' : 'Key medicines and instructions for home care at a glance:'}
            </p>
        `;
        wrapper.appendChild(headerDiv);

        // Medicines Cards
        if (data.medicines && data.medicines.length > 0) {
            data.medicines.forEach((m, idx) => {
                const medCard = document.createElement('div');
                medCard.className = 'family-med-item';
                medCard.innerHTML = `
                    <div class="family-med-title">${idx + 1}. ${escapeHtml(m.name)} — <span class="text-teal">${escapeHtml(m.dose)}</span></div>
                    <div style="font-size: 1.05rem; margin-top: 0.35rem;">
                        <strong>${isTe ? 'ఎప్పుడు వేసుకోవాలి' : 'When to take'}:</strong> ${escapeHtml(m.frequency)}, ${escapeHtml(m.timing)} (${escapeHtml(m.duration)})
                    </div>
                    <div style="font-size: 0.95rem; color: #475569; margin-top: 0.2rem;">
                        <strong>${isTe ? 'సూచన' : 'How'}:</strong> ${escapeHtml(m.how_to_take_plain)}
                    </div>
                `;
                wrapper.appendChild(medCard);
            });
        }

        // Stopped medicines if any
        if (data.stop_medicines && data.stop_medicines.length > 0) {
            const stopDiv = document.createElement('div');
            stopDiv.style.marginTop = '1.5rem';
            stopDiv.innerHTML = `<h4 class="text-danger font-bold" style="font-size: 1.25rem;">🛑 ${isTe ? 'నిలిపివేయవలసిన మందులు (Do Not Give)' : 'Medicines to Stop (Do Not Give)'}:</h4>`;
            data.stop_medicines.forEach(sm => {
                stopDiv.innerHTML += `<div class="stop-pill" style="margin-top: 0.5rem;"><strong>${escapeHtml(sm.name)}</strong>: ${escapeHtml(sm.reason || 'Discontinued')}</div>`;
            });
            wrapper.appendChild(stopDiv);
        }

        familyContentDisplay.appendChild(wrapper);
    }

    if (familyLangEn) {
        familyLangEn.addEventListener('click', () => {
            familyLanguage = 'en';
            familyLangEn.className = 'btn btn-secondary btn-sm active';
            familyLangTe.className = 'btn btn-outline btn-sm';
            if (currentResult) renderFamilyView(currentResult, 'en');
        });
    }

    if (familyLangTe) {
        familyLangTe.addEventListener('click', () => {
            familyLanguage = 'te';
            familyLangTe.className = 'btn btn-secondary btn-sm active';
            familyLangEn.className = 'btn btn-outline btn-sm';
            if (currentResult) renderFamilyView(currentResult, 'te');
        });
    }

    // -------------------------------------------------------------
    // 9. Source Comparison & Traceability Inspector
    // -------------------------------------------------------------
    function renderComparisonInspector(data) {
        const sourceBox = document.getElementById('comparison-source-text');
        const factsBox = document.getElementById('comparison-facts-box');
        if (!sourceBox || !factsBox) return;

        sourceBox.textContent = data._raw_source_text || summaryInput.value;

        factsBox.innerHTML = '';

        // Medicines summary
        const medsHeader = document.createElement('h5');
        medsHeader.className = 'font-bold text-navy';
        medsHeader.textContent = `Extracted Prescriptions (${data.medicines ? data.medicines.length : 0} items):`;
        factsBox.appendChild(medsHeader);

        const medUl = document.createElement('ul');
        medUl.className = 'styled-list text-sm';
        if (data.medicines) {
            data.medicines.forEach(m => {
                const li = document.createElement('li');
                li.innerHTML = `<strong>${escapeHtml(m.name)}</strong> (${escapeHtml(m.dose)}) — ${escapeHtml(m.frequency)} [${escapeHtml(m.timing)}]`;
                medUl.appendChild(li);
            });
        }
        factsBox.appendChild(medUl);

        // Stopped summary
        if (data.stop_medicines && data.stop_medicines.length > 0) {
            const stopH = document.createElement('h5');
            stopH.className = 'font-bold text-danger';
            stopH.style.marginTop = '0.75rem';
            stopH.textContent = 'Segregated Discontinued Drugs:';
            factsBox.appendChild(stopH);

            const stopUl = document.createElement('ul');
            stopUl.className = 'styled-list text-sm';
            data.stop_medicines.forEach(s => {
                const li = document.createElement('li');
                li.innerHTML = `<span class="text-danger">STOP: ${escapeHtml(s.name)}</span> (${escapeHtml(s.reason)})`;
                stopUl.appendChild(li);
            });
            factsBox.appendChild(stopUl);
        }

        // Follow-ups summary
        if (data.follow_ups && data.follow_ups.length > 0) {
            const fuH = document.createElement('h5');
            fuH.className = 'font-bold text-teal';
            fuH.style.marginTop = '0.75rem';
            fuH.textContent = 'Follow-up Grounding:';
            factsBox.appendChild(fuH);

            const fuUl = document.createElement('ul');
            fuUl.className = 'styled-list text-sm';
            data.follow_ups.forEach(fu => {
                const li = document.createElement('li');
                li.innerHTML = `📅 <strong>${escapeHtml(fu.date)}</strong> with ${escapeHtml(fu.with_whom)}`;
                fuUl.appendChild(li);
            });
            factsBox.appendChild(fuUl);
        }
    }

    // -------------------------------------------------------------
    // 10. Printable Family Fridge Sheet
    // -------------------------------------------------------------
    function populateFridgeSheet(data, langMode) {
        const sheetMeds = document.getElementById('fridge-medicines-list');
        sheetMeds.innerHTML = '';
        if (data.medicines) {
            data.medicines.forEach(m => {
                const div = document.createElement('div');
                div.className = 'fridge-med-row';
                div.innerHTML = `
                    <div class="fridge-med-name">${escapeHtml(m.name)} <span>(${escapeHtml(m.dose)})</span></div>
                    <div class="fridge-med-how">${escapeHtml(m.frequency)} — ${escapeHtml(m.timing)} (${escapeHtml(m.duration)})</div>
                `;
                sheetMeds.appendChild(div);
            });
        }

        const sheetFu = document.getElementById('fridge-followup-list');
        sheetFu.innerHTML = '';
        if (data.follow_ups && data.follow_ups.length > 0) {
            data.follow_ups.forEach(fu => {
                const li = document.createElement('li');
                li.innerHTML = `<strong>${escapeHtml(fu.date)}</strong> with ${escapeHtml(fu.with_whom)} (${escapeHtml(fu.purpose)})`;
                sheetFu.appendChild(li);
            });
        } else {
            sheetFu.innerHTML = '<li class="text-muted">Not specified in discharge summary. Please verify with your healthcare provider.</li>';
        }

        const sheetWarn = document.getElementById('fridge-warnings-list');
        sheetWarn.innerHTML = '';
        if (data.warning_signs && data.warning_signs.length > 0) {
            data.warning_signs.slice(0, 4).forEach(w => {
                const li = document.createElement('li');
                li.textContent = w;
                sheetWarn.appendChild(li);
            });
        } else {
            sheetWarn.innerHTML = '<li class="text-muted">Not specified in discharge summary. Please verify with your healthcare provider.</li>';
        }

        const sheetDiet = document.getElementById('fridge-diet-list');
        if (sheetDiet) {
            sheetDiet.innerHTML = '';
            if (data.diet && data.diet.length > 0) {
                data.diet.slice(0, 3).forEach(d => {
                    const li = document.createElement('li');
                    li.textContent = d;
                    sheetDiet.appendChild(li);
                });
            } else {
                sheetDiet.innerHTML = '<li class="text-muted">Not specified in discharge summary. Please verify with your healthcare provider.</li>';
            }
        }

        const sheetAct = document.getElementById('fridge-activity-list');
        if (sheetAct) {
            sheetAct.innerHTML = '';
            if (data.activity && data.activity.length > 0) {
                data.activity.slice(0, 3).forEach(a => {
                    const li = document.createElement('li');
                    li.textContent = a;
                    sheetAct.appendChild(li);
                });
            } else {
                sheetAct.innerHTML = '<li class="text-muted">Not specified in discharge summary. Please verify with your healthcare provider.</li>';
            }
        }
    }

    const fridgeLangSelect = document.getElementById('fridge-lang-select');
    if (fridgeLangSelect) {
        fridgeLangSelect.addEventListener('change', (e) => {
            if (currentResult) populateFridgeSheet(currentResult, e.target.value);
        });
    }

    if (printFridgeBtn) {
        printFridgeBtn.addEventListener('click', () => {
            window.print();
        });
    }

    // -------------------------------------------------------------
    // 11. Privacy-Conscious Session Care Plan History
    // -------------------------------------------------------------
    function saveToSessionHistory(data) {
        try {
            const history = JSON.parse(sessionStorage.getItem('carebridge_history') || '[]');
            const entry = {
                id: data.summary_id || 'SUMMARY-' + Date.now(),
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                medCount: data.medicines ? data.medicines.length : 0,
                status: data.validation ? data.validation.patient_status : 'VERIFIED',
                data: data
            };
            history.unshift(entry);
            // Keep at most 5 entries
            if (history.length > 5) history.pop();
            sessionStorage.setItem('carebridge_history', JSON.stringify(history));
            renderSessionHistory();
        } catch (e) {
            console.warn('Could not save to session storage:', e);
        }
    }

    function renderSessionHistory() {
        if (!sessionHistoryList) return;
        try {
            const history = JSON.parse(sessionStorage.getItem('carebridge_history') || '[]');
            if (history.length === 0) {
                sessionHistoryList.innerHTML = '<li class="text-muted text-sm">No previous care plans in this session yet.</li>';
                return;
            }

            sessionHistoryList.innerHTML = '';
            history.forEach(item => {
                const li = document.createElement('li');
                li.className = 'history-item';
                li.innerHTML = `
                    <div>
                        <button class="history-item-btn font-medium" data-id="${escapeHtml(item.id)}">${escapeHtml(item.id)}</button>
                        <span class="text-muted text-xs">(${escapeHtml(item.timestamp)}) — ${item.medCount} meds</span>
                    </div>
                    <span class="badge badge-accent">${escapeHtml(item.status)}</span>
                `;
                li.querySelector('.history-item-btn').addEventListener('click', () => {
                    currentResult = item.data;
                    renderResults(item.data);
                    resultsArea.classList.remove('hidden');
                    resultsArea.scrollIntoView({ behavior: 'smooth' });
                });
                sessionHistoryList.appendChild(li);
            });
        } catch (e) {
            console.warn('Error reading history:', e);
        }
    }
    renderSessionHistory();

    if (btnClearHistory) {
        btnClearHistory.addEventListener('click', () => {
            sessionStorage.removeItem('carebridge_history');
            renderSessionHistory();
        });
    }

    // -------------------------------------------------------------
    // 12. Synthetic Demo Buttons
    // -------------------------------------------------------------
    const demoValidBtn = document.getElementById('demo-valid-btn');
    if (demoValidBtn) {
        demoValidBtn.addEventListener('click', async () => {
            const diabeticId = 'H2S-047NPLXP';
            try {
                const resp = await fetch(`/api/sample/${diabeticId}`);
                if (resp.ok) {
                    const data = await resp.json();
                    summaryInput.value = data.text;
                    sampleSelector.value = diabeticId;
                    if (uploadFilenameDisplay) {
                        uploadFilenameDisplay.textContent = `Preset: ${diabeticId} (Diabetic DKA / T2DM)`;
                    }
                    resultsArea.classList.add('hidden');
                    currentResult = null;
                    summaryInput.scrollIntoView({ behavior: 'smooth' });
                } else {
                    alert(`Could not load sample ${diabeticId}. Please check server.`);
                }
            } catch (err) {
                console.error('Error loading diabetic demo:', err);
                alert(`Error loading diabetic sample: ${err.message}`);
            }
        });
    }

    const demoTamperBtn = document.getElementById('demo-tamper-btn');
    if (demoTamperBtn) {
        demoTamperBtn.addEventListener('click', () => {
            summaryInput.value = `CITY GENERAL HOSPITAL
DISCHARGE SUMMARY
Patient: John Doe | Age: 50/M
DISCHARGE MEDICATIONS:
1. Tab Metformin 500mg BD after food
2. Tab Telmisartan 40mg OD
STOP MEDICINES:
- Stop Tab Glibenclamide 5mg`;
            setTimeout(() => processBtn.click(), 200);
        });
    }

    // -------------------------------------------------------------
    // Utility Helpers
    // -------------------------------------------------------------
    function renderList(elemId, items) {
        const el = document.getElementById(elemId);
        if (!el) return;
        el.innerHTML = '';
        if (items && items.length > 0) {
            items.forEach(it => {
                const li = document.createElement('li');
                li.textContent = it;
                el.appendChild(li);
            });
        } else {
            el.innerHTML = '<li class="text-muted">Not specified in the discharge summary. Please verify with your healthcare provider.</li>';
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
