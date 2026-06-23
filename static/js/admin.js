document.addEventListener('DOMContentLoaded', () => {
    // ── Global State & Elements ──────────────────────────────────────────────
    let questionsList = [];
    let salesforceTemplates = [];
    
    // Tab switching
    const tabHeaders = document.querySelectorAll('.tab-header');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Form elements
    const questionForm = document.getElementById('question-form');
    const qTypeSelect = document.getElementById('q-type');
    const isMultiCorrectCheckbox = document.getElementById('q-is-multi-correct');
    const mcqMultiCorrectGroup = document.getElementById('mcq-multi-correct-group');
    const mcqOptionsContainer = document.getElementById('mcq-options-container');
    const mcqSingleCorrectSelect = document.getElementById('mcq-single-correct-select');
    const mcqMultiCorrectSelect = document.getElementById('mcq-multi-correct-select');
    const openQuestionContainer = document.getElementById('open-question-container');
    
    const editQidInput = document.getElementById('edit-qid');
    const editModeAlert = document.getElementById('edit-mode-alert');
    const formHeading = document.getElementById('form-heading');
    const formSubmitBtn = document.getElementById('form-submit-btn');
    const formCancelBtn = document.getElementById('form-cancel-btn');
    const qCurrentImagePreview = document.getElementById('q-current-image-preview');
    
    // Templates elements
    const toggleTemplates = document.getElementById('toggle-templates');
    const templatesListContainer = document.getElementById('templates-list-container');

    // ── Tab Switching Logic ──────────────────────────────────────────────────
    tabHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const targetTab = header.getAttribute('data-tab');
            
            tabHeaders.forEach(h => h.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            header.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
            
            // Trigger fetch functions depending on tab
            if (targetTab === 'tab-manage') {
                fetchQuestions();
            } else if (targetTab === 'tab-submissions') {
                fetchSubmissions();
            } else if (targetTab === 'tab-students') {
                fetchStudents();
            }
        });
    });

    // ── Contextual Help / Form Toggles ───────────────────────────────────────
    function updateFormFieldsVisibility() {
        const type = qTypeSelect.value;
        const tipBox = document.getElementById('q-type-tip');
        
        // Update tip text
        if (type === 'Math / Equations') {
            tipBox.style.display = 'block';
            tipBox.innerHTML = '<i class="fa-solid fa-circle-info"></i> 💡 <strong>LaTeX Math Tip:</strong> Wrap inline equations in single dollar signs (e.g. <code>$E=mc^2$</code>) and block equations in double dollar signs (e.g. <code>$$\\int x\\,dx$$</code>).';
        } else if (type === 'Code Problem') {
            tipBox.style.display = 'block';
            tipBox.innerHTML = '<i class="fa-solid fa-circle-info"></i> 💡 <strong>Code Block Tip:</strong> Write code using triple backticks: <pre style="margin: 0.5rem 0 0 0; padding:0.5rem;"><code>```python\ndef hello():\n    return "world"\n```</code></pre>';
        } else if (type === 'Multiple Choice') {
            tipBox.style.display = 'block';
            tipBox.innerHTML = '<i class="fa-solid fa-circle-info"></i> 💡 <strong>MCQ Tip:</strong> Complete the choices A, B, C, D and indicate which options are correct. MCQ items are automatically graded.';
        } else {
            tipBox.style.display = 'none';
        }

        // Show/hide containers
        if (type === 'Multiple Choice') {
            mcqMultiCorrectGroup.style.display = 'block';
            mcqOptionsContainer.style.display = 'block';
            openQuestionContainer.style.display = 'none';
            
            // Toggle between single and multi MCQ
            if (isMultiCorrectCheckbox.checked) {
                mcqSingleCorrectSelect.style.display = 'none';
                mcqMultiCorrectSelect.style.display = 'block';
            } else {
                mcqSingleCorrectSelect.style.display = 'block';
                mcqMultiCorrectSelect.style.display = 'none';
            }
        } else {
            mcqMultiCorrectGroup.style.display = 'none';
            mcqOptionsContainer.style.display = 'none';
            openQuestionContainer.style.display = 'block';
        }
    }

    qTypeSelect.addEventListener('change', updateFormFieldsVisibility);
    isMultiCorrectCheckbox.addEventListener('change', updateFormFieldsVisibility);
    updateFormFieldsVisibility(); // run once on load

    // Toggle template list drawer
    toggleTemplates.addEventListener('click', () => {
        const icon = toggleTemplates.querySelector('i.fa-chevron-down, i.fa-chevron-up');
        if (templatesListContainer.style.display === 'none') {
            templatesListContainer.style.display = 'flex';
            templatesListContainer.style.flexDirection = 'column';
            icon.className = 'fa-solid fa-chevron-up';
            if (salesforceTemplates.length === 0) {
                fetchTemplates();
            }
        } else {
            templatesListContainer.style.display = 'none';
            icon.className = 'fa-solid fa-chevron-down';
        }
    });

    // ── Fetch Salesforce Templates ───────────────────────────────────────────
    function fetchTemplates() {
        templatesListContainer.innerHTML = '<div style="text-align:center; padding:1rem;"><i class="fa-solid fa-circle-notch fa-spin"></i> Loading templates...</div>';
        
        fetch('/api/salesforce_templates')
            .then(res => res.json())
            .then(data => {
                salesforceTemplates = data;
                renderTemplates();
            })
            .catch(err => {
                console.error("Error fetching templates", err);
                templatesListContainer.innerHTML = '<div class="alert alert-danger"><i class="fa-solid fa-triangle-exclamation"></i> Error loading templates.</div>';
            });
    }

    function renderTemplates() {
        if (!salesforceTemplates || salesforceTemplates.length === 0) {
            templatesListContainer.innerHTML = '<div style="padding:1rem;">No templates available.</div>';
            return;
        }

        templatesListContainer.innerHTML = '';
        salesforceTemplates.forEach((tpl, idx) => {
            const item = document.createElement('div');
            item.className = 'template-item';
            
            let optionsHtml = '';
            if (tpl.options) {
                optionsHtml = '<div style="margin:0.25rem 0; font-size:0.8rem; color:var(--text-dim);">';
                Object.keys(tpl.options).forEach(k => {
                    optionsHtml += `<strong>${k}:</strong> ${tpl.options[k]} `;
                });
                optionsHtml += '</div>';
            }

            item.innerHTML = `
                <div class="template-item-info">
                    <span class="template-item-title">${tpl.title}</span>
                    <span class="template-item-meta">
                        Type: <strong>${tpl.type}</strong> | Difficulty: <strong>${tpl.difficulty}</strong> | Marks: <strong>${tpl.marks}</strong>
                    </span>
                    ${optionsHtml}
                </div>
                <button type="button" class="btn btn-secondary btn-sm" data-idx="${idx}" style="padding:0.4rem 0.8rem; font-size:0.8rem;">
                    <i class="fa-solid fa-copy"></i> Load
                </button>
            `;
            
            // Set event listener on Load button
            item.querySelector('button').addEventListener('click', (e) => {
                const index = e.currentTarget.getAttribute('data-idx');
                loadTemplateIntoForm(salesforceTemplates[index]);
            });
            
            templatesListContainer.appendChild(item);
        });
    }

    function loadTemplateIntoForm(tpl) {
        clearQuestionForm();
        
        qTypeSelect.value = tpl.type;
        document.getElementById('q-title').value = tpl.title;
        document.getElementById('q-text').value = tpl.text;
        document.getElementById('q-marks').value = tpl.marks;
        document.getElementById('q-difficulty').value = tpl.difficulty;
        document.getElementById('q-explanation').value = tpl.explanation || '';
        
        if (tpl.type === 'Multiple Choice') {
            isMultiCorrectCheckbox.checked = !!tpl.is_multi_correct;
            
            if (tpl.options) {
                document.getElementById('q-opt-a').value = tpl.options.A || '';
                document.getElementById('q-opt-b').value = tpl.options.B || '';
                document.getElementById('q-opt-c').value = tpl.options.C || '';
                document.getElementById('q-opt-d').value = tpl.options.D || '';
            }
            
            // Handle correct choice(s)
            if (tpl.is_multi_correct) {
                const correctList = Array.isArray(tpl.correct_option) ? tpl.correct_option : [tpl.correct_option];
                document.querySelectorAll('.mcq-correct-cb').forEach(cb => {
                    cb.checked = correctList.includes(cb.value);
                });
            } else {
                const singleCorrect = Array.isArray(tpl.correct_option) ? tpl.correct_option[0] : tpl.correct_option;
                document.getElementById('q-correct-single').value = singleCorrect || 'A';
            }
        } else {
            document.getElementById('q-ideal-answer').value = tpl.ideal_answer || '';
            
            const formats = tpl.allowed_formats || ['Text'];
            document.getElementById('q-allow-format-text').checked = formats.includes('Text');
            document.getElementById('q-allow-format-image').checked = formats.includes('Image');
            document.getElementById('q-allow-format-audio').checked = formats.includes('Audio');
        }
        
        updateFormFieldsVisibility();
        // Scroll to form top
        questionForm.scrollIntoView({ behavior: 'smooth' });
    }

    // ── Fetch Operations (Metrics, Questions, Submissions, Students) ─────────
    function fetchMetrics() {
        fetch('/api/admin/metrics')
            .then(res => res.json())
            .then(data => {
                document.getElementById('metric-questions').innerText = data.questions || 0;
                document.getElementById('metric-submissions').innerText = data.submissions || 0;
                document.getElementById('metric-students').innerText = data.students || 0;
            })
            .catch(err => console.error("Error fetching stats metrics", err));
    }
    fetchMetrics(); // Fetch immediately on load

    function fetchQuestions() {
        const spinner = document.getElementById('questions-loading-spinner');
        const listDiv = document.getElementById('questions-list');
        const alertBox = document.getElementById('no-questions-alert');
        
        spinner.style.display = 'flex';
        listDiv.style.display = 'none';
        alertBox.style.display = 'none';

        fetch('/api/admin/questions')
            .then(res => res.json())
            .then(data => {
                spinner.style.display = 'none';
                questionsList = data;
                
                if (!data || data.length === 0) {
                    alertBox.style.display = 'block';
                } else {
                    listDiv.style.display = 'flex';
                    renderQuestionsList(data, listDiv);
                }
            })
            .catch(err => {
                console.error("Error loading questions list", err);
                spinner.style.display = 'none';
                alertBox.style.display = 'block';
                alertBox.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error loading questions.';
            });
    }

    function renderQuestionsList(questions, container) {
        container.innerHTML = '';
        questions.forEach((q) => {
            const card = document.createElement('div');
            card.className = 'expander';
            card.id = `q-card-${q.id}`;
            
            const badgeClass = `badge-${q.difficulty.toLowerCase()}`;
            
            // Check if MCQ or Open
            let answerDetails = '';
            if (q.type === 'Multiple Choice') {
                const correctList = Array.isArray(q.correct_option) ? q.correct_option : [q.correct_option];
                answerDetails = '<div class="options-list">';
                Object.keys(q.options).forEach(k => {
                    const isCorrect = correctList.includes(k);
                    const isCorrectClass = isCorrect ? 'correct' : '';
                    const marker = isCorrect ? '<span class="correct-marker">✅ Option ' + k + ':</span>' : '<strong>Option ' + k + ':</strong>';
                    answerDetails += `
                        <div class="option-item ${isCorrectClass}">
                            ${marker} ${q.options[k]}
                        </div>
                    `;
                });
                answerDetails += '</div>';
            } else {
                if (q.ideal_answer) {
                    answerDetails += `
                        <div style="margin-top:1rem; padding: 0.75rem; background:rgba(0,0,0,0.2); border-radius:8px; font-size:0.9rem;">
                            <strong>Ideal Answer / Rubric:</strong><br>
                            ${q.ideal_answer}
                        </div>
                    `;
                }
                const formats = q.allowed_formats || [];
                answerDetails += `
                    <div style="margin-top:0.75rem; font-size:0.85rem; color:var(--text-muted);">
                        <strong>Accepted answer formats:</strong> ${formats.join(', ')}
                    </div>
                `;
            }

            let imageHtml = '';
            if (q.has_image) {
                // Fetch image via direct image view API route
                imageHtml = `<div style="margin-top:1rem;"><img src="/api/question/image/${q.id}" class="question-image-attachment" alt="Question Diagram"></div>`;
            }

            card.innerHTML = `
                <div class="expander-header">
                    <div class="expander-title-group">
                        <span class="badge ${badgeClass}">${q.difficulty}</span>
                        <span class="expander-title">${q.title}</span>
                        <span style="font-size:0.8rem; color:var(--text-dim); margin-left:0.5rem;">(${q.marks} marks)</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:1rem;">
                        <span style="font-size:0.8rem; color:var(--text-dim);">${q.type}</span>
                        <i class="fa-solid fa-chevron-down chevron"></i>
                    </div>
                </div>
                <div class="expander-content">
                    <p style="color:#ffffff; font-weight:500; font-size:1rem; margin-bottom:0.75rem;">${q.text}</p>
                    ${imageHtml}
                    ${answerDetails}
                    ${q.explanation ? `<p style="margin-top:1rem; font-size:0.88rem; color:var(--text-muted);">📘 <strong>Explanation:</strong> ${q.explanation}</p>` : ''}
                    
                    <div style="display:flex; justify-content:flex-end; gap:0.75rem; border-top:1px solid rgba(255,255,255,0.05); padding-top:1rem; margin-top:1rem;">
                        <button type="button" class="btn btn-secondary btn-sm" id="btn-edit-${q.id}">
                            <i class="fa-solid fa-pen-to-square"></i> Edit
                        </button>
                        <button type="button" class="btn btn-danger btn-sm" id="btn-delete-${q.id}">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            `;

            // Expand / Collapse toggler
            const header = card.querySelector('.expander-header');
            header.addEventListener('click', () => {
                card.classList.toggle('open');
            });

            // Action Buttons Event Listeners
            card.querySelector(`#btn-edit-${q.id}`).addEventListener('click', (e) => {
                e.stopPropagation();
                enterEditMode(q);
            });
            card.querySelector(`#btn-delete-${q.id}`).addEventListener('click', (e) => {
                e.stopPropagation();
                deleteQuestion(q.id);
            });

            container.appendChild(card);
        });
    }

    function fetchSubmissions() {
        const spinner = document.getElementById('submissions-loading-spinner');
        const listDiv = document.getElementById('submissions-list');
        const alertBox = document.getElementById('no-submissions-alert');
        
        spinner.style.display = 'flex';
        listDiv.style.display = 'none';
        alertBox.style.display = 'none';

        fetch('/api/admin/submissions')
            .then(res => res.json())
            .then(data => {
                spinner.style.display = 'none';
                
                if (!data || data.length === 0) {
                    alertBox.style.display = 'block';
                } else {
                    listDiv.style.display = 'flex';
                    renderSubmissionsList(data, listDiv);
                }
            })
            .catch(err => {
                console.error("Error fetching submissions list", err);
                spinner.style.display = 'none';
                alertBox.style.display = 'block';
                alertBox.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error loading submissions.';
            });
    }

    function renderSubmissionsList(submissions, container) {
        container.innerHTML = '';
        submissions.forEach(sub => {
            const card = document.createElement('div');
            card.className = 'expander';
            card.id = `sub-card-${sub.id}`;
            
            // Format time
            const date = new Date(sub.submitted_at);
            const dateStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            let answerBodyHtml = '';
            if (sub.answer_type === 'Text') {
                answerBodyHtml = `
                    <div style="padding: 1rem; background:rgba(0,0,0,0.3); border-radius:8px; border:1px solid var(--glass-border); margin-top:0.75rem;">
                        <strong>Submitted Answer:</strong><br>
                        <p style="color:#ffffff; margin-top:0.5rem; white-space:pre-wrap;">${sub.answer_text || ''}</p>
                    </div>
                `;
            } else if (sub.answer_type === 'Image') {
                answerBodyHtml = `
                    <div style="margin-top:0.75rem;">
                        <strong>Submitted Webcam / Photo:</strong><br>
                        <img src="/api/submission/image/${sub.id}" style="max-width:100%; max-height:400px; border-radius:8px; margin-top:0.5rem; border:1px solid var(--glass-border);" alt="Student Image Submission">
                    </div>
                `;
            } else if (sub.answer_type === 'Audio') {
                answerBodyHtml = `
                    <div style="margin-top:0.75rem;">
                        <strong>Submitted Voice Note:</strong><br>
                        <audio src="/api/submission/audio/${sub.id}" controls style="width:100%; max-width:400px; margin-top:0.5rem;"></audio>
                    </div>
                `;
            }

            // Parse Gemini Markdown report
            const parsedEvaluationHtml = marked.parse(sub.evaluation || '_No evaluation details found._');

            card.innerHTML = `
                <div class="expander-header">
                    <div class="expander-title-group">
                        <span class="badge" style="background:rgba(99, 102, 241, 0.2); color:#a5b4fc; border:1px solid rgba(99,102,241,0.3);">${sub.student_username}</span>
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
                        <strong>Question text:</strong><br>
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

    function fetchStudents() {
        const spinner = document.getElementById('students-loading-spinner');
        const tableCard = document.getElementById('students-table-card');
        const alertBox = document.getElementById('no-students-alert');
        const tbody = document.getElementById('students-table-body');
        
        spinner.style.display = 'flex';
        tableCard.style.display = 'none';
        alertBox.style.display = 'none';

        fetch('/api/admin/students')
            .then(res => res.json())
            .then(data => {
                spinner.style.display = 'none';
                
                if (!data || data.length === 0) {
                    alertBox.style.display = 'block';
                } else {
                    tableCard.style.display = 'block';
                    tbody.innerHTML = '';
                    
                    data.forEach(s => {
                        const date = new Date(s.created_at);
                        const dateStr = date.toLocaleDateString();
                        
                        const row = document.createElement('tr');
                        row.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                        row.innerHTML = `
                            <td style="padding:1rem; font-weight:600; color:#ffffff;">${s.name}</td>
                            <td style="padding:1rem; color:var(--text-muted);"><code>${s.username}</code></td>
                            <td style="padding:1rem; color:var(--text-dim);">${dateStr}</td>
                        `;
                        tbody.appendChild(row);
                    });
                }
            })
            .catch(err => {
                console.error("Error fetching students directory", err);
                spinner.style.display = 'none';
                alertBox.style.display = 'block';
                alertBox.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error loading student list.';
            });
    }

    // ── Create Student Action ────────────────────────────────────────────────
    const createStudentForm = document.getElementById('create-student-form');
    createStudentForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const formData = new FormData(createStudentForm);
        const payload = Object.fromEntries(formData);
        
        fetch('/api/admin/create_student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                alert(`Student account successfully created!`);
                createStudentForm.reset();
                fetchStudents();
                fetchMetrics();
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(err => {
            console.error("Error creating student", err);
            alert("Network error creating student account.");
        });
    });

    // ── Edit Mode Logic ──────────────────────────────────────────────────────
    function enterEditMode(q) {
        clearQuestionForm();
        
        editQidInput.value = q.id;
        editModeAlert.style.display = 'block';
        formHeading.innerText = 'Edit Question';
        formSubmitBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Changes';
        formCancelBtn.style.display = 'inline-flex';
        
        // Populate inputs
        qTypeSelect.value = q.type;
        document.getElementById('q-title').value = q.title;
        document.getElementById('q-text').value = q.text;
        document.getElementById('q-marks').value = q.marks;
        document.getElementById('q-difficulty').value = q.difficulty;
        document.getElementById('q-explanation').value = q.explanation || '';
        
        if (q.has_image) {
            qCurrentImagePreview.style.display = 'block';
        } else {
            qCurrentImagePreview.style.display = 'none';
        }

        if (q.type === 'Multiple Choice') {
            isMultiCorrectCheckbox.checked = !!q.is_multi_correct;
            
            if (q.options) {
                document.getElementById('q-opt-a').value = q.options.A || '';
                document.getElementById('q-opt-b').value = q.options.B || '';
                document.getElementById('q-opt-c').value = q.options.C || '';
                document.getElementById('q-opt-d').value = q.options.D || '';
            }
            
            // Handle correct choice(s)
            if (q.is_multi_correct) {
                const correctList = Array.isArray(q.correct_option) ? q.correct_option : [q.correct_option];
                document.querySelectorAll('.mcq-correct-cb').forEach(cb => {
                    cb.checked = correctList.includes(cb.value);
                });
            } else {
                const singleCorrect = Array.isArray(q.correct_option) ? q.correct_option[0] : q.correct_option;
                document.getElementById('q-correct-single').value = singleCorrect || 'A';
            }
        } else {
            document.getElementById('q-ideal-answer').value = q.ideal_answer || '';
            
            const formats = q.allowed_formats || ['Text'];
            document.getElementById('q-allow-format-text').checked = formats.includes('Text');
            document.getElementById('q-allow-format-image').checked = formats.includes('Image');
            document.getElementById('q-allow-format-audio').checked = formats.includes('Audio');
        }
        
        updateFormFieldsVisibility();
        
        // Switch tab to upload
        tabHeaders[0].click(); // clicks "Upload Question" tab header
        
        // Scroll to form top
        questionForm.scrollIntoView({ behavior: 'smooth' });
    }

    function exitEditMode() {
        clearQuestionForm();
        editQidInput.value = '';
        editModeAlert.style.display = 'none';
        formHeading.innerText = 'Upload a New Question';
        formSubmitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Upload Question';
        formCancelBtn.style.display = 'none';
        qCurrentImagePreview.style.display = 'none';
        
        // Switch tab back to manage
        document.getElementById('tab-header-manage').click();
    }

    formCancelBtn.addEventListener('click', exitEditMode);

    function clearQuestionForm() {
        questionForm.reset();
        editQidInput.value = '';
        qCurrentImagePreview.style.display = 'none';
        document.querySelectorAll('.mcq-correct-cb').forEach(cb => cb.checked = false);
        // Defaults
        document.getElementById('q-allow-format-text').checked = true;
        document.getElementById('q-allow-format-image').checked = true;
        document.getElementById('q-allow-format-audio').checked = true;
        updateFormFieldsVisibility();
    }

    // ── Delete Question Action ───────────────────────────────────────────────
    function deleteQuestion(qid) {
        if (!confirm("Are you sure you want to permanently delete this question?")) {
            return;
        }

        fetch(`/api/admin/question/delete/${qid}`, {
            method: 'POST'
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                alert("Question deleted successfully!");
                fetchQuestions();
                fetchMetrics();
            } else {
                alert(`Error: ${data.message}`);
            }
        })
        .catch(err => {
            console.error("Error deleting question", err);
            alert("Network error deleting question.");
        });
    }

    // ── Form Submit: Create/Edit Question ────────────────────────────────────
    questionForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const qid = editQidInput.value;
        const isEditing = !!qid;
        
        const formData = new FormData(questionForm);
        
        // Append MCQ correct answers based on single vs multi
        if (qTypeSelect.value === 'Multiple Choice') {
            if (isMultiCorrectCheckbox.checked) {
                const correctList = [];
                document.querySelectorAll('.mcq-correct-cb:checked').forEach(cb => {
                    correctList.push(cb.value);
                });
                
                if (correctList.length === 0) {
                    alert("Please select at least one correct MCQ option.");
                    return;
                }
                
                // Append correct options as JSON string or multi elements
                formData.append('correct_option', JSON.stringify(correctList));
            } else {
                const singleCorrect = document.getElementById('q-correct-single').value;
                formData.append('correct_option', JSON.stringify([singleCorrect]));
            }
        } else {
            // Append accepted formats list
            const formatsList = [];
            if (document.getElementById('q-allow-format-text').checked) formatsList.push('Text');
            if (document.getElementById('q-allow-format-image').checked) formatsList.push('Image');
            if (document.getElementById('q-allow-format-audio').checked) formatsList.push('Audio');
            
            if (formatsList.length === 0) {
                alert("Please select at least one accepted student answer format.");
                return;
            }
            formData.append('allowed_formats', JSON.stringify(formatsList));
        }

        const url = isEditing ? `/api/admin/question/edit/${qid}` : '/api/admin/question/add';
        
        formSubmitBtn.disabled = true;
        formSubmitBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...';

        fetch(url, {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            formSubmitBtn.disabled = false;
            if (data.status === 'ok') {
                alert(isEditing ? "Question updated successfully!" : "Question created successfully!");
                clearQuestionForm();
                if (isEditing) {
                    exitEditMode();
                } else {
                    document.getElementById('tab-header-manage').click();
                }
                fetchMetrics();
            } else {
                alert(`Error saving question: ${data.message}`);
                formSubmitBtn.innerHTML = isEditing ? '<i class="fa-solid fa-floppy-disk"></i> Save Changes' : '<i class="fa-solid fa-paper-plane"></i> Upload Question';
            }
        })
        .catch(err => {
            console.error("Error saving question", err);
            formSubmitBtn.disabled = false;
            formSubmitBtn.innerHTML = isEditing ? '<i class="fa-solid fa-floppy-disk"></i> Save Changes' : '<i class="fa-solid fa-paper-plane"></i> Upload Question';
            alert("Network error saving question.");
        });
    });
});
