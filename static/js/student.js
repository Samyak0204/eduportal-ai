document.addEventListener('DOMContentLoaded', () => {
    // ── Elements & State ─────────────────────────────────────────────────────
    const studentLobby = document.getElementById('student-lobby');
    const studentExam = document.getElementById('student-exam');
    const examHwCheck = document.getElementById('exam-hw-check');
    const examQuestionsSheet = document.getElementById('exam-questions-sheet');
    const studentSummaryReport = document.getElementById('student-summary-report');
    
    const startExamForm = document.getElementById('start-exam-form');
    const lobbyQuestionsInfo = document.getElementById('lobby-questions-info');
    
    // Tab switching for lobby
    const tabHeaders = document.querySelectorAll('#student-lobby .tab-header');
    const tabContents = document.querySelectorAll('#student-lobby .tab-content');
    
    // Hardware Check Elements
    const btnHwCancel = document.getElementById('btn-hw-cancel');
    const btnHwProceed = document.getElementById('btn-hw-proceed');
    const registeredCandidateLabel = document.getElementById('registered-candidate-label');
    
    // Summary report elements
    const btnCloseSummary = document.getElementById('btn-close-summary');

    let examQuestions = [];
    let currentCandidate = null;

    // ── Tab Switching (Lobby) ────────────────────────────────────────────────
    tabHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const targetTab = header.getAttribute('data-tab');
            
            tabHeaders.forEach(h => h.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            header.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
            
            if (targetTab === 'lobby-results') {
                fetchResults();
            }
        });
    });

    // ── Load Assessment Details (Lobby) ──────────────────────────────────────
    function loadLobbyDetails() {
        if (!studentLobby || studentLobby.style.display === 'none') return;
        
        fetch('/api/student/questions')
            .then(res => res.json())
            .then(data => {
                examQuestions = data;
                lobbyQuestionsInfo.innerHTML = `
                    <div class="alert alert-info" style="margin: 0.5rem 0 0 0;">
                        <i class="fa-solid fa-circle-question"></i>
                        <span>This assessment contains <strong>${data.length} questions</strong>. Prepare your webcam and microphone.</span>
                    </div>
                `;
            })
            .catch(err => {
                console.error("Error fetching lobby questions", err);
                lobbyQuestionsInfo.innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fa-solid fa-triangle-exclamation"></i> Error loading assessment details.
                    </div>
                `;
            });
    }
    loadLobbyDetails();

    // ── Start Exam Registration Form ──────────────────────────────────────────
    if (startExamForm) {
        startExamForm.addEventListener('submit', (e) => {
            e.preventDefault();
            
            const studentId = document.getElementById('c-student-id').value.trim();
            const email = document.getElementById('c-email').value.trim();
            const name = document.getElementById('c-name').value.trim();
            
            if (!studentId || !email || !name) {
                alert("Please complete all candidate details.");
                return;
            }

            const payload = {
                student_id: studentId,
                student_email: email,
                student_name: name
            };

            const startBtn = document.getElementById('start-exam-btn');
            startBtn.disabled = true;
            startBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Initializing Exam Session...';

            fetch('/api/student/start_exam', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                startBtn.disabled = false;
                startBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start Assessment';
                
                if (data.status === 'ok') {
                    // Update layout session and enter exam
                    enterExamFlow(data.candidate);
                } else {
                    alert(`Error starting exam: ${data.message}`);
                }
            })
            .catch(err => {
                console.error("Error starting exam session", err);
                startBtn.disabled = false;
                startBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start Assessment';
                alert("Network error starting exam session.");
            });
        });
    }

    // ── Check session state on load ──────────────────────────────────────────
    function checkActiveExamSession() {
        fetch('/api/student/get_state')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'ok' && data.state && data.state.test_active) {
                    currentCandidate = data.state.student_details;
                    enterExamFlow(currentCandidate, data.state);
                }
            })
            .catch(err => console.error("Error checking active session", err));
    }
    checkActiveExamSession();

    // ── Enter Exam Flow ──────────────────────────────────────────────────────
    function enterExamFlow(candidate, savedState = null) {
        currentCandidate = candidate;
        
        // Hide standard layout sidebar by updating body class (handled by base.html / style.css)
        document.body.classList.add('exam-mode');
        
        studentLobby.style.display = 'none';
        studentExam.style.display = 'block';
        studentSummaryReport.style.display = 'none';

        registeredCandidateLabel.innerHTML = `Candidate: <strong>${candidate.name}</strong> (ID: <code>${candidate.id}</code>) | Email: <code>${candidate.email}</code>`;

        const isHwVerified = savedState ? !!savedState.hardware_verified : false;
        
        if (!isHwVerified) {
            examHwCheck.style.display = 'block';
            examQuestionsSheet.style.display = 'none';
            
            // Initialize hardware stream checks
            if (window.ExamHardwareController) {
                window.ExamHardwareController.startWebcam(document.getElementById('webcam-test-video'));
                window.ExamHardwareController.bindCheckTriggers(onHwCheckedStatus);
            }
        } else {
            examHwCheck.style.display = 'none';
            examQuestionsSheet.style.display = 'block';
            
            // Initialize exam sheets
            if (window.ExamQuestionsController) {
                window.ExamQuestionsController.startExamSession(candidate, savedState);
            }
        }
    }

    // Callback on HW Check Status
    function onHwCheckedStatus(webcamOk, micOk) {
        if (webcamOk && micOk) {
            btnHwProceed.removeAttribute('disabled');
            btnHwProceed.classList.remove('btn-secondary');
            btnHwProceed.classList.add('btn-primary');
        } else {
            btnHwProceed.setAttribute('disabled', 'true');
            btnHwProceed.classList.remove('btn-primary');
            btnHwProceed.classList.add('btn-secondary');
        }
    }

    // Proceed to exam from HW Check
    btnHwProceed.addEventListener('click', () => {
        // Stop hardware check media streams
        if (window.ExamHardwareController) {
            window.ExamHardwareController.stopWebcam();
        }
        
        examHwCheck.style.display = 'none';
        examQuestionsSheet.style.display = 'block';

        // Notify backend of hardware check verification & start questions
        fetch('/api/student/save_state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hardware_verified: true })
        })
        .then(() => {
            if (window.ExamQuestionsController) {
                window.ExamQuestionsController.startExamSession(currentCandidate, { hardware_verified: true });
            }
        });
    });

    // Cancel HW check and return to lobby
    btnHwCancel.addEventListener('click', () => {
        if (confirm("Cancel check and return to dashboard? Any temporary progress will be lost.")) {
            if (window.ExamHardwareController) {
                window.ExamHardwareController.stopWebcam();
            }
            
            fetch('/api/student/cancel_exam', { method: 'POST' })
                .then(() => {
                    document.body.classList.remove('exam-mode');
                    studentLobby.style.display = 'block';
                    studentExam.style.display = 'none';
                    loadLobbyDetails();
                });
        }
    });

    // ── Fetch Results History ────────────────────────────────────────────────
    function fetchResults() {
        const spinner = document.getElementById('results-loading-spinner');
        const listDiv = document.getElementById('results-list');
        const alertBox = document.getElementById('no-results-alert');
        
        spinner.style.display = 'flex';
        listDiv.style.display = 'none';
        alertBox.style.display = 'none';

        fetch('/api/student/submissions')
            .then(res => res.json())
            .then(data => {
                spinner.style.display = 'none';
                
                if (!data || data.length === 0) {
                    alertBox.style.display = 'block';
                } else {
                    listDiv.style.display = 'flex';
                    renderResultsList(data, listDiv);
                }
            })
            .catch(err => {
                console.error("Error loading student submissions history", err);
                spinner.style.display = 'none';
                alertBox.style.display = 'block';
                alertBox.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error loading submission history.';
            });
    }

    function renderResultsList(results, container) {
        container.innerHTML = '';
        results.forEach(sub => {
            const card = document.createElement('div');
            card.className = 'expander';
            card.id = `res-card-${sub.id}`;
            
            const date = new Date(sub.submitted_at);
            const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            let answerBodyHtml = '';
            if (sub.answer_type === 'Text') {
                answerBodyHtml = `
                    <div style="padding: 1rem; background:rgba(0,0,0,0.3); border-radius:8px; border:1px solid var(--glass-border); margin-top:0.75rem;">
                        <strong>Your Submitted Answer:</strong><br>
                        <p style="color:#ffffff; margin-top:0.5rem; white-space:pre-wrap;">${sub.answer_text || ''}</p>
                    </div>
                `;
            } else if (sub.answer_type === 'Image') {
                answerBodyHtml = `
                    <div style="margin-top:0.75rem;">
                        <strong>Your Submitted Image:</strong><br>
                        <img src="/api/submission/image/${sub.id}" style="max-width:100%; max-height:350px; border-radius:8px; margin-top:0.5rem; border:1px solid var(--glass-border);" alt="Student Image Submission">
                    </div>
                `;
            } else if (sub.answer_type === 'Audio') {
                answerBodyHtml = `
                    <div style="margin-top:0.75rem;">
                        <strong>Your Submitted Audio:</strong><br>
                        <audio src="/api/submission/audio/${sub.id}" controls style="width:100%; max-width:400px; margin-top:0.5rem;"></audio>
                    </div>
                `;
            }

            const parsedEvaluationHtml = marked.parse(sub.evaluation || '_Evaluation pending._');

            card.innerHTML = `
                <div class="expander-header">
                    <div class="expander-title-group">
                        <span class="expander-title">${sub.question_title || 'Question'}</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:1.5rem;">
                        <span style="font-size:0.8rem; color:var(--text-dim);">${dateStr}</span>
                        <span class="badge" style="background:rgba(255,255,255,0.05); color:#ffffff; font-size:0.7rem;">${sub.answer_type}</span>
                        <i class="fa-solid fa-chevron-down chevron"></i>
                    </div>
                </div>
                <div class="expander-content">
                    <div style="font-size:0.9rem; color:var(--text-muted); margin-bottom:0.75rem;">
                        <strong>Question:</strong><br>
                        <p style="margin-top:0.25rem;">${sub.question_text || ''}</p>
                    </div>
                    
                    ${answerBodyHtml}
                    
                    <div class="gemini-report">
                        <h3 style="font-size:1.15rem; color:var(--secondary); margin-bottom:0.75rem; border-bottom:1px solid rgba(168,85,247,0.1); padding-bottom:0.5rem;">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> AI Assessment Report
                        </h3>
                        <div>${parsedEvaluationHtml}</div>
                    </div>
                </div>
            `;

            // Expand / Collapse toggler
            const header = card.querySelector('.expander-header');
            header.addEventListener('click', () => {
                card.classList.toggle('open');
            });

            container.appendChild(card);
        });
    }

    // ── Close Graded Summary Report ──────────────────────────────────────────
    btnCloseSummary.addEventListener('click', () => {
        document.body.classList.remove('exam-mode');
        studentLobby.style.display = 'block';
        studentExam.style.display = 'none';
        studentSummaryReport.style.display = 'none';
        
        // Reset tabs and fetch new results
        tabHeaders[1].click(); // clicks Results tab
        loadLobbyDetails();
    });
});
