# Local IDE - Cursor Alternative

A fully functional local IDE alternative to Cursor that runs in your browser. This project transforms the existing MCP server into a comprehensive development environment with all the features you'd expect from a modern IDE.

## 🚀 Features

### Core IDE Features
- **File Management**: Complete file tree browsing, opening, editing, and saving
- **Code Editor**: Syntax highlighting for multiple languages with CodeMirror
- **Real-time Collaboration**: WebSocket-based file synchronization
- **Multi-tab Interface**: Open and manage multiple files simultaneously
- **Project Workspace**: Full workspace management with project analysis

### Code Intelligence
- **Smart Completions**: AI-powered and static analysis code completion
- **Language Support**: Python, JavaScript, TypeScript, CSS, HTML, and more
- **Symbol Search**: Project-wide symbol and dependency analysis
- **AST-based Analysis**: Deep code understanding using Tree-sitter

### Git Integration
- **Git Status**: Real-time git status monitoring
- **Branch Display**: Current branch information in status bar
- **File Change Tracking**: Visual indicators for modified files

### Development Tools
- **Integrated Terminal**: Execute commands directly from the IDE
- **Workspace Search**: Full-text search across all project files
- **LSP Integration**: Language Server Protocol support for enhanced features
- **Project Monitoring**: Real-time file watching and incremental indexing

### AI Assistance
- **AI Chat**: Built-in AI assistant panel for code help
- **Code Completions**: Multiple completion sources including AI
- **Smart Suggestions**: Context-aware code recommendations

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11+
- Git (for version control features)
- Node.js (optional, for additional language servers)

### Quick Start

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd LocalContextMCP
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Start the IDE Server**:
   ```bash
   python ide_server.py
   ```

3. **Access the IDE**:
   Open your browser and navigate to `http://localhost:3000`

### Advanced Configuration

#### Environment Variables
- `IDE_SERVER_HOST`: Server host (default: 0.0.0.0)
- `IDE_SERVER_PORT`: Server port (default: 3000)
- `DEBUG`: Enable debug mode (default: false)

#### Database Configuration (Optional)
For enhanced features, configure PostgreSQL:
```bash
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=mcp_memory
export PGUSER=postgres
export PGPASSWORD=your_password
```

## 🎯 Usage Guide

### Opening a Workspace
1. Click "Open Workspace" in the top menu or welcome screen
2. Enter the path to your project directory
3. The IDE will automatically analyze the project structure

### File Operations
- **Open File**: Click on files in the Explorer panel
- **Save File**: Ctrl+S or click the Save button
- **New File**: Click the New File button
- **Close Tab**: Click the X on file tabs

### Code Features
- **Auto-completion**: Start typing and press Ctrl+Space
- **Search**: Use the Search panel or Ctrl+F
- **Command Execution**: Use the integrated terminal

### Git Operations  
- **View Status**: Check the Git panel for file changes
- **Branch Info**: See current branch in the status bar

## 🏗️ Architecture

### Backend Components
- **Flask Server**: Core HTTP server with JSON-RPC API
- **SocketIO**: Real-time WebSocket communication
- **Language Servers**: LSP integration for code intelligence
- **Project Manager**: File watching and project analysis
- **Code Intelligence**: AST parsing and symbol extraction

### Frontend Components
- **CodeMirror**: Advanced code editor with syntax highlighting
- **Modern UI**: VS Code-inspired interface with dark theme
- **Real-time Updates**: Live collaboration features
- **Responsive Design**: Works on desktop and mobile

### Data Flow
```
Browser ↔ WebSocket/HTTP ↔ Flask Server ↔ Language Servers
                                     ↓
                            Code Intelligence Engine
                                     ↓
                              File System & Git
```

## 🔧 API Reference

### Core IDE Methods

#### Session Management
- `create_session()`: Create new IDE session
- `open_workspace(session_id, workspace_path)`: Open project workspace

#### File Operations
- `get_file_tree(session_id, path?)`: Get project file structure
- `open_file(session_id, file_path)`: Open and read file
- `save_file(session_id, file_path, content)`: Save file content

#### Code Intelligence
- `get_completions(session_id, file_path, line, column, content)`: Get code completions
- `search_workspace(session_id, query, file_types?, max_results?)`: Search project files

#### Development Tools
- `execute_command(session_id, command, cwd?)`: Execute terminal commands
- `get_git_status(session_id)`: Get git repository status

### WebSocket Events
- `connect`: Client connection established
- `file_change`: Real-time file content updates
- `file_updated`: Broadcast file changes to other clients

## 🎨 Customization

### Themes
The IDE uses a VS Code-inspired dark theme with CSS variables for easy customization:
```css
:root {
    --bg-primary: #1e1e1e;
    --bg-secondary: #252526;
    --text-primary: #cccccc;
    --accent: #007acc;
}
```

### Adding Language Support
1. Add new language parsers to `language_support.py`
2. Configure LSP servers in `LanguageServerManager`
3. Add syntax highlighting modes to the frontend

### Extending Features
- Add new API endpoints in `ide_server.py`
- Implement frontend components in `static/js/app.js`
- Create additional panels in the sidebar

## 🔒 Security

### Command Execution
- Whitelist of allowed commands for security
- Commands executed in workspace context only
- 30-second timeout for all commands

### File Access
- Restricted to workspace directory
- Input validation and sanitization
- Safe file encoding handling

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

Test specific components:
```bash
python test_server.py
python test_enhanced_features.py
```

## 📊 Monitoring

### Health Check
Monitor server status at `http://localhost:3000/health`

### Metrics
- Active sessions count
- LSP server status
- Feature availability
- Performance metrics

## 🚨 Troubleshooting

### Common Issues

1. **Server won't start**:
   - Check Python version (3.11+ required)
   - Verify all dependencies installed
   - Check port 3000 availability

2. **File operations fail**:
   - Verify workspace permissions
   - Check file encoding (UTF-8 preferred)
   - Ensure sufficient disk space

3. **Git features not working**:
   - Verify git is installed and in PATH
   - Check repository is properly initialized
   - Verify workspace is a git repository

4. **Code completion not working**:
   - Check LSP servers are installed
   - Verify language detection
   - Check network connectivity for AI features

### Debug Mode
Enable debug mode for detailed logging:
```bash
DEBUG=true python ide_server.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- CodeMirror for the excellent code editor
- Flask and SocketIO for the robust backend
- Tree-sitter for advanced language parsing
- The MCP protocol for inspiration

---

**Ready to code? Start your local IDE server and experience the power of a truly local development environment!** 🎉