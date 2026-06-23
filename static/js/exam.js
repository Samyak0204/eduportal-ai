// ── Exam Media & Questions Controller Library ────────────────────────────

(function() {
    // ── Hardware check controller ──────────────────────────────────────────
    const ExamHardwareController = {
        webcamStream: null,
        mediaRecorder: null,
        audioChunks: [],
        audioBlob: null,
        
        webcamChecked: false,
        micChecked: false,
        statusCallback: null,

        startWebcam: function(videoElement) {
            if (this.webcamStream) {
                this.stopWebcam();
            }
            navigator.mediaDevices.getUserMedia({ video: true, audio: false })
                .then(stream => {
                    this.webcamStream = stream;
                    videoElement.srcObject = stream;
                    videoElement.style.display = 'block';
                    document.getElementById('webcam-test-preview').style.display = 'none';
                })
                .catch(err => {
                    console.error("Error accessing webcam", err);
                    document.getElementById('webcam-test-status').className = 'alert alert-danger';
                    document.getElementById('webcam-test-status').innerText = 'Webcam: Error accessing camera (' + err.message + ')';
                });
        },

        stopWebcam: function() {
            if (this.webcamStream) {
                this.webcamStream.getTracks().forEach(track => track.stop());
                this.webcamStream = null;
            }
        },

        bindCheckTriggers: function(statusCallback) {
            this.statusCallback = statusCallback;
            this.webcamChecked = false;
            this.micChecked = false;
            
            // Webcam Snapshot Button
            const btnCap = document.getElementById('btn-capture-webcam-test');
            btnCap.onclick = () => {
                const video = document.getElementById('webcam-test-video');
                const previewContainer = document.getElementById('webcam-test-preview');
                const previewImg = document.getElementById('webcam-test-img');
                const statusBox = document.getElementById('webcam-test-status');

                if (this.webcamStream) {
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth || 640;
                    canvas.height = video.videoHeight || 480;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    const dataUrl = canvas.toDataURL('image/png');
                    previewImg.src = dataUrl;
                    previewContainer.style.display = 'block';
                    video.style.display = 'none';
                    
                    this.webcamChecked = true;
                    statusBox.className = 'alert alert-success';
                    statusBox.innerHTML = '<i class="fa-solid fa-circle-check"></i> Webcam verified successfully!';
                    
                    this.triggerStatusUpdate();
                } else {
                    alert("Camera is not active.");
                }
            };

            // Microphone Test Record Button
            const btnRec = document.getElementById('btn-record-mic-test');
            const btnPlay = document.getElementById('btn-play-mic-test');
            const micIcon = document.getElementById('mic-icon-large');
            const micPlayback = document.getElementById('mic-test-playback');
            const pulse = document.getElementById('mic-animation-container');
            const statusBox = document.getElementById('mic-test-status');

            btnRec.onclick = () => {
                this.audioChunks = [];
                navigator.mediaDevices.getUserMedia({ audio: true, video: false })
                    .then(stream => {
                        this.mediaRecorder = new MediaRecorder(stream);
                        this.mediaRecorder.ondataavailable = e => {
                            if (e.data.size > 0) {
                                this.audioChunks.push(e.data);
                            }
                        };
                        
                        this.mediaRecorder.onstop = () => {
                            // Stop mic streams
                            stream.getTracks().forEach(t => t.stop());
                            
                            this.audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                            const audioUrl = URL.createObjectURL(this.audioBlob);
                            
                            micPlayback.src = audioUrl;
                            micPlayback.style.display = 'block';
                            micIcon.style.display = 'none';
                            pulse.style.display = 'none';
                            
                            btnRec.disabled = false;
                            btnRec.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Redo Check';
                            btnPlay.style.display = 'inline-flex';
                            
                            this.micChecked = true;
                            statusBox.className = 'alert alert-success';
                            statusBox.innerHTML = '<i class="fa-solid fa-circle-check"></i> Microphone verified successfully!';
                            this.triggerStatusUpdate();
                        };

                        // Start recording
                        this.mediaRecorder.start();
                        btnRec.disabled = true;
                        btnRec.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Recording...';
                        pulse.style.display = 'flex';
                        micIcon.style.display = 'none';
                        micPlayback.style.display = 'none';

                        // Record for 3 seconds
                        setTimeout(() => {
                            if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
                                this.mediaRecorder.stop();
                            }
                        }, 3000);
                    })
                    .catch(err => {
                        console.error("Error accessing microphone", err);
                        statusBox.className = 'alert alert-danger';
                        statusBox.innerText = 'Microphone: Access denied (' + err.message + ')';
                    });
            };

            btnPlay.onclick = () => {
                micPlayback.play();
            };
        },

        triggerStatusUpdate: function() {
            if (this.statusCallback) {
                this.statusCallback(this.webcamChecked, this.micChecked);
            }
        }
    };

    // ── Active questions sheet controller ────────────────────────────────────
    const ExamQuestionsController = {
        questions: [],
        currentIndex: 0,
        answers: {}, // qid -> { answer_type, answer_text, image_bytes (base64), audio_bytes (base64) }
        candidate: null,
        
        examCameraStream: null,
        examMediaRecorder: null,
        examAudioChunks: [],
        
        qrPollingInterval: null,
        timerInterval: null,
        totalTimeSeconds: 60 * 60, // 60 minutes default

        startExamSession: function(candidate, savedState = null) {
            this.candidate = candidate;
            this.currentIndex = 0;
            this.answers = {};
            this.questions = [];
            
            // Load questions list
            fetch('/api/student/questions')
                .then(res => res.json())
                .then(data => {
                    this.questions = data;
                    
                    // Restore state if available
                    if (savedState) {
                        this.currentIndex = savedState.current_question_index || 0;
                        this.answers = savedState.answers || {};
                        
                        // Parse timer if stored
                        if (savedState.started_at) {
                            const started = new Date(savedState.started_at);
                            const now = new Date();
                            const elapsed = Math.floor((now - started) / 1000);
                            this.totalTimeSeconds = Math.max(0, (60 * 60) - elapsed); // Assume 60 minutes duration
                        }
                    }

                    // Pre-fill answer state structures
                    this.questions.forEach((q, idx) => {
                        const qid = q.id;
                        if (!this.answers[qid]) {
                            this.answers[qid] = {
                                answer_type: 'Text',
                                answer_text: '',
                                image_bytes: null,
                                audio_bytes: null
                            };
                        }
                    });

                    // Start timer countdown
                    this.startCountdown();

                    // Initial question render
                    this.renderQuestion();
                    this.setupActionBindings();
                })
                .catch(err => {
                    console.error("Error starting exam questions sheet", err);
                    alert("Could not load exam questions. Contact administrator.");
                });
        },

        startCountdown: function() {
            const timerSpan = document.getElementById('exam-timer-span');
            
            if (this.timerInterval) clearInterval(this.timerInterval);
            
            const updateTimerDisplay = () => {
                const mins = Math.floor(this.totalTimeSeconds / 60);
                const secs = this.totalTimeSeconds % 60;
                
                timerSpan.innerText = `Time: ${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                
                // Color timer warning
                if (this.totalTimeSeconds < 600) { // Under 10 minutes
                    timerSpan.style.borderColor = 'var(--danger)';
                    timerSpan.style.color = 'var(--danger)';
                    timerSpan.style.background = 'rgba(239, 68, 68, 0.1)';
                }

                if (this.totalTimeSeconds <= 0) {
                    clearInterval(this.timerInterval);
                    alert("Time has expired! Submitting assessment automatically.");
                    this.submitExamSession();
                }
                
                this.totalTimeSeconds--;
            };

            updateTimerDisplay();
            this.timerInterval = setInterval(updateTimerDisplay, 1000);
        },

        renderQuestion: function() {
            if (this.questions.length === 0) return;
            
            // Stop any active webcam stream from prior question
            this.stopExamWebcam();
            this.stopExamMic();

            const idx = this.currentIndex;
            const q = this.questions[idx];
            const qid = q.id;
            
            // 1. Update headers
            document.getElementById('exam-question-number').innerText = `Question ${idx + 1} of ${this.questions.length}`;
            
            // Progress Bar
            const progressPct = ((idx + 1) / this.questions.length) * 100;
            document.getElementById('exam-progress-bar-fill').style.width = `${progressPct}%`;

            // 2. Card Content
            document.getElementById('q-active-title').innerText = q.title;
            document.getElementById('q-active-difficulty').innerText = q.difficulty;
            document.getElementById('q-active-difficulty').className = `badge badge-${q.difficulty.toLowerCase()}`;
            document.getElementById('q-active-marks').innerText = `${q.marks} Marks`;
            document.getElementById('q-active-type').innerText = q.type;
            document.getElementById('q-active-text').innerText = q.text;

            // Optional Image Attachment
            const imageContainer = document.getElementById('q-active-image-container');
            if (q.has_image) {
                document.getElementById('q-active-image').src = `/api/question/image/${q.id}`;
                imageContainer.style.display = 'block';
            } else {
                imageContainer.style.display = 'none';
            }

            // 3. Render map grid
            this.renderQuestionsMap();

            // 4. Show navigation control visibility
            const btnPrev = document.getElementById('btn-exam-prev');
            const btnNext = document.getElementById('btn-exam-next');
            const btnSubmit = document.getElementById('btn-exam-submit');

            btnPrev.style.visibility = (idx > 0) ? 'visible' : 'hidden';
            if (idx === this.questions.length - 1) {
                btnNext.style.display = 'none';
                btnSubmit.style.display = 'inline-flex';
            } else {
                btnNext.style.display = 'inline-flex';
                btnSubmit.style.display = 'none';
            }

            // 5. Answer Layout depending on Type
            const mcqBox = document.getElementById('exam-mcq-response-box');
            const openBox = document.getElementById('exam-open-response-box');
            
            const ans = this.answers[qid];

            if (q.type === 'Multiple Choice') {
                mcqBox.style.display = 'block';
                openBox.style.display = 'none';
                this.renderMCQChoices(q, ans);
            } else {
                mcqBox.style.display = 'none';
                openBox.style.display = 'block';
                this.renderOpenAnswerTabs(q, ans);
            }
        },

        renderQuestionsMap: function() {
            const container = document.getElementById('exam-questions-grid-map');
            container.innerHTML = '';
            
            this.questions.forEach((q, idx) => {
                const item = document.createElement('div');
                item.className = 'btn btn-secondary';
                item.style.padding = '0.5rem';
                item.style.fontSize = '0.9rem';
                item.style.minWidth = '40px';
                item.innerText = (idx + 1).toString();

                const qid = q.id;
                const isCurrent = (idx === this.currentIndex);
                const hasAnswer = this.isQuestionAnswered(q, this.answers[qid]);

                if (isCurrent) {
                    item.className = 'btn btn-primary';
                } else if (hasAnswer) {
                    item.style.background = 'rgba(16, 185, 129, 0.15)';
                    item.style.borderColor = 'var(--success)';
                    item.style.color = 'var(--success)';
                }

                item.onclick = () => {
                    this.saveCurrentQuestionResponseState();
                    this.currentIndex = idx;
                    this.renderQuestion();
                    this.autosaveStateOnServer();
                };

                container.appendChild(item);
            });
        },

        isQuestionAnswered: function(q, ans) {
            if (!ans) return false;
            if (q.type === 'Multiple Choice') {
                if (Array.isArray(ans.answer_text)) {
                    return ans.answer_text.length > 0;
                }
                return !!ans.answer_text;
            }
            
            // Open questions
            return (ans.answer_text && ans.answer_text.trim()) || ans.image_bytes || ans.audio_bytes;
        },

        renderMCQChoices: function(q, ans) {
            const container = document.getElementById('exam-mcq-choices-container');
            container.innerHTML = '';
            
            const isMulti = !!q.is_multi_correct;
            const correctList = Array.isArray(ans.answer_text) ? ans.answer_text : (ans.answer_text ? [ans.answer_text] : []);
            
            Object.keys(q.options).forEach(k => {
                const item = document.createElement('div');
                item.className = 'mcq-choice-item';
                
                const isSelected = correctList.includes(k);
                if (isSelected) item.classList.add('selected');
                
                const inputType = isMulti ? 'checkbox' : 'radio';
                const inputId = `mcq-opt-${k}`;
                const nameAttr = isMulti ? '' : 'name="mcq-radio-group"';
                const checkedAttr = isSelected ? 'checked' : '';

                item.innerHTML = `
                    <input type="${inputType}" id="${inputId}" ${nameAttr} value="${k}" ${checkedAttr}>
                    <label for="${inputId}" style="cursor:pointer; flex:1; margin-bottom:0; color:#ffffff;"><strong>${k}.</strong> ${q.options[k]}</label>
                `;

                item.addEventListener('click', (e) => {
                    // Prevent infinite triggers on checkbox click
                    if (e.target.tagName === 'INPUT') return;
                    
                    const input = item.querySelector('input');
                    if (inputType === 'radio') {
                        document.querySelectorAll('.mcq-choice-item').forEach(el => el.classList.remove('selected'));
                        item.classList.add('selected');
                        input.checked = true;
                        
                        ans.answer_text = k;
                    } else {
                        input.checked = !input.checked;
                        item.classList.toggle('selected', input.checked);
                        
                        // Gather list
                        const selectedCbs = [];
                        document.querySelectorAll('.mcq-choice-item input:checked').forEach(c => {
                            selectedCbs.push(c.value);
                        });
                        ans.answer_text = selectedCbs;
                    }
                    
                    this.renderQuestionsMap();
                });
                
                // Also listen directly to input check
                const inputEl = item.querySelector('input');
                inputEl.addEventListener('change', () => {
                    if (inputType === 'radio') {
                        document.querySelectorAll('.mcq-choice-item').forEach(el => el.classList.remove('selected'));
                        item.classList.add('selected');
                        ans.answer_text = k;
                    } else {
                        item.classList.toggle('selected', inputEl.checked);
                        const selectedCbs = [];
                        document.querySelectorAll('.mcq-choice-item input:checked').forEach(c => {
                            selectedCbs.push(c.value);
                        });
                        ans.answer_text = selectedCbs;
                    }
                    this.renderQuestionsMap();
                });

                container.appendChild(item);
            });
        },

        renderOpenAnswerTabs: function(q, ans) {
            const allowedFormats = q.allowed_formats || ['Text', 'Image', 'Audio'];
            
            const tabText = document.getElementById('header-ans-tab-text');
            const tabImg = document.getElementById('header-ans-tab-image');
            const tabAudio = document.getElementById('header-ans-tab-audio');
            
            tabText.style.display = allowedFormats.includes('Text') ? 'block' : 'none';
            tabImg.style.display = allowedFormats.includes('Image') ? 'block' : 'none';
            tabAudio.style.display = allowedFormats.includes('Audio') ? 'block' : 'none';

            // Select first visible tab as active
            const headers = document.querySelectorAll('#exam-answer-tab-headers .tab-header');
            const contents = document.querySelectorAll('#exam-open-response-box .tab-content');
            
            headers.forEach(h => h.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            
            let firstVisibleTab = null;
            if (allowedFormats.includes('Text')) {
                firstVisibleTab = tabText;
            } else if (allowedFormats.includes('Image')) {
                firstVisibleTab = tabImg;
            } else if (allowedFormats.includes('Audio')) {
                firstVisibleTab = tabAudio;
            }
            
            if (firstVisibleTab) {
                firstVisibleTab.classList.add('active');
                const targetId = firstVisibleTab.getAttribute('data-tab');
                document.getElementById(targetId).classList.add('active');
                
                // Initialize if webcam
                if (targetId === 'ans-tab-image') this.startExamWebcamStream();
            }

            // Restore text answer
            document.getElementById('exam-text-textarea').value = ans.answer_text || '';

            // Handle webcam image answer status banners
            const imgBanner = document.getElementById('exam-active-image-preview-banner');
            if (ans.image_bytes) {
                imgBanner.style.display = 'block';
                imgBanner.innerHTML = `<i class="fa-solid fa-circle-check"></i> Photo Answer captured! Current File Size: ~${Math.round(ans.image_bytes.length * 0.75 / 1024)} KB.`;
                // Show in canvas preview
                const previewImg = document.getElementById('exam-camera-img');
                const previewDiv = document.getElementById('exam-camera-preview');
                const videoEl = document.getElementById('exam-camera-video');
                
                previewImg.src = ans.image_bytes;
                previewDiv.style.display = 'block';
                videoEl.style.display = 'none';
            } else {
                imgBanner.style.display = 'none';
                document.getElementById('exam-camera-preview').style.display = 'none';
                document.getElementById('exam-camera-video').style.display = 'block';
            }

            // Handle audio answer status banners
            const audBanner = document.getElementById('exam-active-audio-preview-banner');
            const audPlayback = document.getElementById('exam-audio-playback');
            const micIcon = document.getElementById('exam-mic-icon');
            
            if (ans.audio_bytes) {
                audBanner.style.display = 'block';
                audPlayback.src = ans.audio_bytes;
                audPlayback.style.display = 'block';
                micIcon.style.display = 'none';
            } else {
                audBanner.style.display = 'none';
                audPlayback.style.display = 'none';
                micIcon.style.display = 'block';
            }

            // Bind tab clicks inside the active exam
            headers.forEach(header => {
                header.onclick = () => {
                    const target = header.getAttribute('data-tab');
                    headers.forEach(h => h.classList.remove('active'));
                    contents.forEach(c => c.classList.remove('active'));
                    
                    header.classList.add('active');
                    document.getElementById(target).classList.add('active');
                    
                    // Stream toggling
                    if (target === 'ans-tab-image') {
                        this.startExamWebcamStream();
                    } else {
                        this.stopExamWebcam();
                    }
                    
                    this.stopExamMic();
                };
            });
        },

        startExamWebcamStream: function() {
            const video = document.getElementById('exam-camera-video');
            const preview = document.getElementById('exam-camera-preview');
            
            if (preview.style.display === 'block') return; // Don't stream if showing snapshot

            if (this.examCameraStream) this.stopExamWebcam();
            
            navigator.mediaDevices.getUserMedia({ video: true, audio: false })
                .then(stream => {
                    this.examCameraStream = stream;
                    video.srcObject = stream;
                    video.style.display = 'block';
                })
                .catch(err => console.error("Webcam stream access error during exam", err));
        },

        stopExamWebcam: function() {
            if (this.examCameraStream) {
                this.examCameraStream.getTracks().forEach(t => t.stop());
                this.examCameraStream = null;
            }
        },

        stopExamMic: function() {
            if (this.examMediaRecorder && this.examMediaRecorder.state === 'recording') {
                this.examMediaRecorder.stop();
            }
            document.getElementById('exam-mic-pulse').style.display = 'none';
            document.getElementById('exam-mic-icon').style.display = 'block';
        },

        saveCurrentQuestionResponseState: function() {
            if (this.questions.length === 0) return;
            const q = this.questions[this.currentIndex];
            const qid = q.id;
            const ans = this.answers[qid];

            if (q.type !== 'Multiple Choice') {
                // Save written text
                ans.answer_text = document.getElementById('exam-text-textarea').value;
                // Answer Type selection logic
                if (ans.image_bytes) {
                    ans.answer_type = 'Image';
                } else if (ans.audio_bytes) {
                    ans.answer_type = 'Audio';
                } else {
                    ans.answer_type = 'Text';
                }
            }
        },

        setupActionBindings: function() {
            // Prev Question button
            document.getElementById('btn-exam-prev').onclick = () => {
                this.saveCurrentQuestionResponseState();
                if (this.currentIndex > 0) {
                    this.currentIndex--;
                    this.renderQuestion();
                    this.autosaveStateOnServer();
                }
            };

            // Next Question button
            document.getElementById('btn-exam-next').onclick = () => {
                this.saveCurrentQuestionResponseState();
                if (this.currentIndex < this.questions.length - 1) {
                    this.currentIndex++;
                    this.renderQuestion();
                    this.autosaveStateOnServer();
                }
            };

            // Submit Exam button
            document.getElementById('btn-exam-submit').onclick = () => {
                if (confirm("Are you sure you want to submit your final assessment answers? This will trigger AI evaluations.")) {
                    this.saveCurrentQuestionResponseState();
                    this.submitExamSession();
                }
            };

            // Camera capture during exam
            document.getElementById('btn-exam-camera-capture').onclick = () => {
                const video = document.getElementById('exam-camera-video');
                const previewImg = document.getElementById('exam-camera-img');
                const previewDiv = document.getElementById('exam-camera-preview');
                const banner = document.getElementById('exam-active-image-preview-banner');
                const qid = this.questions[this.currentIndex].id;
                const ans = this.answers[qid];

                if (this.examCameraStream) {
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth || 640;
                    canvas.height = video.videoHeight || 480;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    const base64Str = canvas.toDataURL('image/png');
                    previewImg.src = base64Str;
                    previewDiv.style.display = 'block';
                    video.style.display = 'none';
                    
                    ans.image_bytes = base64Str;
                    ans.answer_type = 'Image';
                    
                    this.stopExamWebcam();
                    
                    banner.style.display = 'block';
                    banner.innerHTML = `<i class="fa-solid fa-circle-check"></i> Snapshot successfully saved! File Size: ~${Math.round(base64Str.length * 0.75 / 1024)} KB.`;
                    
                    this.renderQuestionsMap();
                    this.autosaveStateOnServer();
                }
            };

            // Image File Input Upload during exam
            document.getElementById('exam-image-file-input').onchange = (e) => {
                const file = e.target.files[0];
                if (!file) return;

                if (file.size > 5 * 1024 * 1024) {
                    alert("File size exceeds 5MB limit. Please upload a smaller image.");
                    e.target.value = '';
                    return;
                }

                const reader = new FileReader();
                reader.onload = (event) => {
                    const base64Str = event.target.result;
                    const qid = this.questions[this.currentIndex].id;
                    const ans = this.answers[qid];
                    
                    ans.image_bytes = base64Str;
                    ans.answer_type = 'Image';
                    
                    // Show in preview element
                    const previewImg = document.getElementById('exam-camera-img');
                    const previewDiv = document.getElementById('exam-camera-preview');
                    const videoEl = document.getElementById('exam-camera-video');
                    
                    previewImg.src = base64Str;
                    previewDiv.style.display = 'block';
                    videoEl.style.display = 'none';
                    
                    this.stopExamWebcam();
                    
                    const banner = document.getElementById('exam-active-image-preview-banner');
                    banner.style.display = 'block';
                    banner.innerHTML = `<i class="fa-solid fa-circle-check"></i> Image file uploaded! File Size: ~${Math.round(base64Str.length * 0.75 / 1024)} KB.`;
                    
                    this.renderQuestionsMap();
                    this.autosaveStateOnServer();
                };
                reader.readAsDataURL(file);
            };

            // Audio Record Buttons
            const btnAudioRec = document.getElementById('btn-exam-audio-record');
            const btnAudioStop = document.getElementById('btn-exam-audio-stop');
            const micIcon = document.getElementById('exam-mic-icon');
            const audioPlayback = document.getElementById('exam-audio-playback');
            const pulse = document.getElementById('exam-mic-pulse');
            const audBanner = document.getElementById('exam-active-audio-preview-banner');

            btnAudioRec.onclick = () => {
                this.examAudioChunks = [];
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(stream => {
                        this.examMediaRecorder = new MediaRecorder(stream);
                        this.examMediaRecorder.ondataavailable = e => {
                            if (e.data.size > 0) this.examAudioChunks.push(e.data);
                        };
                        
                        this.examMediaRecorder.onstop = () => {
                            stream.getTracks().forEach(t => t.stop());
                            
                            const audioBlob = new Blob(this.examAudioChunks, { type: 'audio/webm' });
                            
                            const reader = new FileReader();
                            reader.onload = (event) => {
                                const base64Str = event.target.result;
                                const qid = this.questions[this.currentIndex].id;
                                const ans = this.answers[qid];
                                
                                ans.audio_bytes = base64Str;
                                ans.answer_type = 'Audio';
                                
                                audioPlayback.src = base64Str;
                                audioPlayback.style.display = 'block';
                                micIcon.style.display = 'none';
                                pulse.style.display = 'none';
                                
                                btnAudioRec.style.display = 'inline-flex';
                                btnAudioRec.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Record Again';
                                btnAudioStop.style.display = 'none';
                                
                                audBanner.style.display = 'block';
                                audBanner.innerHTML = `<i class="fa-solid fa-circle-check"></i> Voice answer recorded successfully!`;
                                
                                this.renderQuestionsMap();
                                this.autosaveStateOnServer();
                            };
                            reader.readAsDataURL(audioBlob);
                        };

                        this.examMediaRecorder.start();
                        btnAudioRec.style.display = 'none';
                        btnAudioStop.style.display = 'inline-flex';
                        pulse.style.display = 'flex';
                        micIcon.style.display = 'none';
                        audioPlayback.style.display = 'none';
                    })
                    .catch(err => {
                        console.error("Error accessing microphone inside exam", err);
                        alert("Microphone access denied: " + err.message);
                    });
            };

            btnAudioStop.onclick = () => {
                this.stopExamMic();
            };

            // Audio File Input Upload during exam
            document.getElementById('exam-audio-file-input').onchange = (e) => {
                const file = e.target.files[0];
                if (!file) return;

                if (file.size > 10 * 1024 * 1024) {
                    alert("Audio file size exceeds 10MB limit.");
                    e.target.value = '';
                    return;
                }

                const reader = new FileReader();
                reader.onload = (event) => {
                    const base64Str = event.target.result;
                    const qid = this.questions[this.currentIndex].id;
                    const ans = this.answers[qid];
                    
                    ans.audio_bytes = base64Str;
                    ans.answer_type = 'Audio';
                    
                    // Show in preview element
                    audioPlayback.src = base64Str;
                    audioPlayback.style.display = 'block';
                    micIcon.style.display = 'none';
                    
                    const banner = document.getElementById('exam-active-audio-preview-banner');
                    banner.style.display = 'block';
                    banner.innerHTML = `<i class="fa-solid fa-circle-check"></i> Audio file uploaded successfully!`;
                    
                    this.renderQuestionsMap();
                    this.autosaveStateOnServer();
                };
                reader.readAsDataURL(file);
            };

            // QR Code Companion Toggle Drawers
            const btnToggleQr = document.getElementById('btn-toggle-qr');
            const qrDrawer = document.getElementById('exam-qr-drawer');
            
            btnToggleQr.onclick = () => {
                if (qrDrawer.style.display === 'none') {
                    qrDrawer.style.display = 'block';
                    btnToggleQr.innerHTML = '<i class="fa-solid fa-xmark"></i> Hide QR Code';
                    this.startQrCompanionProcess();
                } else {
                    qrDrawer.style.display = 'none';
                    btnToggleQr.innerHTML = '<i class="fa-solid fa-qrcode"></i> Scan QR Code';
                    this.stopQrCompanionProcess();
                }
            };
        },

        startQrCompanionProcess: function() {
            const qid = this.questions[this.currentIndex].id;
            const qrCanvas = document.getElementById('qr-companion-canvas');
            const statusLabel = document.getElementById('qr-companion-status');
            
            statusLabel.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Generating scanner token...';

            fetch('/api/student/generate_upload_token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question_id: qid })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'ok') {
                    // Generate QR code pointing to the mobile upload route using QRious
                    const host = window.location.origin;
                    const uploadUrl = `${host}/mobile_upload?token=${data.token}`;
                    
                    new QRious({
                        element: qrCanvas,
                        value: uploadUrl,
                        size: 140,
                        level: 'H'
                    });

                    statusLabel.innerHTML = `<strong>Scan this QR code with your mobile camera.</strong><br><span style="font-size:0.75rem; color:var(--text-dim);">Token expires in 5 minutes. Waiting for capture...</span>`;
                    
                    // Start polling
                    this.pollQrCompanionStatus(data.token);
                } else {
                    statusLabel.innerText = "Error: " + data.message;
                }
            })
            .catch(err => {
                console.error("Error generating QR", err);
                statusLabel.innerText = "Connection error generating QR code.";
            });
        },

        pollQrCompanionStatus: function(token) {
            if (this.qrPollingInterval) clearInterval(this.qrPollingInterval);
            
            const qid = this.questions[this.currentIndex].id;
            const ans = this.answers[qid];
            const statusLabel = document.getElementById('qr-companion-status');

            this.qrPollingInterval = setInterval(() => {
                fetch(`/api/student/check_upload_status?token=${token}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.uploaded) {
                            clearInterval(this.qrPollingInterval);
                            this.qrPollingInterval = null;
                            
                            // Retrieve base64 image data
                            ans.image_bytes = data.image_bytes; // Server returns data url or raw base64. Ensure it is a data URL
                            if (ans.image_bytes && !ans.image_bytes.startsWith('data:')) {
                                ans.image_bytes = `data:image/png;base64,${ans.image_bytes}`;
                            }
                            ans.answer_type = 'Image';
                            
                            // Hide QR drawer and show preview
                            document.getElementById('exam-qr-drawer').style.display = 'none';
                            document.getElementById('btn-toggle-qr').innerHTML = '<i class="fa-solid fa-qrcode"></i> Scan QR Code';
                            
                            // Update webcam preview
                            const previewImg = document.getElementById('exam-camera-img');
                            const previewDiv = document.getElementById('exam-camera-preview');
                            const videoEl = document.getElementById('exam-camera-video');
                            
                            previewImg.src = ans.image_bytes;
                            previewDiv.style.display = 'block';
                            videoEl.style.display = 'none';
                            
                            this.stopExamWebcam();

                            const banner = document.getElementById('exam-active-image-preview-banner');
                            banner.style.display = 'block';
                            banner.innerHTML = `<i class="fa-solid fa-circle-check"></i> Image successfully uploaded from mobile!`;
                            
                            this.renderQuestionsMap();
                            this.autosaveStateOnServer();
                        }
                    })
                    .catch(err => console.error("Error polling upload status", err));
            }, 3000);
        },

        stopQrCompanionProcess: function() {
            if (this.qrPollingInterval) {
                clearInterval(this.qrPollingInterval);
                this.qrPollingInterval = null;
            }
        },

        autosaveStateOnServer: function() {
            const payload = {
                current_question_index: this.currentIndex,
                answers: this.answers
            };

            fetch('/api/student/save_state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .catch(err => console.error("State autosave network error", err));
        },

        submitExamSession: function() {
            if (this.timerInterval) clearInterval(this.timerInterval);
            this.stopExamWebcam();
            this.stopExamMic();
            this.stopQrCompanionProcess();

            const overlay = document.getElementById('grading-modal-overlay');
            const statusLabel = document.getElementById('grading-status-label');

            overlay.classList.add('open');
            statusLabel.innerText = "Preparing submission bundle...";

            // Trigger submit_exam route
            fetch('/api/student/submit_exam', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ answers: this.answers })
            })
            .then(res => res.json())
            .then(data => {
                overlay.classList.remove('open');
                
                if (data.status === 'ok') {
                    this.renderSummaryReport(data.results);
                } else {
                    alert(`Evaluation Error: ${data.message}`);
                    // restart timer and allow review
                    this.startCountdown();
                }
            })
            .catch(err => {
                overlay.classList.remove('open');
                console.error("Submission grading network error", err);
                alert("Network error during assessment submission. Please try again.");
                this.startCountdown();
            });
        },

        renderSummaryReport: function(results) {
            document.getElementById('student-exam').style.display = 'none';
            document.getElementById('student-summary-report').style.display = 'block';

            // Metrics
            const mcqResults = results.filter(r => r.type === 'Multiple Choice');
            const mcqScore = mcqResults.reduce((a, b) => a + b.score, 0);
            const mcqMax = mcqResults.reduce((a, b) => a + b.max_score, 0);
            
            const openResults = results.filter(r => r.type !== 'Multiple Choice');
            const openScore = openResults.reduce((a, b) => a + b.score, 0);
            const openMax = openResults.reduce((a, b) => a + b.max_score, 0);

            document.getElementById('summary-mcq-score').innerText = mcqMax > 0 ? `${mcqScore} / ${mcqMax}` : 'N/A';
            document.getElementById('summary-open-score').innerText = openMax > 0 ? `${openScore} / ${openMax}` : 'N/A';

            document.getElementById('summary-candidate-label').innerHTML = `Candidate: <strong>${this.candidate.name}</strong> (ID: <code>${this.candidate.id}</code>) | Email: <code>${this.candidate.email}</code>`;

            // Renders detailed accordions
            const container = document.getElementById('summary-reports-accordion');
            container.innerHTML = '';

            results.forEach((r, idx) => {
                const card = document.createElement('div');
                card.className = 'expander';
                card.id = `rep-card-${idx}`;

                let answerSnippet = '';
                if (r.ans_type === 'Text') {
                    answerSnippet = `
                        <div style="padding:0.75rem; background:rgba(0,0,0,0.2); border-radius:6px; font-size:0.9rem; margin-top:0.5rem; color:#ffffff;">
                            ${r.answer_text || 'No answer text provided.'}
                        </div>
                    `;
                } else if (r.ans_type === 'Image') {
                    answerSnippet = `
                        <div style="margin-top:0.5rem;">
                            <img src="${r.answer_text || '#'}" style="max-height:250px; border-radius:6px; border:1px solid var(--glass-border);" alt="Your Image Answer">
                        </div>
                    `;
                } else if (r.ans_type === 'Audio') {
                    answerSnippet = `
                        <div style="margin-top:0.5rem;">
                            <audio src="${r.answer_text || '#'}" controls style="width:100%; max-width:320px;"></audio>
                        </div>
                    `;
                }

                const parsedEval = marked.parse(r.evaluation || '_Pending AI response._');

                card.innerHTML = `
                    <div class="expander-header">
                        <div class="expander-title-group">
                            <span class="expander-title">Q${idx + 1}: ${r.title}</span>
                        </div>
                        <div style="display:flex; align-items:center; gap:1rem;">
                            <span class="badge badge-medium">Score: ${r.score} / ${r.max_score}</span>
                            <i class="fa-solid fa-chevron-down chevron"></i>
                        </div>
                    </div>
                    <div class="expander-content">
                        <p style="font-size:0.95rem; color:var(--text-muted); margin-bottom:0.75rem;"><strong>Question:</strong> ${r.text}</p>
                        
                        <div style="margin:0.75rem 0;">
                            <strong>Your Submission:</strong>
                            ${answerSnippet}
                        </div>
                        
                        <div class="gemini-report">
                            <h3 style="font-size:1.1rem; color:var(--secondary); margin-bottom:0.5rem;"><i class="fa-solid fa-wand-magic-sparkles"></i> Evaluation Report</h3>
                            <div>${parsedEval}</div>
                        </div>
                    </div>
                `;

                card.querySelector('.expander-header').onclick = () => {
                    card.classList.toggle('open');
                };

                container.appendChild(card);
            });
        }
    };

    // Export to global namespace
    window.ExamHardwareController = ExamHardwareController;
    window.ExamQuestionsController = ExamQuestionsController;
})();
