// CareBridge AI — Client Application Logic
// Features: Multi-Format Uploads, OCR Review, Doctor Workflow,
// Medication Reminders & Timers, Complete English / Telugu Toggle,
// Direct PDF & Direct PNG Downloads, Traceability Inspector, and Family View.

document.addEventListener('DOMContentLoaded', () => {
    // -------------------------------------------------------------
    // Core Elements & State
    // -------------------------------------------------------------
    const summaryInput = document.getElementById('summary-input');
    const processBtn = document.getElementById('process-btn');
    const clearBtn = document.getElementById('clear-btn');
    const sampleSelector = document.getElementById('sample-selector');
    const fileUpload = document.getElementById('file-upload');
    const uploadFilenameDisplay = document.getElementById('upload-filename-display');
    const loadingSpinner = document.getElementById('loading-spinner');
    const resultsArea = document.getElementById('results-area');

    // Language Toggle Elements
    const btnHeaderLangEn = document.getElementById('btn-header-lang-en');
    const btnHeaderLangTe = document.getElementById('btn-header-lang-te');
    const btnViewLangEn = document.getElementById('btn-view-lang-en');
    const btnViewLangTe = document.getElementById('btn-view-lang-te');

    // Direct Export Elements
    const btnQuickDownloadPdf = document.getElementById('btn-quick-download-pdf');
    const btnQuickDownloadImage = document.getElementById('btn-quick-download-image');
    const btnDownloadPdf = document.getElementById('btn-download-pdf');
    const btnDownloadImage = document.getElementById('btn-download-image');
    const fridgeLangSelect = document.getElementById('fridge-lang-select');

    // Accessibility & Header Tools
    const btnToggleLargeText = document.getElementById('btn-toggle-large-text');
    const btnToggleContrast = document.getElementById('btn-toggle-contrast');
    const btnToggleFamilyView = document.getElementById('btn-toggle-family-view');
    const familyViewSection = document.getElementById('family-view-section');
    const familyContentDisplay = document.getElementById('family-content-display');
    const familyLangEn = document.getElementById('family-lang-en');
    const familyLangTe = document.getElementById('family-lang-te');

    // Doctor Workflow & Verification
    const workflowBadge = document.getElementById('workflow-badge');
    const doctorReviewBadgeStatus = document.getElementById('doctor-review-badge-status');
    const openDocBtn = document.getElementById('btn-open-doctor-review');
    const caseIdDisplay = document.getElementById('case-id-display');
    const doctorFeedbackBanner = document.getElementById('doctor-feedback-banner');

    // OCR Modal Elements
    const ocrReviewModal = document.getElementById('ocr-review-modal');
    const ocrMethodBadge = document.getElementById('ocr-method-badge');
    const ocrWarningsBox = document.getElementById('ocr-warnings-box');
    const ocrWarningsList = document.getElementById('ocr-warnings-list');
    const ocrPreviewTextarea = document.getElementById('ocr-preview-textarea');
    const btnCancelOcr = document.getElementById('btn-cancel-ocr');
    const btnConfirmOcr = document.getElementById('btn-confirm-ocr');

    // Medication Reminder Elements
    const remindersTableBody = document.getElementById('reminders-table-body');
    const remindersSummaryStats = document.getElementById('reminders-summary-stats');
    const btnToggleAudio = document.getElementById('btn-toggle-audio');
    const btnTestChime = document.getElementById('btn-test-chime');
    const btnToggleBrowserPerm = document.getElementById('btn-toggle-browser-perm');
    const btnAddCustomReminder = document.getElementById('btn-add-custom-reminder');
    const btnResetReminders = document.getElementById('btn-reset-reminders');

    // Reminder Modal Elements
    const reminderModal = document.getElementById('reminder-modal');
    const btnCloseReminderModal = document.getElementById('btn-close-reminder-modal');
    const btnCancelReminderModal = document.getElementById('btn-cancel-reminder-modal');
    const btnSaveReminderModal = document.getElementById('btn-save-reminder-modal');
    const modalReminderId = document.getElementById('modal-reminder-id');
    const modalMedName = document.getElementById('modal-med-name');
    const modalMedDoseFreq = document.getElementById('modal-med-dose-freq');
    const modalReminderTime = document.getElementById('modal-reminder-time');
    const modalReminderSlot = document.getElementById('modal-reminder-slot');
    const modalReminderAlert = document.getElementById('modal-reminder-alert');

    // Session History Elements
    const sessionHistoryList = document.getElementById('session-history-list');
    const btnClearHistory = document.getElementById('btn-clear-history');

    // State Variables
    let currentResult = null;
    let currentLang = 'en'; // 'en' | 'te'
    let familyLanguage = 'en';
    let audioAlertEnabled = (localStorage.getItem('carebridge_audio_enabled') !== 'false');
    let activeReminders = [];
    let reminderTickerTimer = null;

    // -------------------------------------------------------------
    // 1. Accessibility Controls
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
                renderFamilyView(currentResult, currentLang);
                familyViewSection.scrollIntoView({ behavior: 'smooth' });
            }
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
    loadPatientNotifications();

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

    if (fileUpload) {
        fileUpload.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (uploadFilenameDisplay) uploadFilenameDisplay.textContent = file.name;

            if (file.name.toLowerCase().endsWith('.txt')) {
                const reader = new FileReader();
                reader.onload = (evt) => {
                    summaryInput.value = evt.target.result;
                };
                reader.readAsText(file);
                return;
            }

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
            processBtn.click();
        });
    }

    clearBtn.addEventListener('click', () => {
        summaryInput.value = '';
        resultsArea.classList.add('hidden');
        if (familyViewSection) familyViewSection.classList.add('hidden');
        currentResult = null;
        if (uploadFilenameDisplay) uploadFilenameDisplay.textContent = 'No file chosen';
        if (caseIdDisplay) caseIdDisplay.textContent = 'Unassigned';
        if (doctorFeedbackBanner) doctorFeedbackBanner.classList.add('hidden');
        syncDoctorWorkflow('PENDING');
        stopReminderTicker();
        activeReminders = [];
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

            // Mandatory Clinical Safety Protocol:
            // If case is PENDING and care plan data is withheld pending doctor review:
            if (data.status === 'PENDING' && !data.medicines) {
                const modalPending = document.getElementById('pending-review-modal');
                const modalPendingId = document.getElementById('modal-pending-case-id');
                const btnProceedDoc = document.getElementById('btn-proceed-doctor-login');
                const btnClosePending = document.getElementById('btn-close-pending-modal');
                const btnViewNotif = document.getElementById('btn-view-notif-history');

                // Save known case ID in localStorage
                addKnownCaseId(data.case_id);

                if (modalPendingId) modalPendingId.textContent = data.case_id;
                if (btnProceedDoc && data.redirect_url) btnProceedDoc.href = data.redirect_url;
                if (modalPending) modalPending.classList.remove('hidden');

                if (btnClosePending) {
                    btnClosePending.onclick = () => {
                        modalPending.classList.add('hidden');
                    };
                }

                if (btnViewNotif) {
                    btnViewNotif.onclick = () => {
                        modalPending.classList.add('hidden');
                        const notifSec = document.getElementById('patient-notifications-section');
                        if (notifSec) notifSec.scrollIntoView({ behavior: 'smooth' });
                    };
                }

                // Immediately refresh and display persistent notification history
                loadPatientNotifications();
                return;
            }

            currentResult = data;
            currentResult._raw_source_text = text;

            // Load or initialize medication reminders
            initMedicationReminders(data);

            // Render view in currently selected language
            renderFullCarePlan(currentResult, currentLang);
            saveToSessionHistory(data);

            resultsArea.classList.remove('hidden');
            resultsArea.scrollIntoView({ behavior: 'smooth' });
        } catch (err) {
            alert(`Processing error: ${err.message}`);
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    });

    // -------------------------------------------------------------
    // URL Query Parameter Listener (e.g. /?case_id=CB-XXXXX)
    // -------------------------------------------------------------
    const urlParams = new URLSearchParams(window.location.search);
    const initialCaseId = urlParams.get('case_id');
    if (initialCaseId) {
        loadApprovedCase(initialCaseId);
    }

    async function loadApprovedCase(caseId) {
        loadingSpinner.classList.remove('hidden');
        loadingSpinner.querySelector('p').textContent = `Retrieving verified clinical case ${caseId}...`;
        try {
            const resp = await fetch(`/api/case/${encodeURIComponent(caseId)}`);
            if (resp.status === 403) {
                const errData = await resp.json();
                const modalPending = document.getElementById('pending-review-modal');
                const modalPendingId = document.getElementById('modal-pending-case-id');
                const modalPendingTitle = document.getElementById('pending-modal-title');
                const btnProceedDoc = document.getElementById('btn-proceed-doctor-login');
                if (modalPendingId) modalPendingId.textContent = caseId;
                if (modalPendingTitle) {
                    modalPendingTitle.textContent = errData.status === 'CHANGES_REQUESTED'
                        ? 'Corrections Requested by Attending Doctor'
                        : 'Care Plan Awaiting Physician Review';
                }
                if (btnProceedDoc) {
                    btnProceedDoc.href = `/doctor/login?next=/doctor/case/${encodeURIComponent(caseId)}`;
                }
                if (modalPending) modalPending.classList.remove('hidden');
                return;
            }

            if (!resp.ok) {
                alert(`Case ${caseId} not found.`);
                return;
            }

            const caseRecord = await resp.json();
            addKnownCaseId(caseId);
            loadPatientNotifications();
            if (caseRecord.status === 'APPROVED' && caseRecord.care_plan_data) {
                currentResult = caseRecord.care_plan_data;
                currentResult.case_id = caseRecord.id;
                currentResult.doctor_review_status = caseRecord.status;
                currentResult.approval_info = caseRecord.approval_info;
                currentResult.latest_change_request = caseRecord.latest_change_request;
                if (caseRecord.original_text && summaryInput) {
                    summaryInput.value = caseRecord.original_text;
                }

                initMedicationReminders(currentResult);
                renderFullCarePlan(currentResult, currentLang);
                saveToSessionHistory(currentResult);
                resultsArea.classList.remove('hidden');
                resultsArea.scrollIntoView({ behavior: 'smooth' });
            } else {
                alert(`Case ${caseId} is awaiting doctor review.`);
            }
        } catch (e) {
            console.error('Failed to load case:', e);
        } finally {
            loadingSpinner.classList.add('hidden');
        }
    }

    // -------------------------------------------------------------
    // 4. Patient Notifications & Case Activity History
    // -------------------------------------------------------------
    let cachedNotifications = [];

    function getKnownCaseIds() {
        try {
            const raw = localStorage.getItem('carebridge_known_cases');
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    function addKnownCaseId(caseId) {
        if (!caseId) return;
        const current = getKnownCaseIds();
        if (!current.includes(caseId)) {
            current.unshift(caseId);
            localStorage.setItem('carebridge_known_cases', JSON.stringify(current.slice(0, 30)));
        }
    }

    async function loadPatientNotifications() {
        const knownCases = getKnownCaseIds();

        try {
            let url = '/api/patient/notifications';
            if (knownCases.length > 0) {
                url += `?case_ids=${encodeURIComponent(knownCases.join(','))}`;
            }

            const resp = await fetch(url);
            if (!resp.ok) return;

            const data = await resp.json();
            cachedNotifications = data.notifications || [];

            renderNotificationsList(cachedNotifications, currentLang);
        } catch (err) {
            console.warn('Could not load patient notifications:', err);
        }
    }

    function renderNotificationsList(notifications, lang) {
        const notifListEl = document.getElementById('notifications-list');
        const notifBadge = document.getElementById('notifications-count-badge');
        if (!notifListEl) return;

        const isTe = (lang === 'te');

        if (!notifications || notifications.length === 0) {
            notifListEl.innerHTML = `
                <div id="notifications-empty-state" class="notifications-empty" style="text-align: center; padding: 2rem 1rem; color: #64748b;">
                    <div style="font-size: 2.25rem; margin-bottom: 0.5rem;">📋</div>
                    <h4 style="margin: 0 0 0.35rem 0; font-size: 1.05rem; color: var(--navy);">${isTe ? 'ఇంకా ఎలాంటి కేస్ యాక్టివిటీ లేదు' : 'No Case Activity Yet'}</h4>
                    <p class="text-sm text-muted" style="margin: 0;">
                        ${isTe ? 'పై భాగంలో డిశ్చార్జ్ సారాంశాన్ని ఎంచుకోండి లేదా అప్‌లోడ్ చేసి వైద్యుల సమీక్ష కోసం సమర్పించండి.' : 'Select or upload a discharge summary above and click "Convert to Patient Care Plan" to initiate physician review.'}
                    </p>
                </div>
            `;
            if (notifBadge) notifBadge.textContent = isTe ? '0 అప్‌డేట్‌లు' : '0 Updates';
            return;
        }

        if (notifBadge) {
            notifBadge.textContent = isTe ? `${notifications.length} అప్‌డేట్‌లు` : `${notifications.length} Updates`;
        }

        notifListEl.innerHTML = '';

        notifications.forEach(n => {
            const card = document.createElement('div');
            const eventType = (n.event_type || 'PLAN_SUBMITTED').toUpperCase();

            let typeClass = 'notif-plan-submitted';
            let icon = '📤';
            if (eventType === 'PLAN_APPROVED') {
                typeClass = 'notif-plan-approved';
                icon = '✅';
            } else if (eventType === 'CHANGES_REQUESTED') {
                typeClass = 'notif-changes-requested';
                icon = '⚠️';
            } else if (eventType === 'PLAN_RESUBMITTED') {
                typeClass = 'notif-plan-resubmitted';
                icon = '🔄';
            }

            card.className = `notif-card-item ${typeClass}`;

            const title = isTe && n.title_te ? n.title_te : n.title;
            const message = isTe && n.message_te ? n.message_te : n.message;
            const statusBadgeText = isTe && n.status_badge_te ? n.status_badge_te : n.status_badge;

            let badgeClass = 'badge-draft';
            if (n.status_badge === 'APPROVED') badgeClass = 'badge-pass';
            else if (n.status_badge === 'CHANGES REQUESTED') badgeClass = 'badge-fail';

            const timeStr = n.created_at ? n.created_at.substring(0, 16).replace('T', ' ') + ' UTC' : '';

            let docInfoHtml = '';
            if (n.doctor_name) {
                docInfoHtml = `<span class="notif-meta-item"><strong>${isTe ? 'డాక్టర్' : 'Doctor'}:</strong> ${escapeHtml(n.doctor_name)} ${n.doctor_license ? `(${escapeHtml(n.doctor_license)})` : ''}</span>`;
            }

            let commentsHtml = '';
            if (n.comments) {
                commentsHtml = `<div style="margin-top: 0.4rem; padding: 0.4rem 0.6rem; background: rgba(0,0,0,0.03); border-radius: 4px; font-style: italic; font-size: 0.88rem;"><strong>${isTe ? 'డాక్టర్ గమనిక' : 'Physician Note'}:</strong> "${escapeHtml(n.comments)}"</div>`;
            }

            let actionHtml = '';
            if (n.status_badge === 'APPROVED') {
                actionHtml = `
                    <div class="notif-card-action">
                        <button class="btn btn-primary btn-sm btn-view-approved-case" data-case-id="${escapeHtml(n.case_id)}" style="display: inline-flex; align-items: center; gap: 0.35rem;">
                            <span>${isTe ? 'ఆమోదించబడిన కేర్ ప్లాన్ చూడండి' : 'View Approved Care Plan'} (v${n.case_version}) &rarr;</span>
                        </button>
                    </div>
                `;
            } else if (n.status_badge === 'CHANGES REQUESTED') {
                actionHtml = `
                    <div class="notif-card-action">
                        <a href="/doctor/case/${escapeHtml(n.case_id)}" class="btn btn-secondary btn-sm" target="_blank" style="text-decoration: none;">
                            <span>${isTe ? 'దిద్దుబాట్లను పరిశీలించండి' : 'Review Requested Changes'} &rarr;</span>
                        </a>
                    </div>
                `;
            } else {
                actionHtml = `
                    <div class="notif-card-action">
                        <span class="text-xs text-muted" style="display: inline-flex; align-items: center; gap: 0.3rem;">
                            <span>⏳ ${isTe ? 'హాస్పిటల్ డాక్టర్ క్లినికల్ సమీక్ష కోసం వేచి ఉంది' : 'Awaiting physician chart review'}</span>
                        </span>
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="notif-card-header">
                    <div class="notif-card-title-row">
                        <span class="notif-event-icon">${icon}</span>
                        <h4 class="notif-card-title">${escapeHtml(title)}</h4>
                    </div>
                    <span class="badge ${badgeClass}">${escapeHtml(statusBadgeText)}</span>
                </div>
                <div class="notif-card-body">
                    ${escapeHtml(message)}
                    ${commentsHtml}
                </div>
                <div class="notif-card-meta">
                    <span class="notif-meta-item"><strong>${isTe ? 'కేస్ ఐడి' : 'Case ID'}:</strong> <code>${escapeHtml(n.case_id)}</code></span>
                    <span class="notif-meta-item"><strong>${isTe ? 'వెర్షన్' : 'Version'}:</strong> v${escapeHtml(n.case_version)}</span>
                    <span class="notif-meta-item"><strong>${isTe ? 'సమయం' : 'Time'}:</strong> ${escapeHtml(timeStr)}</span>
                    ${docInfoHtml}
                </div>
                ${actionHtml}
            `;

            notifListEl.appendChild(card);
        });

        // Attach event listeners to all "View Approved Care Plan" buttons
        notifListEl.querySelectorAll('.btn-view-approved-case').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetCaseId = e.currentTarget.getAttribute('data-case-id');
                if (targetCaseId) {
                    loadApprovedCase(targetCaseId);
                }
            });
        });
    }

    const btnRefreshNotifs = document.getElementById('btn-refresh-notifications');
    if (btnRefreshNotifs) {
        btnRefreshNotifs.addEventListener('click', () => {
            loadPatientNotifications();
        });
    }

    // -------------------------------------------------------------
    // 5. Complete English / Telugu Summary Switch
    // -------------------------------------------------------------
    function setLanguage(lang) {
        currentLang = lang;

        // Sync header buttons
        if (btnHeaderLangEn) btnHeaderLangEn.classList.toggle('active', lang === 'en');
        if (btnHeaderLangTe) btnHeaderLangTe.classList.toggle('active', lang === 'te');

        // Sync toolbar buttons
        if (btnViewLangEn) btnViewLangEn.classList.toggle('active', lang === 'en');
        if (btnViewLangTe) btnViewLangTe.classList.toggle('active', lang === 'te');

        // Update download button labels
        const pdfLabel = lang === 'te' ? 'Download PDF (తెలుగు)' : 'Download PDF';
        const imgLabel = lang === 'te' ? 'Download Image (PNG - తెలుగు)' : 'Download Image (PNG)';

        const quickPdf = document.getElementById('quick-pdf-label');
        if (quickPdf) quickPdf.textContent = pdfLabel;
        const quickImg = document.getElementById('quick-img-label');
        if (quickImg) quickImg.textContent = imgLabel;

        const btnPdfText = document.getElementById('btn-pdf-text');
        if (btnPdfText) btnPdfText.textContent = pdfLabel;
        const btnImgText = document.getElementById('btn-img-text');
        if (btnImgText) btnImgText.textContent = imgLabel;

        // Sync notification headers and re-render
        const notifTitle = document.getElementById('notif-section-title');
        const notifSubtitle = document.getElementById('notif-section-subtitle');
        const btnRefreshLabel = document.getElementById('btn-refresh-notif-label');

        if (notifTitle) notifTitle.textContent = lang === 'te' ? 'కేర్ ప్లాన్ అప్డేట్స్ మరియు నోటిఫికేషన్లు' : 'Care Plan Updates & Notifications';
        if (notifSubtitle) notifSubtitle.textContent = lang === 'te' ? 'కేర్ ప్లాన్ సమర్పణలు, వైద్యుల సమీక్షలు మరియు క్లినికల్ ఆమోదాల కాలక్రమానుసార రికార్డు.' : 'Chronological record of care plan submissions, physician reviews, and clinical approvals.';
        if (btnRefreshLabel) btnRefreshLabel.textContent = lang === 'te' ? 'తాజా అప్‌డేట్‌లు' : 'Check Updates';

        if (cachedNotifications && cachedNotifications.length > 0) {
            renderNotificationsList(cachedNotifications, lang);
        }

        // If results are visible, re-render
        if (currentResult) {
            renderFullCarePlan(currentResult, currentLang);
            if (familyViewSection && !familyViewSection.classList.contains('hidden')) {
                renderFamilyView(currentResult, currentLang);
            }
        }
    }

    if (btnHeaderLangEn) btnHeaderLangEn.addEventListener('click', () => setLanguage('en'));
    if (btnHeaderLangTe) btnHeaderLangTe.addEventListener('click', () => setLanguage('te'));
    if (btnViewLangEn) btnViewLangEn.addEventListener('click', () => setLanguage('en'));
    if (btnViewLangTe) btnViewLangTe.addEventListener('click', () => setLanguage('te'));

    function renderFullCarePlan(data, lang) {
        const isTe = (lang === 'te');

        // 1. Patient Verification Banner & Doctor Review Status
        renderPatientVerification(data.validation, isTe, data.doctor_review_status, data);
        updateDoctorReviewStatusDisplay(data, isTe);

        // 2. Daily Medication Schedule
        const sched = isTe && data.telugu_structured && data.telugu_structured.medication_schedule
            ? data.telugu_structured.medication_schedule
            : data.medication_schedule;
        renderDailySchedule(sched, isTe);

        // 3. Medication Reminders Section
        renderRemindersTable(isTe);

        // 4. Active Medicines Table
        renderActiveMedicinesTable(data, isTe);

        // 5. Discontinued Medicines
        renderStopMedicines(data, isTe);

        // 6. Follow-up Appointments
        renderFollowUps(data, isTe);

        // 7. Warning Signs, Diet, Activity
        renderClinicalGuidance(data, isTe);

        // 8. Bilingual Plans Display
        document.getElementById('english-care-plan').textContent = data.english_plan || '';
        document.getElementById('telugu-care-plan').textContent = data.telugu_plan || '';

        // 9. Readability
        if (data.readability) {
            document.getElementById('readability-grade').textContent = data.readability.score || 'N/A';
            document.getElementById('readability-desc').textContent = data.readability.reading_level || '';
            document.getElementById('readability-expl').textContent = data.readability.explanation || '';
        }

        // 10. Source Traceability
        renderComparisonInspector(data);

        // 11. Family Fridge Sheet
        const fridgeMode = fridgeLangSelect ? fridgeLangSelect.value : (isTe ? 'te' : 'bilingual');
        populateFridgeSheet(data, fridgeMode);
    }

    // -------------------------------------------------------------
    // 5. Verification Banner & Doctor Review Sync
    // -------------------------------------------------------------
    function renderPatientVerification(val, isTe, docStatus, fullData) {
        val = val || {};
        const bannerCard = document.querySelector('.patient-verification-card');
        const iconBox = document.getElementById('verification-icon-box');
        const titleEl = document.getElementById('patient-status-title');
        const descEl = document.getElementById('patient-status-desc');

        const overallStatus = val.overall_status || 'NEEDS_REVIEW';
        const isApproved = (docStatus === 'APPROVED') || (fullData && fullData.doctor_review_status === 'APPROVED');
        const docName = (fullData && fullData.approval_info && fullData.approval_info.doctor_name) || 'Attending Physician';
        const docLicense = (fullData && fullData.approval_info && fullData.approval_info.doctor_license) || '';

        bannerCard.classList.remove('banner-pass', 'banner-fail', 'banner-incomplete');

        if (isApproved) {
            bannerCard.classList.add('banner-pass');
            if (overallStatus === 'PASS') {
                titleEl.textContent = isTe
                    ? 'సాంకేతిక ధృవీకరణ: ఉత్తీర్ణత (PASS) — వైద్యులు ఆమోదించారు'
                    : 'TECHNICAL VALIDATION: PASS — APPROVED BY ATTENDING PHYSICIAN';
                descEl.textContent = isTe
                    ? `డాక్టర్ ${docName} గారిచే సమీక్షించబడి, డిశ్చార్జ్ సారాంశం ప్రకారం ధృవీకరించబడింది.`
                    : `Reviewed and clinically certified by ${docName} (${docLicense}). All prescribed medications, dosages, and dates match hospital discharge orders.`;
            } else {
                titleEl.textContent = isTe
                    ? 'సాంకేతిక ఆడిట్: వైద్యులు సమీక్షించి ధృవీకరించారు (FLAGGED — ACKNOWLEDGED)'
                    : 'TECHNICAL AUDIT: FLAGGED — ACKNOWLEDGED & CERTIFIED BY PHYSICIAN';
                descEl.textContent = isTe
                    ? `క్లినికల్ ఫ్లాగ్‌లను డాక్టర్ ${docName} పరిశీలించి రోగి విడుదల కోసం ఆమోదించారు.`
                    : `The attending physician ${docName} (${docLicense}) has examined all extracted instructions and clinical audit flags and certified this care plan for patient release.`;
            }
            iconBox.innerHTML = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
        } else if (overallStatus === 'PASS') {
            bannerCard.classList.add('banner-pass');
            titleEl.textContent = isTe ? 'సాంకేతిక ధృవీకరణ: ఉత్తీర్ణత (PASS)' : 'TECHNICAL VALIDATION: PASS';
            descEl.textContent = isTe
                ? 'ఔషధాల మోతాదులు, సమయాలు మరియు తేదీలు డిశ్చార్జ్ సారాంశం ప్రకారం ఖచ్చితంగా సరిపోలాయి.'
                : 'All extracted medications, dosages, and dates are grounded in the source discharge summary.';
            iconBox.innerHTML = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
        } else if (overallStatus === 'FAIL') {
            bannerCard.classList.add('banner-fail');
            titleEl.textContent = isTe ? 'సాంకేతిక ధృవీకరణ: లోపం (FAIL)' : 'TECHNICAL VALIDATION: FAIL';
            descEl.textContent = val.patient_message || (isTe ? 'క్లినికల్ భద్రతా లోపం గుర్తించబడింది.' : 'A clinical safety concern was flagged.');
            iconBox.innerHTML = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
        } else {
            bannerCard.classList.add('banner-incomplete');
            titleEl.textContent = isTe ? 'సాంకేతిక ధృవీకరణ: పెండింగ్ సమీక్ష (PENDING PHYSICIAN REVIEW)' : 'TECHNICAL VALIDATION: PENDING PHYSICIAN REVIEW';
            descEl.textContent = isTe
                ? 'క్లినికల్ మోతాదులు మరియు సూచనలను హాస్పిటల్ డాక్టర్ పోర్టల్‌లో నిర్ధారించవలసి ఉంది.'
                : 'Clinical dosages and instructions are awaiting attending doctor certification in the Doctor Portal.';
            iconBox.innerHTML = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
        }

        // Checklist Pills
        const items = val.items || [];
        updateCheckPill('check-meds-pill', items.filter(i => i.check_name.includes('Medication')));
        updateCheckPill('check-stops-pill', items.filter(i => i.check_name.includes('Discontinued')));
        updateCheckPill('check-doses-pill', items.filter(i => i.check_name.includes('Dose')));
        updateCheckPill('check-dates-pill', items.filter(i => i.check_name.includes('Follow-Up')));

        // Audit Table
        const checksBody = document.querySelector('#validation-table tbody');
        if (checksBody) {
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

    function updateDoctorReviewStatusDisplay(data, isTe) {
        if (!data) return;
        const caseId = data.case_id || 'CB-PENDING';
        if (caseIdDisplay) caseIdDisplay.textContent = caseId;
        if (openDocBtn) openDocBtn.href = `/doctor/case/${caseId}`;

        const status = (data.doctor_review_status || 'PENDING').toUpperCase();

        if (status === 'APPROVED') {
            const docName = (data.approval_info && data.approval_info.doctor_name) || 'Attending Physician';
            const docLicense = (data.approval_info && data.approval_info.doctor_license) || 'Certified MD';
            const timeStr = (data.approval_info && data.approval_info.created_at) ? data.approval_info.created_at.substring(0, 16).replace('T', ' ') + ' UTC' : '';

            syncDoctorWorkflow('APPROVED', docName);

            if (doctorFeedbackBanner) {
                doctorFeedbackBanner.className = 'alert-message alert-success';
                doctorFeedbackBanner.innerHTML = isTe
                    ? `<strong>🛡️ వైద్యులచే ఆమోదించబడింది (APPROVED):</strong> డాక్టర్ <strong>${escapeHtml(docName)}</strong> (${escapeHtml(docLicense)}) చే ${escapeHtml(timeStr)} న ధృవీకరించబడింది.`
                    : `<strong>🛡️ Clinically Certified for Patient Release:</strong> Approved by <strong>${escapeHtml(docName)}</strong> (${escapeHtml(docLicense)}) on ${escapeHtml(timeStr)}.`;
                doctorFeedbackBanner.classList.remove('hidden');
            }
        } else if (status === 'CHANGES_REQUESTED') {
            const docName = (data.latest_change_request && data.latest_change_request.doctor_name) || 'Attending Physician';
            const comments = (data.latest_change_request && data.latest_change_request.comments) || 'Corrections requested.';

            syncDoctorWorkflow('CHANGES_REQUESTED');

            if (doctorFeedbackBanner) {
                doctorFeedbackBanner.className = 'alert-message alert-error';
                doctorFeedbackBanner.innerHTML = isTe
                    ? `<strong>⚠️ వైద్యుల పరిశీలన: మార్పులు అవసరం (CHANGES REQUESTED):</strong> డాక్టర్ ${escapeHtml(docName)} సూచన: <em>"${escapeHtml(comments)}"</em>.`
                    : `<strong>⚠️ Physician Requested Corrections:</strong> ${escapeHtml(docName)} noted: <em>"${escapeHtml(comments)}"</em>.`;
                doctorFeedbackBanner.classList.remove('hidden');
            }
        } else {
            syncDoctorWorkflow('PENDING');
            if (doctorFeedbackBanner) {
                doctorFeedbackBanner.className = 'alert-message';
                doctorFeedbackBanner.style.background = '#f8fafc';
                doctorFeedbackBanner.style.border = '1px solid #e2e8f0';
                doctorFeedbackBanner.style.color = '#475569';
                doctorFeedbackBanner.innerHTML = isTe
                    ? `<span>ℹ️ <strong>వైద్యుల పరిశీలన:</strong> ఈ సంరక్షణ ప్రణాళిక డాక్టర్ పోర్టల్‌లో సమీక్ష కొరకు వేచి ఉంది (Case Ref: <code>${escapeHtml(caseId)}</code>).</span>`
                    : `<span>ℹ️ <strong>Clinical Protocol Notice:</strong> This care plan has been queued in the Doctor Portal (Case Ref: <code>${escapeHtml(caseId)}</code>). Final patient distribution requires physician review.</span>`;
                doctorFeedbackBanner.classList.remove('hidden');
            }
        }
    }

    function syncDoctorWorkflow(status, docName) {
        let badgeClass = 'badge badge-draft';
        let label = 'Doctor Review: PENDING';

        if (status === 'APPROVED') {
            badgeClass = 'badge badge-pass';
            label = docName ? `Doctor Review: APPROVED BY ${docName}` : 'Doctor Review: APPROVED';
        } else if (status === 'CHANGES_REQUESTED') {
            badgeClass = 'badge badge-fail';
            label = 'Doctor Review: CHANGES REQUESTED';
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

    // -------------------------------------------------------------
    // 6. Daily Medication Schedule
    // -------------------------------------------------------------
    function renderDailySchedule(sched, isTe) {
        sched = sched || { morning: [], afternoon: [], night: [], as_needed: [], unspecified: [] };

        const schedHeading = document.getElementById('schedule-heading');
        if (schedHeading) {
            schedHeading.textContent = isTe ? 'దినసరి మందుల సమయ పట్టిక' : 'Daily Medication Schedule';
        }

        renderSlot('slot-morning-items', sched.morning, isTe ? 'ఉదయం మందులు లేవు' : 'No morning medicines scheduled');
        renderSlot('slot-afternoon-items', sched.afternoon, isTe ? 'మధ్యాహ్నం మందులు లేవు' : 'No afternoon medicines scheduled');
        renderSlot('slot-night-items', sched.night, isTe ? 'రాత్రి మందులు లేవు' : 'No night medicines scheduled');
        renderSlot('slot-sos-items', sched.as_needed, isTe ? 'అవసరమైనప్పుడు వేసుకునే మందులు లేవు' : 'No SOS medicines scheduled');

        const unspecCol = document.getElementById('slot-unspecified-col');
        if (sched.unspecified && sched.unspecified.length > 0) {
            if (unspecCol) unspecCol.classList.remove('hidden');
            renderSlot('slot-unspecified-items', sched.unspecified, '');
        } else {
            if (unspecCol) unspecCol.classList.add('hidden');
        }
    }

    function renderSlot(containerId, items, emptyText) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = '';

        if (!items || items.length === 0) {
            el.innerHTML = `<div class="slot-empty">${escapeHtml(emptyText)}</div>`;
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
    // 7. Active Medicines Table
    // -------------------------------------------------------------
    function renderActiveMedicinesTable(data, isTe) {
        const medTableBody = document.querySelector('#medicines-table tbody');
        if (!medTableBody) return;
        medTableBody.innerHTML = '';

        const medHeading = document.querySelector('#medicines-table').closest('.card').querySelector('.card-header h3');
        if (medHeading) {
            medHeading.textContent = isTe ? 'ఇంట్లో వేసుకోవలసిన మందులు (Active Prescriptions)' : 'Active Prescribed Medications';
        }

        const thCols = document.querySelectorAll('#medicines-table thead th');
        if (thCols && thCols.length === 6) {
            thCols[0].textContent = isTe ? 'మందు పేరు (Medicine)' : 'Medicine';
            thCols[1].textContent = isTe ? 'మోతాదు (Dose)' : 'Dose';
            thCols[2].textContent = isTe ? 'పద్ధతి (Frequency)' : 'Frequency';
            thCols[3].textContent = isTe ? 'సమయం (Timing)' : 'Timing';
            thCols[4].textContent = isTe ? 'వ్యవధి (Duration)' : 'Duration';
            thCols[5].textContent = isTe ? 'ఎలా వేసుకోవాలి (How to Take)' : 'How to Take';
        }

        const list = (isTe && data.telugu_structured && data.telugu_structured.medicines)
            ? data.telugu_structured.medicines
            : data.medicines;

        if (list && list.length > 0) {
            list.forEach(m => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="font-bold text-navy">${escapeHtml(m.name)}</td>
                    <td><span class="badge badge-dose">${escapeHtml(m.dose)}</span></td>
                    <td>${escapeHtml(isTe ? (m.frequency_te || m.frequency) : m.frequency)}</td>
                    <td>${escapeHtml(isTe ? (m.timing_te || m.timing) : m.timing)}</td>
                    <td>${escapeHtml(isTe ? (m.duration_te || m.duration) : m.duration)}</td>
                    <td>${escapeHtml(isTe ? (m.how_to_take_plain_te || m.how_to_take_plain) : m.how_to_take_plain)}</td>
                `;
                medTableBody.appendChild(row);
            });
        } else {
            medTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">${isTe ? 'మందులు లేవు.' : 'No active medications found in summary.'}</td></tr>`;
        }
    }

    // -------------------------------------------------------------
    // 8. Discontinued / Stopped Medicines
    // -------------------------------------------------------------
    function renderStopMedicines(data, isTe) {
        const stopContainer = document.getElementById('stop-medicines-list');
        if (!stopContainer) return;
        stopContainer.innerHTML = '';

        const stopCardHeader = stopContainer.closest('.card').querySelector('.card-header h3');
        if (stopCardHeader) {
            stopCardHeader.textContent = isTe ? 'నిలిపివేయవలసిన మందులు (Discontinued Drugs)' : 'Discontinued / Stopped Medications';
        }

        const stops = (isTe && data.telugu_structured && data.telugu_structured.stop_medicines)
            ? data.telugu_structured.stop_medicines
            : data.stop_medicines;

        if (stops && stops.length > 0) {
            stops.forEach(sm => {
                const item = document.createElement('div');
                item.className = 'stop-pill';
                const label = isTe ? 'వాడటం ఆపండి (STOP)' : 'STOP';
                item.innerHTML = `<strong>${label}: ${escapeHtml(sm.name)}</strong> <span>(${escapeHtml(sm.reason || 'Discontinued')})</span>`;
                stopContainer.appendChild(item);
            });
        } else {
            stopContainer.innerHTML = `<span class="text-muted">${isTe ? 'పాత మందులలో వేటినీ ఆపవలసిన అవసరం లేదు.' : 'No medicines were marked for discontinuation. Continue only prescribed items.'}</span>`;
        }
    }

    // -------------------------------------------------------------
    // 9. Follow-up Appointments
    // -------------------------------------------------------------
    function renderFollowUps(data, isTe) {
        const fuTableBody = document.querySelector('#followup-table tbody');
        if (!fuTableBody) return;
        fuTableBody.innerHTML = '';

        const fuHeader = fuTableBody.closest('.card').querySelector('.card-header h3');
        if (fuHeader) {
            fuHeader.textContent = isTe ? 'తదుపరి సమీక్ష తేదీలు (Scheduled Appointments)' : 'Scheduled Follow-up Appointments';
        }

        const fuCols = document.querySelectorAll('#followup-table thead th');
        if (fuCols && fuCols.length === 3) {
            fuCols[0].textContent = isTe ? 'తేదీ (Date)' : 'Date';
            fuCols[1].textContent = isTe ? 'వైద్యుడు / విభాగం (Doctor / Dept)' : 'Department / Doctor';
            fuCols[2].textContent = isTe ? 'పరీక్ష ఉద్దేశం (Purpose)' : 'Purpose';
        }

        const fus = data.follow_ups;
        if (fus && fus.length > 0) {
            fus.forEach(fu => {
                const r = document.createElement('tr');
                r.innerHTML = `
                    <td class="font-bold">${escapeHtml(fu.date)}</td>
                    <td>${escapeHtml(fu.with_whom)}</td>
                    <td>${escapeHtml(fu.purpose)}</td>
                `;
                fuTableBody.appendChild(r);
            });
        } else {
            fuTableBody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">${isTe ? 'ప్రత్యేక సమీక్ష తేదీ పేర్కొనబడలేదు. వైద్యుడిని సంప్రదించండి.' : 'Not specified in discharge summary. Please verify with your healthcare provider.'}</td></tr>`;
        }
    }

    // -------------------------------------------------------------
    // 10. Warning Signs, Diet, and Activity Guidance
    // -------------------------------------------------------------
    function renderClinicalGuidance(data, isTe) {
        const telStruct = data.telugu_structured || {};

        const warns = isTe && telStruct.warning_signs ? telStruct.warning_signs : data.warning_signs;
        const diet = isTe && telStruct.diet ? telStruct.diet : data.diet;
        const act = isTe && telStruct.activity ? telStruct.activity : data.activity;

        renderList('warnings-list', warns);
        renderList('diet-list', diet);
        renderList('activity-list', act);
    }

    // -------------------------------------------------------------
    // 11. Medication Reminders & Timers Engine
    // -------------------------------------------------------------
    function initMedicationReminders(data) {
        const meds = data.medicines || [];
        const storageKey = `carebridge_reminders_${data.case_id || data.summary_id || 'DEFAULT'}`;

        // Load existing saved reminders for this case if available
        const saved = localStorage.getItem(storageKey);
        if (saved) {
            try {
                activeReminders = JSON.parse(saved);
                startReminderTicker();
                return;
            } catch (e) {
                console.warn('Failed to parse saved reminders:', e);
            }
        }

        // Generate clean initial reminder schedule strictly based on prescription facts
        activeReminders = [];
        let rIndex = 1;

        meds.forEach(m => {
            const freq = (m.frequency || '').toLowerCase();
            const timing = (m.timing || '').toLowerCase();
            const name = m.name;
            const dose = m.dose;

            // Check SOS / PRN
            if (freq.includes('sos') || freq.includes('prn') || freq.includes('as needed') || timing.includes('sos')) {
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'When required for symptoms',
                    slotLabel: 'As Needed (SOS)',
                    reminderTime: null,
                    unspecified: false,
                    isSos: true,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
                return;
            }

            // Check if multiple daily doses (BID / TDS / QID / 1-0-1 / 1-1-1)
            if (freq.includes('1-0-1') || freq.includes('bd') || freq.includes('bid') || freq.includes('twice daily')) {
                // Dose 1: Morning
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'Morning dose',
                    slotLabel: 'Morning Dose',
                    reminderTime: '08:00',
                    unspecified: false,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
                // Dose 2: Night
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'Night dose',
                    slotLabel: 'Night / Bedtime Dose',
                    reminderTime: '20:00',
                    unspecified: false,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
                return;
            }

            if (freq.includes('1-1-1') || freq.includes('tds') || freq.includes('tid') || freq.includes('thrice daily')) {
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'Morning dose',
                    slotLabel: 'Morning Dose',
                    reminderTime: '08:00',
                    unspecified: false,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'Afternoon dose',
                    slotLabel: 'Afternoon Dose',
                    reminderTime: '13:00',
                    unspecified: false,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'Night dose',
                    slotLabel: 'Night / Bedtime Dose',
                    reminderTime: '20:00',
                    unspecified: false,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
                return;
            }

            // Single daily doses: check morning vs night vs unspecified
            const isNight = freq.includes('0-0-1') || freq.includes('hs') || freq.includes('bedtime') || timing.includes('night') || timing.includes('bedtime');
            const isMorning = freq.includes('1-0-0') || timing.includes('morning') || timing.includes('empty stomach') || timing.includes('breakfast');

            if (isNight) {
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'Night / Bedtime',
                    slotLabel: 'Night / Bedtime Dose',
                    reminderTime: '20:00',
                    unspecified: false,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
            } else if (isMorning) {
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'Morning',
                    slotLabel: 'Morning Dose',
                    reminderTime: '08:00',
                    unspecified: false,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
            } else {
                // CLINICAL SAFETY GUARD: Unspecified timing
                // Do NOT assume arbitrary times like 8:00 AM!
                activeReminders.push({
                    id: `rem_${rIndex++}`,
                    medName: name,
                    dose: dose,
                    frequency: m.frequency,
                    prescribedTiming: m.timing || 'Timing not specified',
                    slotLabel: 'Timing Not Specified',
                    reminderTime: null,
                    unspecified: true,
                    status: 'Upcoming',
                    paused: false,
                    takenAt: null,
                    snoozedUntil: null
                });
            }
        });

        saveRemindersToStorage();
        startReminderTicker();
    }

    function saveRemindersToStorage() {
        if (!currentResult) return;
        const key = `carebridge_reminders_${currentResult.case_id || currentResult.summary_id || 'DEFAULT'}`;
        try {
            localStorage.setItem(key, JSON.stringify(activeReminders));
        } catch (e) {
            console.warn('Could not save reminders to localStorage:', e);
        }
    }

    function renderRemindersTable(isTe) {
        if (!remindersTableBody) return;
        remindersTableBody.innerHTML = '';

        // Table Column Headers
        const thMed = document.getElementById('th-rem-med');
        const thFreq = document.getElementById('th-rem-freq');
        const thTiming = document.getElementById('th-rem-timing');
        const thTime = document.getElementById('th-rem-time');
        const thCd = document.getElementById('th-rem-countdown');
        const thSt = document.getElementById('th-rem-status');
        const thAct = document.getElementById('th-rem-actions');

        if (thMed) thMed.textContent = isTe ? 'మందు & మోతాదు (Medicine)' : 'Medicine & Dose';
        if (thFreq) thFreq.textContent = isTe ? 'పద్ధతి (Frequency)' : 'Frequency';
        if (thTiming) thTiming.textContent = isTe ? 'సూచించిన సమయం (Prescribed Timing)' : 'Prescribed Timing';
        if (thTime) thTime.textContent = isTe ? 'రిమైండర్ సమయం (Time)' : 'Reminder Time';
        if (thCd) thCd.textContent = isTe ? 'కౌంట్‌డౌన్ (Countdown)' : 'Next Alarm Countdown';
        if (thSt) thSt.textContent = isTe ? 'స్థితి (Status)' : 'Status';
        if (thAct) thAct.textContent = isTe ? 'నియంత్రణలు (Controls)' : 'Controls';

        if (!activeReminders || activeReminders.length === 0) {
            remindersTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted">${isTe ? 'మందుల రిమైండర్లు ఏవీ లేవు.' : 'No active medication reminders configured.'}</td></tr>`;
            if (remindersSummaryStats) remindersSummaryStats.textContent = isTe ? '0 రిమైండర్లు యాక్టివ్‌గా ఉన్నాయి' : '0 reminders active';
            return;
        }

        let activeCount = 0;

        activeReminders.forEach(rem => {
            if (!rem.paused && rem.status !== 'Taken') activeCount++;

            const tr = document.createElement('tr');
            tr.id = `row-${rem.id}`;

            // Reminder Time Display
            let timeDisplay = '';
            if (rem.unspecified || !rem.reminderTime) {
                timeDisplay = `<span class="badge badge-fail" style="font-size: 0.78rem;">⚠️ ${isTe ? 'సమయం పేర్కొనబడలేదు' : 'Timing not specified'}</span>`;
            } else {
                timeDisplay = `<strong>${format12Hour(rem.reminderTime)}</strong> <span class="text-xs text-muted">(${escapeHtml(rem.slotLabel)})</span>`;
            }

            // Countdown & Status computation
            const cdData = computeReminderCountdown(rem, isTe);
            rem.status = cdData.status;

            // Status Badge
            const statusBadgeHtml = getReminderStatusBadge(rem.status, isTe);

            // Controls buttons
            let actionBtns = '';
            if (rem.status === 'Taken') {
                actionBtns = `
                    <button class="btn btn-outline btn-sm btn-action-undo" data-id="${rem.id}" title="Reset status to upcoming">
                        <span>↩️ ${isTe ? 'రీసెట్' : 'Reset'}</span>
                    </button>
                    <button class="btn btn-outline btn-sm btn-action-edit" data-id="${rem.id}">
                        <span>✏️ ${isTe ? 'సవరించు' : 'Edit'}</span>
                    </button>
                    <button class="btn btn-outline btn-sm btn-action-del" data-id="${rem.id}" style="color: #dc2626;">
                        <span>🗑️</span>
                    </button>
                `;
            } else if (rem.unspecified || !rem.reminderTime) {
                actionBtns = `
                    <button class="btn btn-primary btn-sm btn-action-set" data-id="${rem.id}">
                        <span>⏰ ${isTe ? 'సమయం సెట్ చేయండి' : 'Set Time'}</span>
                    </button>
                    <button class="btn btn-outline btn-sm btn-action-del" data-id="${rem.id}" style="color: #dc2626;">
                        <span>🗑️</span>
                    </button>
                `;
            } else {
                const pauseLabel = rem.paused ? (isTe ? '▶️ పునఃప్రారంభించు' : '▶️ Resume') : (isTe ? '⏸️ పాజ్' : '⏸️ Pause');
                actionBtns = `
                    <button class="btn btn-primary btn-sm btn-action-take" data-id="${rem.id}" title="Mark medicine as taken">
                        <span>✓ ${isTe ? 'వేసుకున్నాను' : 'Mark Taken'}</span>
                    </button>
                    <button class="btn btn-outline btn-sm btn-action-snooze" data-id="${rem.id}" title="Snooze for 10 minutes">
                        <span>💤 +10m</span>
                    </button>
                    <button class="btn btn-outline btn-sm btn-action-edit" data-id="${rem.id}">
                        <span>✏️</span>
                    </button>
                    <button class="btn btn-outline btn-sm btn-action-pause" data-id="${rem.id}">
                        <span>${pauseLabel}</span>
                    </button>
                    <button class="btn btn-outline btn-sm btn-action-del" data-id="${rem.id}" style="color: #dc2626;">
                        <span>🗑️</span>
                    </button>
                `;
            }

            tr.innerHTML = `
                <td>
                    <strong class="text-navy">${escapeHtml(rem.medName)}</strong>
                    <div><span class="badge badge-dose">${escapeHtml(rem.dose)}</span></div>
                </td>
                <td>${escapeHtml(rem.frequency)}</td>
                <td>${escapeHtml(rem.prescribedTiming)}</td>
                <td>${timeDisplay}</td>
                <td class="countdown-cell">${cdData.html}</td>
                <td>${statusBadgeHtml}</td>
                <td><div class="reminder-btn-group">${actionBtns}</div></td>
            `;

            remindersTableBody.appendChild(tr);
        });

        if (remindersSummaryStats) {
            remindersSummaryStats.textContent = isTe
                ? `${activeCount} రిమైండర్లు అమల్లో ఉన్నాయి (మొత్తం ${activeReminders.length})`
                : `${activeCount} reminders active (${activeReminders.length} total scheduled)`;
        }

        bindReminderActionEvents();
    }

    function computeReminderCountdown(rem, isTe) {
        if (rem.status === 'Taken') {
            const timeTaken = rem.takenAt ? new Date(rem.takenAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
            return {
                status: 'Taken',
                html: `<span class="countdown-badge countdown-taken">✓ ${isTe ? 'తీసుకున్నారు' : 'Taken'} (${timeTaken})</span>`
            };
        }

        if (rem.paused) {
            return {
                status: 'Upcoming',
                html: `<span class="countdown-badge">⏸️ ${isTe ? 'పాజ్ చేయబడింది' : 'Paused'}</span>`
            };
        }

        if (rem.unspecified || !rem.reminderTime) {
            return {
                status: 'Upcoming',
                html: `<span class="countdown-badge countdown-unspecified">⚠️ ${isTe ? 'సమయం పేర్కొనబడలేదు – మీ డాక్టర్‌ను సంప్రదించండి' : 'Timing not specified – confirm with doctor'}</span>`
            };
        }

        // Check if currently snoozed
        if (rem.snoozedUntil) {
            const diff = rem.snoozedUntil - Date.now();
            if (diff > 0) {
                return {
                    status: 'Snoozed',
                    html: `<span class="countdown-badge countdown-snoozed">💤 ${isTe ? 'వాయిదా' : 'Snoozed'}: ${formatSecondsToCountdown(Math.floor(diff / 1000))}</span>`
                };
            } else {
                rem.snoozedUntil = null;
                // Transition to Due Now!
                triggerReminderAlert(rem);
                return {
                    status: 'Due Now',
                    html: `<span class="countdown-badge countdown-duenow">🔔 ${isTe ? 'ఇప్పుడే వేసుకోవాలి!' : 'DUE NOW!'}</span>`
                };
            }
        }

        // Compute daily target time
        const parts = rem.reminderTime.split(':');
        const target = new Date();
        target.setHours(parseInt(parts[0], 10), parseInt(parts[1], 10), 0, 0);

        const diffMs = target.getTime() - Date.now();

        if (diffMs <= 0 && diffMs > -(15 * 60 * 1000)) {
            // Due within past 15 minutes
            if (rem.status !== 'Due Now') {
                triggerReminderAlert(rem);
            }
            return {
                status: 'Due Now',
                html: `<span class="countdown-badge countdown-duenow">🔔 ${isTe ? 'ఇప్పుడే వేసుకోవాలి!' : 'DUE NOW!'}</span>`
            };
        } else if (diffMs <= -(15 * 60 * 1000)) {
            // Missed by >15 mins
            const passedSecs = Math.abs(Math.floor(diffMs / 1000));
            return {
                status: 'Missed',
                html: `<span class="countdown-badge countdown-missed">⚠️ ${isTe ? 'మిస్ అయింది' : 'Missed'} (${formatSecondsToCountdown(passedSecs)} ${isTe ? 'క్రితం' : 'ago'})</span>`
            };
        } else {
            // Future today
            const remSecs = Math.floor(diffMs / 1000);
            return {
                status: 'Upcoming',
                html: `<span class="countdown-badge countdown-upcoming">⏱️ ${isTe ? 'ఇంకా' : 'In'} ${formatSecondsToCountdown(remSecs)}</span>`
            };
        }
    }

    function getReminderStatusBadge(status, isTe) {
        if (status === 'Due Now') {
            return `<span class="status-pill-reminder status-duenow">${isTe ? 'ఇప్పుడే వేసుకోవాలి' : 'Due Now'}</span>`;
        } else if (status === 'Taken') {
            return `<span class="status-pill-reminder status-taken">${isTe ? 'తీసుకున్నారు' : 'Taken'}</span>`;
        } else if (status === 'Snoozed') {
            return `<span class="status-pill-reminder status-snoozed">${isTe ? 'వాయిదా' : 'Snoozed'}</span>`;
        } else if (status === 'Missed') {
            return `<span class="status-pill-reminder status-missed">${isTe ? 'మిస్ అయింది' : 'Missed'}</span>`;
        }
        return `<span class="status-pill-reminder status-upcoming">${isTe ? 'రాబోయే సమయం' : 'Upcoming'}</span>`;
    }

    function bindReminderActionEvents() {
        // Mark as Taken
        document.querySelectorAll('.btn-action-take').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.getAttribute('data-id');
                const rem = activeReminders.find(r => r.id === id);
                if (rem) {
                    rem.status = 'Taken';
                    rem.takenAt = new Date().toISOString();
                    rem.snoozedUntil = null;
                    saveRemindersToStorage();
                    renderRemindersTable(currentLang === 'te');
                }
            });
        });

        // Undo Taken
        document.querySelectorAll('.btn-action-undo').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                const rem = activeReminders.find(r => r.id === id);
                if (rem) {
                    rem.status = 'Upcoming';
                    rem.takenAt = null;
                    rem.snoozedUntil = null;
                    saveRemindersToStorage();
                    renderRemindersTable(currentLang === 'te');
                }
            });
        });

        // Snooze 10 minutes
        document.querySelectorAll('.btn-action-snooze').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                const rem = activeReminders.find(r => r.id === id);
                if (rem) {
                    rem.status = 'Snoozed';
                    rem.snoozedUntil = Date.now() + (10 * 60 * 1000);
                    saveRemindersToStorage();
                    renderRemindersTable(currentLang === 'te');
                }
            });
        });

        // Pause / Resume
        document.querySelectorAll('.btn-action-pause').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                const rem = activeReminders.find(r => r.id === id);
                if (rem) {
                    rem.paused = !rem.paused;
                    saveRemindersToStorage();
                    renderRemindersTable(currentLang === 'te');
                }
            });
        });

        // Delete Reminder
        document.querySelectorAll('.btn-action-del').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                if (confirm('Delete this medication reminder?')) {
                    activeReminders = activeReminders.filter(r => r.id !== id);
                    saveRemindersToStorage();
                    renderRemindersTable(currentLang === 'te');
                }
            });
        });

        // Edit or Set Reminder
        document.querySelectorAll('.btn-action-edit, .btn-action-set').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.getAttribute('data-id');
                const rem = activeReminders.find(r => r.id === id);
                if (rem) openReminderModal(rem);
            });
        });
    }

    function startReminderTicker() {
        if (reminderTickerTimer) clearInterval(reminderTickerTimer);
        reminderTickerTimer = setInterval(() => {
            if (activeReminders && activeReminders.length > 0) {
                // Update countdown cells live without resetting full DOM
                activeReminders.forEach(rem => {
                    const row = document.getElementById(`row-${rem.id}`);
                    if (!row) return;

                    const cdCell = row.querySelector('.countdown-cell');
                    if (cdCell) {
                        const cd = computeReminderCountdown(rem, currentLang === 'te');
                        cdCell.innerHTML = cd.html;
                    }
                });
            }
        }, 1000);
    }

    function stopReminderTicker() {
        if (reminderTickerTimer) {
            clearInterval(reminderTickerTimer);
            reminderTickerTimer = null;
        }
    }

    // -------------------------------------------------------------
    // 12. Audio Alerts & Web Audio API Synth Chime
    // -------------------------------------------------------------
    function playMedicalChime() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            const ctx = new AudioContext();

            function playTone(freq, startTime, duration) {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, startTime);

                // Smooth cosine / linear ramp
                gain.gain.setValueAtTime(0, startTime);
                gain.gain.linearRampToValueAtTime(0.22, startTime + 0.03);
                gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(startTime);
                osc.stop(startTime + duration);
            }

            const now = ctx.currentTime;
            // Two-tone harmonic chime (A5 880Hz, then D6 1174.66Hz)
            playTone(880, now, 0.18);
            playTone(1174.66, now + 0.20, 0.45);
        } catch (e) {
            console.warn('Audio chime error:', e);
        }
    }

    function triggerReminderAlert(rem) {
        if (audioAlertEnabled) {
            playMedicalChime();
        }

        // Show Browser Notification
        if ('Notification' in window && Notification.permission === 'granted') {
            const title = `⏰ CareBridge AI — Medicine Due Now`;
            const body = `Time to take: ${rem.medName} (${rem.dose}). Prescribed timing: ${rem.prescribedTiming || rem.slotLabel}.`;
            new Notification(title, {
                body: body,
                icon: '/static/favicon.ico'
            });
        }
    }

    // Audio Toggle Button
    if (btnToggleAudio) {
        btnToggleAudio.addEventListener('click', () => {
            audioAlertEnabled = !audioAlertEnabled;
            localStorage.setItem('carebridge_audio_enabled', String(audioAlertEnabled));
            updateAudioButtonDisplay();
        });
    }

    function updateAudioButtonDisplay() {
        if (!btnToggleAudio) return;
        const icon = document.getElementById('audio-icon');
        const label = document.getElementById('audio-label');
        if (audioAlertEnabled) {
            if (icon) icon.textContent = '🔔';
            if (label) label.textContent = 'Sound Alert: ON';
            btnToggleAudio.classList.remove('btn-outline');
            btnToggleAudio.classList.add('btn-primary');
        } else {
            if (icon) icon.textContent = '🔕';
            if (label) label.textContent = 'Sound Alert: OFF';
            btnToggleAudio.classList.remove('btn-primary');
            btnToggleAudio.classList.add('btn-outline');
        }
    }
    updateAudioButtonDisplay();

    // Test Audio Chime
    if (btnTestChime) {
        btnTestChime.addEventListener('click', () => {
            playMedicalChime();
        });
    }

    // Browser Notification Permission Request
    if (btnToggleBrowserPerm) {
        btnToggleBrowserPerm.addEventListener('click', async () => {
            if (!('Notification' in window)) {
                alert('Browser notifications are not supported in this browser.');
                return;
            }

            const perm = await Notification.requestPermission();
            const label = document.getElementById('perm-label');
            if (perm === 'granted') {
                if (label) label.textContent = '🔔 Notifications: Active';
                btnToggleBrowserPerm.classList.add('btn-primary');
                btnToggleBrowserPerm.classList.remove('btn-outline');
                new Notification('CareBridge AI Reminders Active', {
                    body: 'Daily medication notifications are now active.',
                    icon: '/static/favicon.ico'
                });
            } else {
                alert('Notification permission was denied. You can re-enable notifications in your browser site settings.');
            }
        });
    }

    // -------------------------------------------------------------
    // 13. Reminder Edit & Set Modal
    // -------------------------------------------------------------
    function openReminderModal(rem) {
        if (!reminderModal) return;
        modalReminderId.value = rem.id;
        modalMedName.value = rem.medName;
        modalMedDoseFreq.value = `${rem.dose} | ${rem.frequency} (${rem.prescribedTiming || ''})`;
        modalReminderTime.value = rem.reminderTime || '08:00';
        modalReminderSlot.value = rem.slotLabel || 'Morning';

        if (rem.unspecified) {
            modalReminderAlert.classList.remove('hidden');
        } else {
            modalReminderAlert.classList.add('hidden');
        }

        reminderModal.classList.remove('hidden');
    }

    function closeReminderModal() {
        if (reminderModal) reminderModal.classList.add('hidden');
    }

    if (btnCloseReminderModal) btnCloseReminderModal.addEventListener('click', closeReminderModal);
    if (btnCancelReminderModal) btnCancelReminderModal.addEventListener('click', closeReminderModal);

    if (btnSaveReminderModal) {
        btnSaveReminderModal.addEventListener('click', () => {
            const id = modalReminderId.value;
            const newTime = modalReminderTime.value;
            const newSlot = modalReminderSlot.value;

            if (!newTime) {
                alert('Please select a reminder alert time.');
                return;
            }

            const rem = activeReminders.find(r => r.id === id);
            if (rem) {
                rem.reminderTime = newTime;
                rem.slotLabel = newSlot;
                rem.unspecified = false; // Confirmed by user
                rem.status = 'Upcoming';
                rem.snoozedUntil = null;
                saveRemindersToStorage();
                closeReminderModal();
                renderRemindersTable(currentLang === 'te');
            }
        });
    }

    if (btnAddCustomReminder) {
        btnAddCustomReminder.addEventListener('click', () => {
            if (!currentResult || !currentResult.medicines || currentResult.medicines.length === 0) {
                alert('Please process a discharge summary first to load medications.');
                return;
            }

            const meds = currentResult.medicines;
            const medNames = meds.map(m => m.name).join('\n');
            const chosenName = prompt(`Select medicine to add alarm for:\n\nAvailable:\n${medNames}\n\nEnter medicine name:`, meds[0].name);
            if (!chosenName) return;

            const targetMed = meds.find(m => m.name.toLowerCase().includes(chosenName.trim().toLowerCase())) || meds[0];

            const newRem = {
                id: `rem_${Date.now()}`,
                medName: targetMed.name,
                dose: targetMed.dose,
                frequency: targetMed.frequency,
                prescribedTiming: targetMed.timing,
                slotLabel: 'Custom Dose Time',
                reminderTime: '12:00',
                unspecified: false,
                status: 'Upcoming',
                paused: false,
                takenAt: null,
                snoozedUntil: null
            };

            activeReminders.push(newRem);
            saveRemindersToStorage();
            renderRemindersTable(currentLang === 'te');
            openReminderModal(newRem);
        });
    }

    if (btnResetReminders) {
        btnResetReminders.addEventListener('click', () => {
            if (!currentResult) return;
            if (confirm('Reset all medication reminders to default prescription schedule?')) {
                const storageKey = `carebridge_reminders_${currentResult.case_id || currentResult.summary_id || 'DEFAULT'}`;
                localStorage.removeItem(storageKey);
                initMedicationReminders(currentResult);
                renderRemindersTable(currentLang === 'te');
            }
        });
    }

    // -------------------------------------------------------------
    // 14. Direct PDF & Image (PNG) File Downloads (No Print Dialog)
    // -------------------------------------------------------------
    async function triggerDirectDownload(type) {
        if (!currentResult) {
            alert('Please load an approved care plan first.');
            return;
        }

        if (currentResult.doctor_review_status !== 'APPROVED') {
            alert('Export Restricted: Care plan must be clinically approved by an attending physician before PDF or PNG download.');
            return;
        }

        const caseId = currentResult.case_id;
        if (!caseId) {
            alert('No verified case reference found for this care plan.');
            return;
        }

        const ext = (type === 'pdf') ? 'pdf' : 'png';
        const cleanId = String(caseId).replace(/[^a-zA-Z0-9_\-]/g, '_');
        const filename = `CareBridge_Care_Plan_${cleanId}_${currentLang}.${ext}`;

        // Indicate progress on buttons
        const triggerBtns = (type === 'pdf')
            ? [btnQuickDownloadPdf, btnDownloadPdf]
            : [btnQuickDownloadImage, btnDownloadImage];

        triggerBtns.forEach(btn => {
            if (btn) {
                btn.disabled = true;
                btn.style.opacity = '0.7';
            }
        });

        try {
            const endpoint = `/api/export/${type}/${encodeURIComponent(caseId)}?lang=${encodeURIComponent(currentLang)}`;
            const resp = await fetch(endpoint, { method: 'GET' });

            if (!resp.ok) {
                const err = await resp.json();
                alert(`Export error (${resp.status}): ${err.error || 'Failed to generate file'}`);
                return;
            }

            const blob = await resp.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            }, 1000);

        } catch (err) {
            console.error(`Download error for ${type}:`, err);
            alert(`Download failed: ${err.message}`);
        } finally {
            triggerBtns.forEach(btn => {
                if (btn) {
                    btn.disabled = false;
                    btn.style.opacity = '1.0';
                }
            });
        }
    }

    if (btnQuickDownloadPdf) btnQuickDownloadPdf.addEventListener('click', () => triggerDirectDownload('pdf'));
    if (btnDownloadPdf) btnDownloadPdf.addEventListener('click', () => triggerDirectDownload('pdf'));
    if (btnQuickDownloadImage) btnQuickDownloadImage.addEventListener('click', () => triggerDirectDownload('image'));
    if (btnDownloadImage) btnDownloadImage.addEventListener('click', () => triggerDirectDownload('image'));

    // -------------------------------------------------------------
    // 15. Family Caregiver View
    // -------------------------------------------------------------
    function renderFamilyView(data, lang) {
        if (!familyContentDisplay || !data) return;
        familyContentDisplay.innerHTML = '';

        const isTe = (lang === 'te');
        const wrapper = document.createElement('div');
        wrapper.className = isTe ? 'telugu-text' : '';

        // Heading
        const headerDiv = document.createElement('div');
        headerDiv.innerHTML = `
            <h3 class="font-bold text-navy" style="font-size: 1.5rem; margin-bottom: 0.5rem;">
                ${isTe ? '👨‍👩‍👧 రోగి సంరక్షణ గైడ్ (Family Care Plan)' : '👨‍👩‍👧 Home Caregiver Quick Guide'}
            </h3>
            <p class="text-muted" style="margin-bottom: 1.5rem;">
                ${isTe ? 'కుటుంబ సభ్యులు సులభంగా అర్థం చేసుకునే ముఖ్యమైన మందుల వివరాలు:' : 'Key medicines and instructions for home care at a glance:'}
            </p>
        `;
        wrapper.appendChild(headerDiv);

        // Medicines Cards
        const meds = (isTe && data.telugu_structured && data.telugu_structured.medicines)
            ? data.telugu_structured.medicines
            : data.medicines;

        if (meds && meds.length > 0) {
            meds.forEach((m, idx) => {
                const medCard = document.createElement('div');
                medCard.className = 'family-med-item';
                medCard.innerHTML = `
                    <div class="family-med-title">${idx + 1}. ${escapeHtml(m.name)} — <span class="text-teal">${escapeHtml(m.dose)}</span></div>
                    <div style="font-size: 1.05rem; margin-top: 0.35rem;">
                        <strong>${isTe ? 'ఎప్పుడు వేసుకోవాలి' : 'When to take'}:</strong> ${escapeHtml(isTe ? (m.frequency_te || m.frequency) : m.frequency)}, ${escapeHtml(isTe ? (m.timing_te || m.timing) : m.timing)} (${escapeHtml(isTe ? (m.duration_te || m.duration) : m.duration)})
                    </div>
                    <div style="font-size: 0.95rem; color: #475569; margin-top: 0.2rem;">
                        <strong>${isTe ? 'సూచన' : 'How'}:</strong> ${escapeHtml(isTe ? (m.how_to_take_plain_te || m.how_to_take_plain) : m.how_to_take_plain)}
                    </div>
                `;
                wrapper.appendChild(medCard);
            });
        }

        // Stopped medicines if any
        const stops = (isTe && data.telugu_structured && data.telugu_structured.stop_medicines)
            ? data.telugu_structured.stop_medicines
            : data.stop_medicines;

        if (stops && stops.length > 0) {
            const stopDiv = document.createElement('div');
            stopDiv.style.marginTop = '1.5rem';
            stopDiv.innerHTML = `<h4 class="text-danger font-bold" style="font-size: 1.25rem;">🛑 ${isTe ? 'నిలిపివేయవలసిన మందులు (Do Not Give)' : 'Medicines to Stop (Do Not Give)'}:</h4>`;
            stops.forEach(sm => {
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
    // 16. Source Comparison & Traceability Inspector
    // -------------------------------------------------------------
    function renderComparisonInspector(data) {
        const sourceBox = document.getElementById('comparison-source-text');
        const factsBox = document.getElementById('comparison-facts-box');
        if (!sourceBox || !factsBox) return;

        sourceBox.textContent = data._raw_source_text || summaryInput.value;
        factsBox.innerHTML = '';

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
    // 17. Family Fridge Sheet (Bilingual / English / Telugu)
    // -------------------------------------------------------------
    function populateFridgeSheet(data, langMode) {
        const isTe = (langMode === 'te');
        const sheetMeds = document.getElementById('fridge-medicines-list');
        sheetMeds.innerHTML = '';

        const list = (isTe && data.telugu_structured && data.telugu_structured.medicines)
            ? data.telugu_structured.medicines
            : data.medicines;

        if (list && list.length > 0) {
            list.forEach(m => {
                const div = document.createElement('div');
                div.className = 'fridge-med-row';
                const freqStr = isTe ? (m.frequency_te || m.frequency) : m.frequency;
                const timeStr = isTe ? (m.timing_te || m.timing) : m.timing;
                const durStr = isTe ? (m.duration_te || m.duration) : m.duration;
                div.innerHTML = `
                    <div class="fridge-med-name">${escapeHtml(m.name)} <span>(${escapeHtml(m.dose)})</span></div>
                    <div class="fridge-med-how">${escapeHtml(freqStr)} — ${escapeHtml(timeStr)} (${escapeHtml(durStr)})</div>
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
            sheetFu.innerHTML = `<li class="text-muted">${isTe ? 'తేదీ పేర్కొనబడలేదు. వైద్యుడిని సంప్రదించండి.' : 'Not specified in discharge summary. Please verify with your healthcare provider.'}</li>`;
        }

        const sheetWarn = document.getElementById('fridge-warnings-list');
        sheetWarn.innerHTML = '';
        const warns = (isTe && data.telugu_structured && data.telugu_structured.warning_signs)
            ? data.telugu_structured.warning_signs
            : data.warning_signs;

        if (warns && warns.length > 0) {
            warns.slice(0, 4).forEach(w => {
                const li = document.createElement('li');
                li.textContent = w;
                sheetWarn.appendChild(li);
            });
        } else {
            sheetWarn.innerHTML = `<li class="text-muted">${isTe ? 'తీవ్ర లక్షణాలు వస్తే వెంటనే ఆసుపత్రికి వెళ్ళండి.' : 'Not specified in discharge summary. Please verify with your healthcare provider.'}</li>`;
        }

        const sheetDiet = document.getElementById('fridge-diet-list');
        if (sheetDiet) {
            sheetDiet.innerHTML = '';
            const diets = (isTe && data.telugu_structured && data.telugu_structured.diet)
                ? data.telugu_structured.diet
                : data.diet;
            if (diets && diets.length > 0) {
                diets.slice(0, 3).forEach(d => {
                    const li = document.createElement('li');
                    li.textContent = d;
                    sheetDiet.appendChild(li);
                });
            } else {
                sheetDiet.innerHTML = `<li class="text-muted">${isTe ? 'డాక్టర్ సూచించిన ఆహారం తీసుకోండి.' : 'Not specified in discharge summary. Please verify with your healthcare provider.'}</li>`;
            }
        }

        const sheetAct = document.getElementById('fridge-activity-list');
        if (sheetAct) {
            sheetAct.innerHTML = '';
            const acts = (isTe && data.telugu_structured && data.telugu_structured.activity)
                ? data.telugu_structured.activity
                : data.activity;
            if (acts && acts.length > 0) {
                acts.slice(0, 3).forEach(a => {
                    const li = document.createElement('li');
                    li.textContent = a;
                    sheetAct.appendChild(li);
                });
            } else {
                sheetAct.innerHTML = `<li class="text-muted">${isTe ? 'తగినంత విశ్రాంతి తీసుకోండి.' : 'Not specified in discharge summary. Please verify with your healthcare provider.'}</li>`;
            }
        }
    }

    if (fridgeLangSelect) {
        fridgeLangSelect.addEventListener('change', (e) => {
            if (currentResult) populateFridgeSheet(currentResult, e.target.value);
        });
    }

    // -------------------------------------------------------------
    // 18. Session History & Demo Helpers
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
                    initMedicationReminders(item.data);
                    renderFullCarePlan(item.data, currentLang);
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

    function format12Hour(time24) {
        if (!time24) return '';
        const parts = time24.split(':');
        let hours = parseInt(parts[0], 10);
        const minutes = parts[1];
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12;
        hours = hours ? hours : 12;
        return `${hours}:${minutes} ${ampm}`;
    }

    function formatSecondsToCountdown(totalSecs) {
        if (totalSecs <= 0) return '0s';
        const hours = Math.floor(totalSecs / 3600);
        const mins = Math.floor((totalSecs % 3600) / 60);
        const secs = totalSecs % 60;

        if (hours > 0) {
            return `${hours}h ${mins}m ${secs}s`;
        } else if (mins > 0) {
            return `${mins}m ${secs}s`;
        }
        return `${secs}s`;
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
