const API = {
    baseUrl: '',

    async request(url, options = {}) {
        const res = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            }
        });
        if (!res.ok) {
            const errBody = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(errBody.detail || 'API request failed');
        }
        return res.json();
    },

    async createProject(title, storyText, style = 'manga') {
        return this.request('/api/projects/', {
            method: 'POST',
            body: JSON.stringify({ title, story_text: storyText, style })
        });
    },

    async getProjects() {
        return this.request('/api/projects/');
    },

    async getProject(id) {
        return this.request(`/api/projects/${id}`);
    },

    async deleteProject(id) {
        return this.request(`/api/projects/${id}`, {
            method: 'DELETE'
        });
    },

    async startGeneration(projectId) {
        return this.request(`/api/generate/${projectId}`, {
            method: 'POST'
        });
    },

    async getGenerationStatus(projectId) {
        return this.request(`/api/generate/${projectId}/status`);
    },

    async submitBatch(stories) {
        return this.request('/api/batch/', {
            method: 'POST',
            body: JSON.stringify({ stories })
        });
    },

    async getSettings() {
        return this.request('/api/settings/');
    },

    async updateSettings(settings) {
        return this.request('/api/settings/', {
            method: 'PUT',
            body: JSON.stringify(settings)
        });
    },

    async getStyles() {
        return this.request('/api/settings/styles');
    },

    async getSystemStatus() {
        return this.request('/api/settings/status');
    },

    subscribeToProgress(jobId, onEvent) {
        const source = new EventSource(`/api/events/${jobId}`);
        
        source.addEventListener('progress', (e) => {
            try {
                const data = JSON.parse(e.data);
                onEvent(data);
            } catch (err) {
                console.error('Error parsing SSE progress data:', err);
            }
        });

        source.addEventListener('error', (err) => {
            console.error('SSE Error:', err);
            source.close();
        });

        return source;
    }
};
window.API = API;
