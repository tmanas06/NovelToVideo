const App = {
    currentPage: 'dashboard',
    activeEventSource: null,
    activeTimer: null,
    stylesList: [],

    async init() {
        console.log('StoryToReel AI SPA initialized.');
        
        // Listen for hash changes
        window.addEventListener('hashchange', () => this.handleRouting());
        
        // Global modal close listeners
        const closeModal = document.getElementById('close-modal');
        if (closeModal) {
            closeModal.onclick = () => {
                const modal = document.getElementById('video-modal');
                const player = document.getElementById('modal-video-player');
                modal.classList.remove('open');
                player.pause();
                player.src = '';
            };
        }
        
        // Load settings in memory & styles
        try {
            this.stylesList = await API.getStyles();
        } catch (e) {
            console.error('Failed to load styles preset list:', e);
        }

        // Run initial routing
        this.handleRouting();
        
        // Perform initial system health check and schedule periodically
        this.checkSystemStatus();
        setInterval(() => this.checkSystemStatus(), 30000);
    },

    handleRouting() {
        const hash = window.location.hash || '#dashboard';
        const page = hash.substring(1);
        
        // Set active navigation link
        document.querySelectorAll('.nav-link').forEach(link => {
            if (link.getAttribute('data-page') === page) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
        
        this.currentPage = page;
        this.renderPage(page);
    },

    async checkSystemStatus() {
        const ollamaDot = document.getElementById('ollama-dot');
        const comfyuiDot = document.getElementById('comfyui-dot');
        const piperDot = document.getElementById('piper-dot');
        
        const ollamaText = document.getElementById('ollama-text');
        const comfyuiText = document.getElementById('comfyui-text');
        const piperText = document.getElementById('piper-text');
        
        if (!ollamaDot) return; // Not on page yet
        
        try {
            const report = await API.getSystemStatus();
            
            // Ollama
            if (report.ollama.available) {
                ollamaDot.className = 'dot green';
                ollamaText.textContent = 'ready';
            } else {
                ollamaDot.className = 'dot red';
                ollamaText.textContent = 'offline';
            }
            
            // ComfyUI
            if (report.comfyui.available) {
                comfyuiDot.className = 'dot green';
                comfyuiText.textContent = 'ready';
            } else {
                comfyuiDot.className = 'dot red';
                comfyuiText.textContent = 'offline';
            }
            
            // Piper TTS
            if (report.piper_tts.available && report.piper_tts.voice_model) {
                piperDot.className = 'dot green';
                piperText.textContent = 'ready';
            } else if (report.piper_tts.available) {
                piperDot.className = 'dot yellow';
                piperText.textContent = 'missing voice';
            } else {
                piperDot.className = 'dot red';
                piperText.textContent = 'offline';
            }
        } catch (e) {
            console.error('System health query failed:', e);
        }
    },

    async renderPage(page) {
        const content = document.getElementById('page-content');
        const title = document.getElementById('page-title');
        const headerActions = document.getElementById('header-actions');
        
        content.innerHTML = `<div style="display: flex; justify-content: center; padding: 40px;">${Components.spinner('lg')}</div>`;
        headerActions.innerHTML = '';
        
        // Disconnect any active SSE stream and timer when navigating away from page
        if (this.activeEventSource) {
            this.activeEventSource.close();
            this.activeEventSource = null;
        }
        if (this.activeTimer) {
            clearInterval(this.activeTimer);
            this.activeTimer = null;
        }

        try {
            if (page === 'dashboard') {
                title.textContent = 'Content Factory Dashboard';
                await this.renderDashboard(content, headerActions);
            } else if (page === 'create') {
                title.textContent = 'Create New Reel/Short';
                await this.renderCreatePage(content);
            } else if (page === 'batch') {
                title.textContent = 'Batch Process stories';
                await this.renderBatchPage(content);
            } else if (page === 'outputs') {
                title.textContent = 'Generated Exports';
                await this.renderOutputsPage(content);
            } else if (page === 'settings') {
                title.textContent = 'Pipeline Configuration';
                await this.renderSettingsPage(content);
            } else {
                title.textContent = 'Dashboard';
                location.hash = '#dashboard';
            }
        } catch (err) {
            content.innerHTML = `
                <div class="card" style="border-color: var(--error);">
                    <h3 style="color: var(--error); margin-bottom: 12px;">Error Loading Page</h3>
                    <p style="color: var(--text-secondary);">${err.message}</p>
                    <button class="btn secondary" style="margin-top: 16px;" onclick="App.handleRouting()">Retry</button>
                </div>
            `;
        }
    },

    async renderDashboard(container, actions) {
        // Fetch projects list
        const projects = await API.getProjects();
        
        const total = projects.length;
        const completed = projects.filter(p => p.status === 'completed').length;
        const failed = projects.filter(p => p.status === 'failed').length;
        const processing = projects.filter(p => p.status === 'generating').length;
        
        actions.innerHTML = `<a href="#create" class="btn primary">➕ Create New Video</a>`;

        container.innerHTML = `
            <div class="dashboard-grid">
                <div class="stat-card">
                    <span class="label">Total Videos</span>
                    <span class="value">${total}</span>
                </div>
                <div class="stat-card" style="border-left: 4px solid var(--success);">
                    <span class="label">Ready / Exported</span>
                    <span class="value">${completed}</span>
                </div>
                <div class="stat-card" style="border-left: 4px solid var(--primary);">
                    <span class="label">Active Generation</span>
                    <span class="value">${processing}</span>
                </div>
                <div class="stat-card" style="border-left: 4px solid var(--error);">
                    <span class="label">Pipeline Crashes</span>
                    <span class="value">${failed}</span>
                </div>
            </div>

            <div class="card">
                <div class="card-title">
                    <span>Recent Content Factory Projects</span>
                    <a href="#outputs" style="color: var(--primary); font-size: 13px; text-decoration: none; font-weight: 600;">View All</a>
                </div>
                ${total === 0 ? Components.emptyState(' ', 'No projects created yet. Start by turning a story into a stunning vertical video!', 'Create Video', '#create') : `
                    <div class="outputs-grid">
                        ${projects.slice(0, 4).map(p => Components.projectCard(p)).join('')}
                    </div>
                `}
            </div>
        `;
    },

    async renderCreatePage(container) {
        container.innerHTML = `
            <div class="card" id="generation-form-container">
                <div class="card-title">Video Details</div>
                <form id="create-project-form" onsubmit="App.handleCreateSubmit(event)">
                    <div class="form-group">
                        <label for="story-title">Project Title</label>
                        <input type="text" id="story-title" class="form-control" placeholder="e.g. The Legend of Leo" required>
                    </div>

                    <div class="form-group">
                        <label for="story-style">Artistic Preset Style</label>
                        ${Components.styleSelector()}
                    </div>

                    <div class="form-group">
                        <label>Story text or Novel Chapter</label>
                        <textarea id="story-text" class="form-control" placeholder="Paste your raw text, summary, novel paragraph here..." required></textarea>
                    </div>

                    <div style="margin: 24px 0 20px 0;">
                        <p style="font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px;">OR IMPORT A STORY FILE</p>
                        ${Components.fileUpload('file-uploader')}
                    </div>

                    <div style="display: flex; gap: 16px; margin-top: 24px;">
                        <button type="submit" class="btn primary" style="flex: 1;">Start Automated Pipeline</button>
                        <button type="reset" class="btn secondary">Reset</button>
                    </div>
                </form>
            </div>

            <!-- Pipeline Monitoring Panel (hidden initially) -->
            <div class="card" id="pipeline-monitor-panel" style="display: none;">
                <div class="card-title" style="margin-bottom: 12px;">
                    <span>Live Processing Pipeline</span>
                    <span id="pipeline-status-badge">generating</span>
                </div>
                
                <div id="pipeline-progress-slot">
                    <!-- Progress bar -->
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 24px;">
                    <div>
                        <h4 style="margin-bottom: 12px;">Step Checklist</h4>
                        ${Components.pipelineStepsList()}
                    </div>
                    <div>
                        <h4 style="margin-bottom: 12px;">Factory Terminal (Real-time Engine Output)</h4>
                        <div class="engine-terminal" id="pipeline-engine-terminal">
                            <div class="terminal-line"><span class="terminal-timestamp">${new Date().toLocaleTimeString()}</span> <span class="terminal-info">[SYSTEM]</span> Factory engine standing by...</div>
                        </div>
                    </div>
                </div>

                <div style="margin-top: 28px;">
                    <h4 style="margin-bottom: 12px;">Generated Image Previews</h4>
                    <div class="preview-grid" id="pipeline-previews-slot">
                        <!-- generated scenes preview -->
                    </div>
                </div>
            </div>
        `;

        // Handle file uploader change
        const fileInput = document.getElementById('file-uploader');
        const textInput = document.getElementById('story-text');
        const titleInput = document.getElementById('story-title');
        
        if (fileInput) {
            fileInput.onchange = (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                const reader = new FileReader();
                reader.onload = (event) => {
                    textInput.value = event.target.result;
                    titleInput.value = file.name.replace(/\.[^/.]+$/, ""); // strip extension
                    Components.showToast('Text file loaded successfully!', 'success');
                };
                reader.readAsText(file);
            };
        }
    },

    async handleCreateSubmit(e) {
        e.preventDefault();
        
        const title = document.getElementById('story-title').value.trim();
        const style = document.getElementById('story-style').value;
        const storyText = document.getElementById('story-text').value.trim();
        
        if (!title || !storyText) {
            Components.showToast('Please fill out all fields', 'error');
            return;
        }

        const submitBtn = e.target.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting task...';

        try {
            // 1. Create project
            const project = await API.createProject(title, storyText, style);
            Components.showToast('Project registered in database.', 'success');
            
            // 2. Hide form, show monitor panel
            document.getElementById('generation-form-container').style.display = 'none';
            const monitor = document.getElementById('pipeline-monitor-panel');
            monitor.style.display = 'block';
            
            // 3. Trigger video generation
            const job = await API.startGeneration(project.id);
            Components.showToast('Task queued in worker thread.', 'success');
            
            // 4. Start progress stream
            this.monitorPipelineProgress(job.id, project.id);
            
        } catch (err) {
            Components.showToast(`Generation launch failed: ${err.message}`, 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Automated Pipeline';
        }
    },

    async monitorPipelineProgress(jobId, projectId) {
        const progressSlot = document.getElementById('pipeline-progress-slot');
        const engineTerminal = document.getElementById('pipeline-engine-terminal');
        const previewsSlot = document.getElementById('pipeline-previews-slot');
        const badgeSlot = document.getElementById('pipeline-status-badge');
        
        progressSlot.innerHTML = Components.progressBar(0.0, 'queued', 'queued');
        badgeSlot.innerHTML = Components.statusBadge('queued');
        
        let lastStep = '';
        const startTime = Date.now();
        let timerInterval = null;
        
        // Fetch settings for better time estimation
        let settings = { image_mode: 'comfyui', scenes_per_story: 5 };
        try {
            settings = await API.getSettings();
        } catch (e) { console.error('Failed to load settings for timer:', e); }

        const formatTime = (seconds) => {
            if (seconds < 0) return '0s';
            const m = Math.floor(seconds / 60);
            const s = Math.floor(seconds % 60);
            return m > 0 ? `${m}m ${s}s` : `${s}s`;
        };

        const updateTimerDisplay = (progress, step) => {
            const elapsedSeconds = (Date.now() - startTime) / 1000;
            
            // Heuristic-based estimation
            const N = settings.scenes_per_story || 5;
            let imgTime = settings.image_mode === 'comfyui' ? 180 : (settings.image_mode === 'api' ? 10 : 2);
            let totalEstimatedSeconds = 50 + (imgTime * N) + (13 * N);
            
            // Adjust estimate if it seems too low based on progress
            if (progress > 0 && progress < 1) {
                const currentExtrapolatedTotal = elapsedSeconds / progress;
                totalEstimatedSeconds = Math.max(totalEstimatedSeconds, currentExtrapolatedTotal);
            }

            const remainingSeconds = Math.max(0, totalEstimatedSeconds - elapsedSeconds);
            
            const timeInfo = {
                elapsed: formatTime(elapsedSeconds),
                remaining: progress < 1.0 ? formatTime(remainingSeconds) : null
            };
            
            progressSlot.innerHTML = Components.progressBar(progress, step, 'generating', timeInfo);
        };

        // Initial timer start
        this.activeTimer = setInterval(() => {
            if (lastStep && lastStep !== 'finished' && lastStep !== 'failed') {
                // We need the current progress value, let's store it locally
                updateTimerDisplay(window._currentJobProgress || 0, lastStep);
            }
        }, 1000);
        
        this.activeEventSource = API.subscribeToProgress(jobId, (event) => {
            const { type, step, progress, message, level } = event;
            window._currentJobProgress = progress;
            
            // Handle Progress events
            if (!type || type === 'progress') {
                lastStep = step;
                updateTimerDisplay(progress, step);
                badgeSlot.innerHTML = Components.statusBadge('generating');
                
                // Write high-level checklist logs
                if (message) {
                    const time = new Date().toLocaleTimeString();
                    const logEntry = document.createElement('div');
                    logEntry.className = 'terminal-line';
                    logEntry.innerHTML = `<span class="terminal-timestamp">${time}</span> <span class="terminal-info">[INFO]</span> ${message}`;
                    if (engineTerminal) {
                        engineTerminal.appendChild(logEntry);
                        engineTerminal.scrollTop = engineTerminal.scrollHeight;
                    }
                }
                
                // Highlight step list
                if (step !== lastStep || true) { // Always refresh to ensure spinner is correct
                    // ... (rest of step highlighting logic)
                    const stepsIds = [
                        'loading_project', 'scene_extraction', 'prompt_generation', 
                        'image_generation', 'narration_generation', 'animation_generation', 
                        'subtitle_generation', 'audio_mixing', 'video_assembly'
                    ];
                    
                    const currentIdx = stepsIds.indexOf(step);
                    stepsIds.forEach((sid, idx) => {
                        const row = document.getElementById(`step-row-${sid}`);
                        if (row) {
                            if (idx < currentIdx) {
                                row.className = 'step-indicator completed';
                                row.querySelector('.step-icon').textContent = '✓';
                            } else if (idx === currentIdx) {
                                row.className = 'step-indicator active';
                                row.querySelector('.step-icon').innerHTML = Components.spinner('sm');
                            } else {
                                row.className = 'step-indicator';
                                row.querySelector('.step-icon').textContent = '○';
                            }
                        }
                    });
                }

                // Image generation previews
                if (step === 'image_generation' && message.includes("Generated image")) {
                    this.updatePipelinePreviews(projectId, previewsSlot);
                }

                // Pipeline complete!
                if (step === 'finished') {
                    if (this.activeTimer) {
                        clearInterval(this.activeTimer);
                        this.activeTimer = null;
                    }
                    Components.showToast('Video built and exported!', 'success');
                    badgeSlot.innerHTML = Components.statusBadge('completed');
                    document.querySelectorAll('.step-indicator').forEach(row => {
                        row.className = 'step-indicator completed';
                        row.querySelector('.step-icon').textContent = 'OK';
                    });
                    setTimeout(() => {
                        this.playVideo(projectId, 'Generation complete');
                        location.hash = '#outputs';
                    }, 1500);
                }

                // Pipeline error!
                if (step === 'failed') {
                    if (this.activeTimer) {
                        clearInterval(this.activeTimer);
                        this.activeTimer = null;
                    }
                    Components.showToast('Pipeline crash detected.', 'error');
                    badgeSlot.innerHTML = Components.statusBadge('failed');
                    const activeRow = document.querySelector('.step-indicator.active');
                    if (activeRow) {
                        activeRow.className = 'step-indicator';
                        activeRow.querySelector('.step-icon').textContent = 'X';
                    }

                    // Add Retry Button if it doesn't exist
                    if (!document.getElementById('retry-pipeline-btn')) {
                        const retryBtn = document.createElement('button');
                        retryBtn.id = 'retry-pipeline-btn';
                        retryBtn.className = 'btn primary';
                        retryBtn.style.marginTop = '20px';
                        retryBtn.innerHTML = 'Try Again / Restart Pipeline';
                        retryBtn.onclick = () => this.handleResetAndRetry(projectId);
                        progressSlot.appendChild(retryBtn);
                    }
                }
            } 
            // Handle Log events
            else if (type === 'log') {
                const time = new Date().toLocaleTimeString();
                const levelClass = `terminal-${level || 'info'}`;
                const logEntry = document.createElement('div');
                logEntry.className = 'terminal-line';
                logEntry.innerHTML = `<span class="terminal-timestamp">${time}</span> <span class="${levelClass}">[${(level || 'info').toUpperCase()}]</span> ${message}`;
                
                if (engineTerminal) {
                    engineTerminal.appendChild(logEntry);
                    engineTerminal.scrollTop = engineTerminal.scrollHeight;
                }
            }
        });
    },

    async handleResetAndRetry(projectId) {
        try {
            Components.showToast('Re-initializing pipeline...', 'info');
            
            // 1. Reset UI
            const monitor = document.getElementById('pipeline-monitor-panel');
            const engineTerminal = document.getElementById('pipeline-engine-terminal');
            const previewsSlot = document.getElementById('pipeline-previews-slot');
            
            engineTerminal.innerHTML = `<div class="terminal-line"><span class="terminal-timestamp">${new Date().toLocaleTimeString()}</span> <span class="terminal-info">[SYSTEM]</span> Factory engine restarting...</div>`;
            previewsSlot.innerHTML = '';
            
            // Remove retry button if it exists
            const retryBtn = document.getElementById('retry-pipeline-btn');
            if (retryBtn) retryBtn.remove();

            // 2. Trigger video generation again
            const job = await API.startGeneration(projectId);
            Components.showToast('Task re-queued in worker thread.', 'success');
            
            // 3. Re-start monitoring
            this.monitorPipelineProgress(job.id, projectId);
            
        } catch (err) {
            Components.showToast(`Retry failed: ${err.message}`, 'error');
        }
    },


    async updatePipelinePreviews(projectId, container) {
        try {
            const project = await API.getProject(projectId);
            if (project && project.scenes) {
                container.innerHTML = project.scenes
                    .filter(s => s.image_path)
                    .map(s => `
                        <div class="preview-item">
                            <span class="scene-tag">Scene ${s.scene_number}</span>
                            <img src="${s.image_path.replace('/home/manas/Desktop/StoryToReel', '')}" alt="scene preview">
                        </div>
                    `).join('');
            }
        } catch (e) {
            console.error('Failed to load live preview thumbnails:', e);
        }
    },

    async renderBatchPage(container) {
        container.innerHTML = `
            <div class="card">
                <div class="card-title">Bulk Story Submissions</div>
                <p style="color: var(--text-secondary); margin-bottom: 20px; font-size: 13px;">
                    Submit multiple stories simultaneously. The factory will process them sequentially one by one in the background.
                </p>
                <div id="batch-slots-container">
                    <!-- Dynamic slots injected here -->
                </div>
                
                <div style="display: flex; gap: 16px; margin-top: 24px;">
                    <button class="btn secondary" onclick="App.addBatchSlot()">Add Story</button>
                    <button class="btn primary" onclick="App.submitBatchForm()">Submit Batch Queue</button>
                </div>
            </div>
            
            <!-- Active batch job monitor list -->
            <div class="card" id="batch-monitor-card" style="display: none;">
                <div class="card-title">Active Batch Processing Queue</div>
                <div id="batch-monitor-rows" style="display: flex; flex-direction: column; gap: 8px;">
                    <!-- progress rows -->
                </div>
            </div>
        `;
        
        // Add two starting slots by default
        this.addBatchSlot();
        this.addBatchSlot();
    },

    addBatchSlot() {
        const container = document.getElementById('batch-slots-container');
        const slotCount = container.children.length + 1;
        const slotId = `batch-slot-${slotCount}-${Math.random().toString(36).substr(2, 5)}`;
        
        const slotDiv = document.createElement('div');
        slotDiv.className = 'batch-story-slot';
        slotDiv.id = slotId;
        
        slotDiv.innerHTML = `
            <span class="remove-slot-btn" onclick="document.getElementById('${slotId}').remove();">&times;</span>
            <h4 style="margin-bottom: 12px; color: var(--primary);">Story Slot #${slotCount}</h4>
            <div class="form-group">
                <label>Story Title</label>
                <input type="text" class="form-control batch-title" placeholder="e.g. Chapter ${slotCount} summary" required>
            </div>
            <div class="form-group">
                <label>Artistic style</label>
                ${Components.styleSelector()}
            </div>
            <div class="form-group">
                <label>Story Text</label>
                <textarea class="form-control batch-text" placeholder="Enter story text..." required></textarea>
            </div>
        `;
        container.appendChild(slotDiv);
    },

    async submitBatchForm() {
        const slots = document.querySelectorAll('.batch-story-slot');
        const stories = [];
        
        slots.forEach(slot => {
            const title = slot.querySelector('.batch-title').value.trim();
            const style = slot.querySelector('select').value;
            const storyText = slot.querySelector('.batch-text').value.trim();
            
            if (title && storyText) {
                stories.push({ title, story_text: storyText, style });
            }
        });

        if (stories.length === 0) {
            Components.showToast('Please fill out at least one story', 'error');
            return;
        }

        try {
            const result = await API.submitBatch(stories);
            Components.showToast(`Batch of ${stories.length} stories submitted successfully!`, 'success');
            
            // Hide input card, show monitor panel
            document.getElementById('batch-slots-container').parentElement.style.display = 'none';
            const monitor = document.getElementById('batch-monitor-card');
            monitor.style.display = 'block';
            
            // Populate monitor rows
            const rowsContainer = document.getElementById('batch-monitor-rows');
            rowsContainer.innerHTML = result.jobs.map(job => `
                <div class="batch-job-row" id="batch-job-row-${job.id}">
                    <span style="font-weight: 600;">Job ID: ${job.id.substr(0, 8)}</span>
                    <span id="batch-job-step-${job.id}">Queued</span>
                    <span id="batch-job-progress-${job.id}" style="font-weight: 700; color: var(--primary);">0%</span>
                </div>
            `).join('');
            
            // Listen to each job's events one by one or concurrently (only sequentially triggers anyway)
            result.jobs.forEach(job => {
                API.subscribeToProgress(job.id, (e) => {
                    const row = document.getElementById(`batch-job-row-${job.id}`);
                    const stepText = document.getElementById(`batch-job-step-${job.id}`);
                    const progressText = document.getElementById(`batch-job-progress-${job.id}`);
                    
                    if (row) {
                        stepText.textContent = e.step.replace('_', ' ');
                        progressText.textContent = `${Math.round(e.progress * 100)}%`;
                        
                        if (e.step === 'finished') {
                            row.style.borderLeft = '4px solid var(--success)';
                            progressText.style.color = 'var(--success)';
                        }
                        if (e.step === 'failed') {
                            row.style.borderLeft = '4px solid var(--error)';
                            progressText.style.color = 'var(--error)';
                        }
                    }
                });
            });

        } catch (e) {
            Components.showToast(`Batch submit failed: ${e.message}`, 'error');
        }
    },

    async renderOutputsPage(container) {
        const projects = await API.getProjects();
        
        container.innerHTML = `
            <div class="card">
                <div class="card-title">Completed MP4 Exports</div>
                ${projects.length === 0 ? Components.emptyState(' ', 'No videos exported yet. Build one from the Create page!', 'Create Video', '#create') : `
                    <div class="outputs-grid">
                        ${projects.map(p => Components.projectCard(p)).join('')}
                    </div>
                `}
            </div>
        `;
    },

    async playVideo(projectId, title) {
        const project = await API.getProject(projectId);
        if (!project || project.status !== 'completed') {
            Components.showToast('Video not ready or has failed', 'warning');
            return;
        }

        // Search for output video path. Since the file is saved to outputs/,
        // and we have mapped outputs/ to /outputs/ static route,
        // we can guess the URL: /outputs/{sanitized_title}_{short_id}.mp4
        // Let's call a quick method or read output video name directly
        // The project Response has scenes, let's construct the output URL:
        // We know final output files are in /outputs/...
        // Let's get title and id to find the exact filename:
        // Our python helper creates outputs/{sanitized_title}_{short_id}.mp4
        const sanitizedTitle = project.title.replace(/[^a-zA-Z0-9\s\-]/g, '_').replace(/\s+/g, '-').trim().toLowerCase() || "project";
        const shortId = project.id.substring(0, 8);
        const videoUrl = `/outputs/${sanitizedTitle}_${shortId}.mp4`;

        const modal = document.getElementById('video-modal');
        const player = document.getElementById('modal-video-player');
        const modalTitle = document.getElementById('modal-video-title');
        const downloadBtn = document.getElementById('modal-download-btn');
        
        if (modal) {
            modalTitle.textContent = title || project.title;
            player.src = videoUrl;
            downloadBtn.href = videoUrl;
            modal.classList.add('open');
            player.load();
            player.play();
        }
    },

    async resumeGeneration(projectId) {
        try {
            const job = await API.startGeneration(projectId);
            Components.showToast('Re-triggering pipeline...', 'success');
            location.hash = '#create';
            // Wait slightly for DOM to render create page, then hijack panel
            setTimeout(() => {
                document.getElementById('generation-form-container').style.display = 'none';
                const monitor = document.getElementById('pipeline-monitor-panel');
                monitor.style.display = 'block';
                this.monitorPipelineProgress(job.id, projectId);
            }, 500);
        } catch (e) {
            Components.showToast(`Resume trigger failed: ${e.message}`, 'error');
        }
    },

    confirmDelete(projectId, title) {
        if (confirm(`Are you absolutely sure you want to delete "${title}"? This will delete all generated assets, narration, images and final video.`)) {
            this.deleteProject(projectId);
        }
    },

    async deleteProject(projectId) {
        try {
            await API.deleteProject(projectId);
            Components.showToast('Project deleted successfully.', 'success');
            // Remove from outputs page or re-render
            const card = document.getElementById(`project-card-${projectId}`);
            if (card) {
                card.remove();
            } else {
                this.renderPage(this.currentPage);
            }
        } catch (e) {
            Components.showToast(`Delete failed: ${e.message}`, 'error');
        }
    },

    async renderSettingsPage(container) {
        const settings = await API.getSettings();
        
        container.innerHTML = `
            <div class="card">
                <div class="card-title">Backend Configuration Engine</div>
                <form id="settings-form" onsubmit="App.handleSettingsSubmit(event)">
                    
                    <h3 style="margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">AI Engines</h3>
                    
                    <div class="form-group">
                        <label for="ollama-url">Ollama Local API URL</label>
                        <input type="text" id="ollama-url" class="form-control" value="${settings.ollama_url}" required>
                    </div>

                    <div class="form-group">
                        <label for="ollama-model">Ollama LLM Model</label>
                        <input type="text" id="ollama-model" class="form-control" value="${settings.ollama_model}" required>
                        <p style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">Recommended: qwen2.5:3b or phi4-mini for fast CPU processing</p>
                    </div>

                    <div class="form-group">
                        <label for="image-mode">Image Generation Mode</label>
                        <select id="image-mode" class="form-control">
                            <option value="comfyui" ${settings.image_mode === 'comfyui' ? 'selected' : ''}>Local ComfyUI (SD1.5, Slow on CPU)</option>
                            <option value="api" ${settings.image_mode === 'api' ? 'selected' : ''}>External REST API (Fast, Cloud)</option>
                            <option value="placeholder" ${settings.image_mode === 'placeholder' ? 'selected' : ''}>Pillow Placeholders (Gradient + Overlay Text, Ultra-Fast testing)</option>
                        </select>
                    </div>

                    <div class="form-group" id="image-api-fields" style="display: ${settings.image_mode === 'api' ? 'block' : 'none'};">
                        <label for="image-api-url">Image REST API Endpoint URL</label>
                        <input type="text" id="image-api-url" class="form-control" value="${settings.image_api_url || ''}">
                        <label for="image-api-key" style="margin-top: 10px;">API Authorization Bearer Key</label>
                        <input type="password" id="image-api-key" class="form-control" value="${settings.image_api_key || ''}">
                    </div>

                    <div class="form-group">
                        <label for="comfyui-url">ComfyUI Local API URL</label>
                        <input type="text" id="comfyui-url" class="form-control" value="${settings.comfyui_url}" required>
                    </div>

                    <h3 style="margin: 28px 0 16px 0; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">Audio & TTS settings</h3>
                    
                    <div class="form-group">
                        <label for="tts-voice">Piper TTS Voice</label>
                        <input type="text" id="tts-voice" class="form-control" value="${settings.tts_voice}" required>
                        <p style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">Default American Voice: en_US-lessac-medium</p>
                    </div>

                    <div class="form-group">
                        <label for="tts-speed">Narration Speed Ratio</label>
                        <input type="number" id="tts-speed" class="form-control" step="0.1" min="0.5" max="2.0" value="${settings.tts_speed}" required>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div class="form-group">
                            <label for="narration-vol">Narration Volume</label>
                            <input type="number" id="narration-vol" class="form-control" step="0.05" min="0.0" max="1.0" value="${settings.narration_volume}" required>
                        </div>
                        <div class="form-group">
                            <label for="music-vol">Background Music Volume</label>
                            <input type="number" id="music-vol" class="form-control" step="0.05" min="0.0" max="1.0" value="${settings.bg_music_volume}" required>
                        </div>
                    </div>

                    <h3 style="margin: 28px 0 16px 0; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">Video Assembly Resolution</h3>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div class="form-group">
                            <label for="video-w">Width</label>
                            <input type="number" id="video-w" class="form-control" value="${settings.video_width}" required>
                        </div>
                        <div class="form-group">
                            <label for="video-h">Height</label>
                            <input type="number" id="video-h" class="form-control" value="${settings.video_height}" required>
                        </div>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div class="form-group">
                            <label for="video-fps">FPS Frame Rate</label>
                            <input type="number" id="video-fps" class="form-control" value="${settings.video_fps}" required>
                        </div>
                        <div class="form-group">
                            <label for="story-scenes-count">Storyboard Scenes Per Novel</label>
                            <input type="number" id="story-scenes-count" class="form-control" value="${settings.scenes_per_story}" required>
                        </div>
                    </div>

                    <div style="display: flex; gap: 16px; margin-top: 32px;">
                        <button type="submit" class="btn primary" style="flex: 1;">Save Configuration</button>
                        <button type="button" class="btn secondary" onclick="App.checkSystemStatus()">Check Health</button>
                    </div>
                </form>
            </div>
        `;

        // Toggle API details display when image mode select changes
        const selectMode = document.getElementById('image-mode');
        const apiFields = document.getElementById('image-api-fields');
        if (selectMode) {
            selectMode.onchange = (e) => {
                if (e.target.value === 'api') {
                    apiFields.style.display = 'block';
                } else {
                    apiFields.style.display = 'none';
                }
            };
        }
    },

    async handleSettingsSubmit(e) {
        e.preventDefault();
        
        const updates = {
            ollama_url: document.getElementById('ollama-url').value,
            ollama_model: document.getElementById('ollama-model').value,
            image_mode: document.getElementById('image-mode').value,
            image_api_url: document.getElementById('image-api-url').value,
            image_api_key: document.getElementById('image-api-key').value,
            comfyui_url: document.getElementById('comfyui-url').value,
            tts_voice: document.getElementById('tts-voice').value,
            tts_speed: parseFloat(document.getElementById('tts-speed').value),
            narration_volume: parseFloat(document.getElementById('narration-vol').value),
            bg_music_volume: parseFloat(document.getElementById('music-vol').value),
            video_width: parseInt(document.getElementById('video-w').value),
            video_height: parseInt(document.getElementById('video-h').value),
            video_fps: parseInt(document.getElementById('video-fps').value),
            scenes_per_story: parseInt(document.getElementById('story-scenes-count').value),
        };

        const submitBtn = e.target.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving...';

        try {
            await API.updateSettings(updates);
            Components.showToast('Settings saved successfully!', 'success');
            this.checkSystemStatus();
        } catch (err) {
            Components.showToast(`Failed to save settings: ${err.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Save Configuration';
        }
    }
};

window.App = App;
document.addEventListener('DOMContentLoaded', () => App.init());
