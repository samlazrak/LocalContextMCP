// Main Application JavaScript for Local IDE
class LocalIDE {
    constructor() {
        this.sessionId = null;
        this.workspacePath = null;
        this.currentFile = null;
        this.openFiles = new Map();
        this.editor = null;
        this.socket = null;
        this.terminal = null;
        
        this.init();
    }
    
    async init() {
        // Initialize session
        await this.createSession();
        
        // Initialize components
        this.initializeEditor();
        this.initializeSocket();
        this.initializeEventListeners();
        this.initializeTerminal();
        
        // Load workspace if available
        this.checkForWorkspace();
    }
    
    async createSession() {
        try {
            const response = await this.sendRequest('create_session');
            this.sessionId = response.session_id;
            console.log('Session created:', this.sessionId);
        } catch (error) {
            console.error('Failed to create session:', error);
        }
    }
    
    initializeEditor() {
        this.editor = CodeMirror(document.getElementById('editor'), {
            theme: 'material-darker',
            lineNumbers: true,
            autoCloseBrackets: true,
            matchBrackets: true,
            indentUnit: 4,
            tabSize: 4,
            mode: 'javascript',
            extraKeys: {
                'Ctrl-S': () => this.saveCurrentFile(),
                'Ctrl-O': () => this.openWorkspace(),
                'Ctrl-P': () => this.quickOpen(),
                'Ctrl-Shift-P': () => this.commandPalette(),
                'Ctrl-`': () => this.toggleTerminal(),
                'Ctrl-Space': 'autocomplete'
            }
        });
        
        // Hide editor initially
        document.getElementById('editor').style.display = 'none';
        
        // Editor event listeners
        this.editor.on('change', () => {
            if (this.currentFile) {
                this.markFileAsModified(this.currentFile);
            }
        });
        
        this.editor.on('cursorActivity', () => {
            this.updateCursorPosition();
        });
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateConnectionStatus(true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('file_change', (data) => {
            this.handleFileChange(data);
        });
    }
    
    initializeEventListeners() {
        // Menu buttons
        document.getElementById('new-file-btn').addEventListener('click', () => this.newFile());
        document.getElementById('open-workspace-btn').addEventListener('click', () => this.openWorkspace());
        document.getElementById('save-btn').addEventListener('click', () => this.saveCurrentFile());
        document.getElementById('search-btn').addEventListener('click', () => this.focusSearch());
        document.getElementById('terminal-btn').addEventListener('click', () => this.toggleTerminal());
        document.getElementById('git-btn').addEventListener('click', () => this.showGitPanel());
        
        // Sidebar tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // File tree actions
        document.getElementById('refresh-explorer').addEventListener('click', () => this.refreshFileTree());
        document.getElementById('open-folder-btn').addEventListener('click', () => this.openWorkspace());
        
        // Search functionality
        document.getElementById('search-execute').addEventListener('click', () => this.executeSearch());
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.executeSearch();
        });
        
        // Git actions
        document.getElementById('refresh-git').addEventListener('click', () => this.refreshGitStatus());
        
        // Welcome screen actions
        document.getElementById('welcome-open-folder').addEventListener('click', () => this.openWorkspace());
        document.getElementById('welcome-new-file').addEventListener('click', () => this.newFile());
        
        // Modal actions
        document.getElementById('modal-cancel').addEventListener('click', () => this.closeModal());
        document.getElementById('modal-open').addEventListener('click', () => this.confirmOpenWorkspace());
        
        // Terminal actions
        document.getElementById('close-terminal').addEventListener('click', () => this.hideTerminal());
        document.getElementById('terminal-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.executeTerminalCommand();
        });
    }
    
    initializeTerminal() {
        this.terminal = {
            history: [],
            historyIndex: -1,
            currentPath: '~'
        };
    }
    
    // API Communication
    async sendRequest(method, params = {}) {
        try {
            const response = await fetch('/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: method,
                    params: params,
                    id: Date.now()
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error.message || 'Unknown error');
            }
            
            return data.result;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    
    // Workspace Management
    async openWorkspace() {
        document.getElementById('folder-picker-modal').style.display = 'flex';
        document.getElementById('workspace-path').focus();
    }
    
    async confirmOpenWorkspace() {
        const path = document.getElementById('workspace-path').value.trim();
        if (!path) return;
        
        try {
            const result = await this.sendRequest('open_workspace', {
                session_id: this.sessionId,
                workspace_path: path
            });
            
            this.workspacePath = path;
            this.closeModal();
            this.updateWorkspaceUI();
            await this.loadFileTree();
            await this.refreshGitStatus();
            
            console.log('Workspace opened:', result);
        } catch (error) {
            alert('Failed to open workspace: ' + error.message);
        }
    }
    
    closeModal() {
        document.getElementById('folder-picker-modal').style.display = 'none';
        document.getElementById('workspace-path').value = '';
    }
    
    updateWorkspaceUI() {
        document.getElementById('workspace-name').textContent = this.workspacePath.split('/').pop() || this.workspacePath;
        document.querySelector('.no-workspace').style.display = 'none';
        document.getElementById('welcome-screen').style.display = 'none';
    }
    
    // File Tree Management
    async loadFileTree() {
        try {
            const result = await this.sendRequest('get_file_tree', {
                session_id: this.sessionId
            });
            
            this.renderFileTree(result.tree);
        } catch (error) {
            console.error('Failed to load file tree:', error);
        }
    }
    
    renderFileTree(tree) {
        const container = document.getElementById('file-tree');
        container.innerHTML = '';
        
        tree.forEach(item => {
            const element = this.createFileTreeItem(item);
            container.appendChild(element);
        });
    }
    
    createFileTreeItem(item) {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.dataset.path = item.path;
        
        const icon = document.createElement('i');
        if (item.type === 'directory') {
            icon.className = 'fas fa-folder folder-icon';
        } else {
            icon.className = `fas fa-file file-icon ${this.getFileIconClass(item.name)}`;
        }
        
        const name = document.createElement('span');
        name.textContent = item.name;
        
        div.appendChild(icon);
        div.appendChild(name);
        
        // Add click handler
        div.addEventListener('click', () => {
            if (item.type === 'file') {
                this.openFile(item.path);
            } else {
                this.toggleDirectory(div, item);
            }
        });
        
        return div;
    }
    
    getFileIconClass(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const iconMap = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown'
        };
        return iconMap[ext] || 'default';
    }
    
    async toggleDirectory(element, item) {
        const existing = element.nextElementSibling;
        if (existing && existing.classList.contains('directory-children')) {
            existing.remove();
            element.querySelector('i').classList.replace('fa-folder-open', 'fa-folder');
            return;
        }
        
        try {
            const result = await this.sendRequest('get_file_tree', {
                session_id: this.sessionId,
                path: item.path
            });
            
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'directory-children';
            
            result.tree.forEach(child => {
                const childElement = this.createFileTreeItem(child);
                childrenContainer.appendChild(childElement);
            });
            
            element.parentNode.insertBefore(childrenContainer, element.nextSibling);
            element.querySelector('i').classList.replace('fa-folder', 'fa-folder-open');
        } catch (error) {
            console.error('Failed to load directory:', error);
        }
    }
    
    // File Operations
    async openFile(filePath) {
        try {
            const result = await this.sendRequest('open_file', {
                session_id: this.sessionId,
                file_path: filePath
            });
            
            this.currentFile = filePath;
            this.openFiles.set(filePath, {
                content: result.content,
                language: result.language,
                modified: false
            });
            
            this.editor.setValue(result.content);
            this.editor.setOption('mode', this.getEditorMode(result.language));
            
            // Show editor, hide welcome screen
            document.getElementById('welcome-screen').style.display = 'none';
            document.getElementById('editor').style.display = 'block';
            
            // Update UI
            this.updateFileTab(filePath);
            this.updateStatusBar(filePath, result.language);
            
        } catch (error) {
            console.error('Failed to open file:', error);
            alert('Failed to open file: ' + error.message);
        }
    }
    
    async saveCurrentFile() {
        if (!this.currentFile) return;
        
        try {
            const content = this.editor.getValue();
            await this.sendRequest('save_file', {
                session_id: this.sessionId,
                file_path: this.currentFile,
                content: content
            });
            
            // Update file state
            this.openFiles.get(this.currentFile).modified = false;
            this.updateFileTab(this.currentFile);
            
            console.log('File saved:', this.currentFile);
        } catch (error) {
            console.error('Failed to save file:', error);
            alert('Failed to save file: ' + error.message);
        }
    }
    
    newFile() {
        const fileName = prompt('Enter file name:');
        if (!fileName) return;
        
        const filePath = fileName;
        this.currentFile = filePath;
        this.openFiles.set(filePath, {
            content: '',
            language: 'text',
            modified: true,
            isNew: true
        });
        
        this.editor.setValue('');
        this.editor.setOption('mode', 'text');
        
        // Show editor
        document.getElementById('welcome-screen').style.display = 'none';
        document.getElementById('editor').style.display = 'block';
        
        this.updateFileTab(filePath);
        this.updateStatusBar(filePath, 'text');
    }
    
    // UI Updates
    updateFileTab(filePath) {
        const tabBar = document.getElementById('tab-bar');
        const fileName = filePath.split('/').pop();
        const modified = this.openFiles.get(filePath)?.modified || false;
        
        // Remove existing tab if any
        const existingTab = tabBar.querySelector(`[data-path="${filePath}"]`);
        if (existingTab) {
            existingTab.remove();
        }
        
        // Create new tab
        const tab = document.createElement('div');
        tab.className = 'file-tab active';
        tab.dataset.path = filePath;
        tab.innerHTML = `
            <span class="file-tab-name">${fileName}${modified ? ' •' : ''}</span>
            <button class="file-tab-close" onclick="ide.closeFile('${filePath}')">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Remove active class from other tabs
        tabBar.querySelectorAll('.file-tab').forEach(t => t.classList.remove('active'));
        
        tabBar.appendChild(tab);
        
        // Add click handler
        tab.addEventListener('click', (e) => {
            if (!e.target.classList.contains('file-tab-close')) {
                this.switchToFile(filePath);
            }
        });
    }
    
    updateStatusBar(filePath, language) {
        const fileName = filePath.split('/').pop();
        document.getElementById('file-language').textContent = language;
        this.updateCursorPosition();
    }
    
    updateCursorPosition() {
        if (this.editor) {
            const cursor = this.editor.getCursor();
            document.getElementById('cursor-position').textContent = `Ln ${cursor.line + 1}, Col ${cursor.ch + 1}`;
        }
    }
    
    updateConnectionStatus(connected) {
        const status = document.getElementById('connection-status');
        const icon = status.querySelector('i');
        
        if (connected) {
            icon.style.color = 'var(--accent-green)';
            status.innerHTML = '<i class="fas fa-circle"></i> Connected';
        } else {
            icon.style.color = 'var(--accent-red)';
            status.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
        }
    }
    
    markFileAsModified(filePath) {
        const fileInfo = this.openFiles.get(filePath);
        if (fileInfo && !fileInfo.modified) {
            fileInfo.modified = true;
            this.updateFileTab(filePath);
        }
    }
    
    // Tab Management
    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');
    }
    
    // Search Functionality
    async executeSearch() {
        const query = document.getElementById('search-input').value.trim();
        if (!query) return;
        
        try {
            const results = await this.sendRequest('search_workspace', {
                session_id: this.sessionId,
                query: query,
                max_results: 50
            });
            
            this.renderSearchResults(results.results);
        } catch (error) {
            console.error('Search failed:', error);
        }
    }
    
    renderSearchResults(results) {
        const container = document.getElementById('search-results');
        container.innerHTML = '';
        
        if (results.length === 0) {
            container.innerHTML = '<p>No results found</p>';
            return;
        }
        
        results.forEach(result => {
            const div = document.createElement('div');
            div.className = 'search-result';
            div.innerHTML = `
                <div class="search-result-file">${result.file}:${result.line}</div>
                <div class="search-result-content">${result.content}</div>
            `;
            
            div.addEventListener('click', () => {
                this.openFile(result.file);
                // TODO: Jump to line
            });
            
            container.appendChild(div);
        });
    }
    
    focusSearch() {
        this.switchTab('search');
        document.getElementById('search-input').focus();
    }
    
    // Git Integration
    async refreshGitStatus() {
        try {
            const result = await this.sendRequest('get_git_status', {
                session_id: this.sessionId
            });
            
            this.renderGitStatus(result);
        } catch (error) {
            console.error('Failed to get git status:', error);
        }
    }
    
    renderGitStatus(gitData) {
        const container = document.getElementById('git-status');
        
        if (!gitData.is_repo) {
            container.innerHTML = '<div class="no-repo"><p>No git repository found</p></div>';
            return;
        }
        
        container.innerHTML = `
            <div class="git-branch">
                <i class="fas fa-code-branch"></i>
                <span>${gitData.branch}</span>
            </div>
        `;
        
        if (gitData.files && gitData.files.length > 0) {
            gitData.files.forEach(file => {
                const div = document.createElement('div');
                div.className = 'git-file';
                div.innerHTML = `
                    <span class="git-status-icon git-${file.status}">${file.status.charAt(0).toUpperCase()}</span>
                    <span>${file.path}</span>
                `;
                container.appendChild(div);
            });
        }
        
        // Update status bar
        document.getElementById('git-branch').textContent = gitData.branch;
        document.getElementById('git-branch').style.display = 'inline';
    }
    
    showGitPanel() {
        this.switchTab('git');
        this.refreshGitStatus();
    }
    
    // Terminal
    toggleTerminal() {
        const terminal = document.getElementById('terminal-panel');
        if (terminal.style.display === 'none') {
            this.showTerminal();
        } else {
            this.hideTerminal();
        }
    }
    
    showTerminal() {
        document.getElementById('terminal-panel').style.display = 'flex';
        document.getElementById('terminal-input').focus();
    }
    
    hideTerminal() {
        document.getElementById('terminal-panel').style.display = 'none';
    }
    
    async executeTerminalCommand() {
        const input = document.getElementById('terminal-input');
        const command = input.value.trim();
        if (!command) return;
        
        const output = document.getElementById('terminal-output');
        
        // Add command to output
        output.innerHTML += `<div class="terminal-command">$ ${command}</div>`;
        
        try {
            const result = await this.sendRequest('execute_command', {
                session_id: this.sessionId,
                command: command,
                cwd: this.workspacePath
            });
            
            // Add output
            if (result.stdout) {
                output.innerHTML += `<div class="terminal-stdout">${result.stdout}</div>`;
            }
            if (result.stderr) {
                output.innerHTML += `<div class="terminal-stderr">${result.stderr}</div>`;
            }
            
            // Add to history
            this.terminal.history.push(command);
            this.terminal.historyIndex = this.terminal.history.length;
            
        } catch (error) {
            output.innerHTML += `<div class="terminal-error">Error: ${error.message}</div>`;
        }
        
        // Clear input and scroll to bottom
        input.value = '';
        output.scrollTop = output.scrollHeight;
    }
    
    // Utility Methods
    getEditorMode(language) {
        const modeMap = {
            'python': 'python',
            'javascript': 'javascript',
            'typescript': 'javascript',
            'html': 'xml',
            'css': 'css',
            'json': 'application/json',
            'markdown': 'markdown'
        };
        return modeMap[language] || 'text';
    }
    
    closeFile(filePath) {
        const fileInfo = this.openFiles.get(filePath);
        if (fileInfo && fileInfo.modified) {
            if (!confirm('File has unsaved changes. Close anyway?')) {
                return;
            }
        }
        
        this.openFiles.delete(filePath);
        
        // Remove tab
        const tab = document.querySelector(`[data-path="${filePath}"]`);
        if (tab) {
            tab.remove();
        }
        
        // Switch to another file or show welcome screen
        if (this.currentFile === filePath) {
            const remainingFiles = Array.from(this.openFiles.keys());
            if (remainingFiles.length > 0) {
                this.switchToFile(remainingFiles[0]);
            } else {
                this.currentFile = null;
                document.getElementById('editor').style.display = 'none';
                document.getElementById('welcome-screen').style.display = 'flex';
            }
        }
    }
    
    switchToFile(filePath) {
        const fileInfo = this.openFiles.get(filePath);
        if (!fileInfo) return;
        
        this.currentFile = filePath;
        this.editor.setValue(fileInfo.content);
        this.editor.setOption('mode', this.getEditorMode(fileInfo.language));
        
        // Update active tab
        document.querySelectorAll('.file-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-path="${filePath}"]`).classList.add('active');
        
        this.updateStatusBar(filePath, fileInfo.language);
    }
    
    refreshFileTree() {
        if (this.workspacePath) {
            this.loadFileTree();
        }
    }
    
    checkForWorkspace() {
        // Check if there's a workspace path in localStorage or URL params
        const savedWorkspace = localStorage.getItem('ide-workspace');
        if (savedWorkspace) {
            document.getElementById('workspace-path').value = savedWorkspace;
            this.confirmOpenWorkspace();
        }
    }
    
    handleFileChange(data) {
        // Handle real-time file changes from other clients
        console.log('File changed:', data);
        // TODO: Implement collaborative editing
    }
}

// Initialize the IDE when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.ide = new LocalIDE();
});

// Global keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
            case 's':
                e.preventDefault();
                if (window.ide) window.ide.saveCurrentFile();
                break;
            case 'o':
                e.preventDefault();
                if (window.ide) window.ide.openWorkspace();
                break;
            case '`':
                e.preventDefault();
                if (window.ide) window.ide.toggleTerminal();
                break;
        }
    }
});