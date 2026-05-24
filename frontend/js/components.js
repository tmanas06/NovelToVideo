const Components = {
    statusBadge(status) {
        let cls = 'dot yellow';
        if (status === 'completed' || status === 'done' || status === 'success') cls = 'dot green';
        if (status === 'failed' || status === 'error') cls = 'dot red';
        if (status === 'queued') cls = 'dot yellow';
        
        return `
            <div style="display: flex; align-items: center; gap: 6px;">
                <span class="${cls}"></span>
                <span style="font-size: 13px; font-weight: 600; text-transform: capitalize;">${status}</span>
            </div>
        `;
    },

    spinner(size = 'md') {
        const dimensions = size === 'sm' ? '14px' : size === 'lg' ? '32px' : '20px';
        return `<div class="spinner" style="width: ${dimensions}; height: ${dimensions};"></div>`;
    },

    emptyState(icon, message, actionText = '', actionHref = '') {
        return `
            <div style="text-align: center; padding: 48px 24px; border: 1px dashed var(--border-color); border-radius: var(--radius-lg); background-color: var(--bg-surface);">
                <div style="font-size: 40px; margin-bottom: 16px;">[ ]</div>
                <p style="color: var(--text-secondary); margin-bottom: 20px; font-size: 14px;">${message}</p>
                ${actionText ? `<a href="${actionHref}" class="btn primary">${actionText}</a>` : ''}
            </div>
        `;
    },

    progressBar(progress, step, status, timeInfo = null) {
        const percent = Math.round(progress * 100);
        let timeDisplay = '';
        
        if (timeInfo) {
            timeDisplay = `
                <div style="display: flex; gap: 20px; margin-top: 8px; font-size: 11px; color: var(--text-secondary); font-weight: 500;">
                    <span>ELAPSED: <strong>${timeInfo.elapsed}</strong></span>
                    ${timeInfo.remaining ? `<span>REMAINING: <strong>${timeInfo.remaining}</strong></span>` : ''}
                </div>
            `;
        }

        return `
            <div class="progress-container">
                <div class="progress-label">
                    <span style="font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 0.05em; color: var(--text-primary);">
                        ${step ? step.replace('_', ' ') : 'Processing'}
                    </span>
                    <span style="font-weight: 700; color: var(--primary);">${percent}%</span>
                </div>
                <div class="progress-bar-wrapper">
                    <div class="progress-bar-fill" style="width: ${percent}%;"></div>
                </div>
                ${timeDisplay}
            </div>
        `;
    },

    projectCard(project) {
        const dateStr = new Date(project.created_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
        const hasVideo = project.status === 'completed';
        const imagePreset = project.style || 'manga';
        
        return `
            <div class="video-card" id="project-card-${project.id}">
                <div class="video-thumbnail" onclick="${hasVideo ? `App.playVideo('${project.id}', '${project.title}')` : `location.hash='#create';`}" style="aspect-ratio: 9/16;">
                    ${hasVideo ? `
                        <div class="play-overlay">Play</div>
                        <div style="position: absolute; top: 12px; right: 12px; background-color: var(--success); color: white; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 11px; font-weight: 700;">READY</div>
                    ` : `
                        <div style="text-align: center; color: var(--text-secondary); padding: 20px;">
                            <span style="font-size: 40px; display: block; margin-bottom: 12px;">[ ]</span>
                            <span style="font-weight: 600; font-size: 13px;">${project.status.toUpperCase()}</span>
                        </div>
                    `}
                    ${project.scenes && project.scenes[0] && project.scenes[0].image_path ? `
                        <img src="${project.scenes[0].image_path.replace('/home/manas/Desktop/StoryToReel', '')}" alt="first scene preview">
                    ` : ''}
                </div>
                <div class="video-details">
                    <h3 class="video-card-title">${project.title}</h3>
                    <div class="video-card-meta">
                        <span class="badge-pro" style="margin: 0; text-transform: uppercase;">${imagePreset}</span>
                        <span>${dateStr}</span>
                    </div>
                    <div class="video-card-actions">
                        ${hasVideo ? `
                            <button class="btn primary" onclick="App.playVideo('${project.id}', '${project.title}')">Play</button>
                        ` : `
                            <button class="btn secondary" onclick="App.resumeGeneration('${project.id}')">Resume</button>
                        `}
                        <button class="btn danger" onclick="App.confirmDelete('${project.id}', '${project.title}')">Delete</button>
                    </div>
                </div>
            </div>
        `;
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let icon = 'INFO';
        if (type === 'success') icon = 'OK';
        if (type === 'warning') icon = 'WARN';
        if (type === 'error') icon = 'ERR';

        toast.innerHTML = `
            <span>${icon}</span>
            <div style="font-size: 13px; font-weight: 500;">${message}</div>
        `;

        container.appendChild(toast);
        
        // Remove toast after 4 seconds
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s reverse forwards';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    },

    fileUpload(id) {
        return `
            <div class="upload-dropzone" id="dropzone-${id}" onclick="document.getElementById('${id}').click();">
                <span>[ Upload ]</span>
                <p style="font-weight: 600; font-size: 14px; color: var(--text-primary);">Click to upload story text file</p>
                <p style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">Supports only plain text (.txt)</p>
                <input type="file" id="${id}" accept=".txt" style="display: none;">
            </div>
        `;
    },

    styleSelector(selected = 'manga') {
        const options = [
            { id: 'manga', name: 'Manga (B&W High-Contrast Ink)' },
            { id: 'anime', name: 'Anime (Studio Ghibli/Vibrant)' },
            { id: 'realistic', name: 'Realistic (8K Cinematic Photo)' },
            { id: 'fantasy', name: 'Fantasy (Magical Glow Concept)' },
            { id: 'dark', name: 'Dark (Moody Noir Shadows)' },
            { id: 'cinematic', name: 'Cinematic (Dramatic Camera Grade)' }
        ];

        return `
            <select id="story-style" class="form-control">
                ${options.map(opt => `<option value="${opt.id}" ${opt.id === selected ? 'selected' : ''}>${opt.name}</option>`).join('')}
            </select>
        `;
    },

    pipelineStepsList() {
        const steps = [
            { id: 'loading_project', title: 'Initialize Project', desc: 'Fetching story configurations' },
            { id: 'scene_extraction', title: 'Scene Splitter', desc: 'Running Ollama to extract storytelling visual scenes' },
            { id: 'prompt_generation', title: 'Prompt Expansion', desc: 'Crafting highly detailed descriptions for SD models' },
            { id: 'image_generation', title: 'AI Image Generation', desc: 'Synthesizing manga/cinematic portrait visuals' },
            { id: 'narration_generation', title: 'Narration Synthesis', desc: 'Running local Piper TTS vocal narration' },
            { id: 'animation_generation', title: 'Ken Burns Animation', desc: 'Applying pan & zoom camera flows on still scenes' },
            { id: 'subtitle_generation', title: 'Subtitle Burn-In', desc: 'Aligning timed reels subtitles with karaoke scales' },
            { id: 'audio_mixing', title: 'Audio Ducking', desc: 'Mixing speech narration with ambient sound layers' },
            { id: 'video_assembly', title: 'Final Video Rendering', desc: 'Assembling all channels to high-res vertical MP4' }
        ];

        return `
            <div class="pipeline-steps" id="pipeline-steps-checklist">
                ${steps.map(step => `
                    <div class="step-indicator" id="step-row-${step.id}">
                        <div class="step-icon"></div>
                        <div class="step-details">
                            <span class="step-title">${step.title}</span>
                            <span class="step-desc">${step.desc}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
};

window.Components = Components;
