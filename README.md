# 🧠 CognitiveLattice: Intelligent AI Agent Framework

**CognitiveLattice** is a sophisticated AI agent framework that combines **intelligent tool orchestration**, **persistent memory**, and **context-aware processing** to create truly adaptive and capable AI assistants.

Rather than being just another LLM wrapper, CognitiveLattice implements a **cognitive architecture** that enables AI agents to:
- Remember where they've been, what they're doing, and where they're going
- Intelligently select and coordinate tools based on context
- Maintain persistent session memory across interactions
- Process documents with enhanced RAG (Retrieval-Augmented Generation)
- Execute complex multi-step tasks with adaptive planning

---
## 🎬 Live Demo
Watch the CognitiveLattice agent in action. This is not a scripted demo. It's a live demonstration of the Cognitive Lattice enabling a series of stateless API calls to be chained into a single, successful, multi-step task. The agent's ability to select the right tool and recall its own actions is entirely dynamic.
![CognitiveLattice1](https://github.com/user-attachments/assets/3b2bf69c-04d4-4714-91a6-b593bb1a1334)

---
## 🌟 Key Features

### 🧠 **Cognitive Lattice** - Persistent Memory & Session Management
- **Hybrid State Management**: Active task tracking + comprehensive event logging
- **Cross-Session Persistence**: Session files can be loaded/resumed (user-selectable lattice loading coming soon)
- **Dynamic Context Extraction**: Automatically builds relevant context from session history
- **Task Progress Tracking**: Monitors multi-step task completion with step-by-step state
- **Model-Agnostic Memory**: Lattice data works with any LLM - switch models without losing context

### 🔧 **Intelligent Tool Management**
- **LLM-Driven Tool Selection**: Uses AI reasoning to choose appropriate tools
- **Generic Tool Architecture**: Works with any tool, not hardcoded for specific domains
- **Contextual Parameter Extraction**: Automatically extracts tool parameters from conversation
- **Tool Result Integration**: Seamlessly integrates tool outputs into conversations

### 📋 **Structured Task Execution**
- **Multi-Step Planning**: Creates and executes complex task plans
- **Adaptive Step Management**: Handles user input at any step, allows backtracking
- **Task Lock System**: Maintains focus during active task execution
- **Progress Summarization**: Provides comprehensive "what have we done so far" summaries

### 📄 **Advanced Document Processing**
- **Enhanced RAG System**: Sophisticated document analysis with external AI enhancement
- **Multi-Format Support**: Handles various document types and structures
- **Semantic Search**: Intelligent document querying with context awareness
- **Session-Based RAG Storage**: Avoids JSON serialization issues with in-memory management

### 🌐 **External API Integration**
- **OpenAI Integration**: Leverages GPT models for enhanced reasoning
- **Modular API Client**: Easy to extend with other AI services
- **Error Handling & Fallbacks**: Graceful degradation when external services unavailable
- **Token-Conscious Processing**: Optimizes token usage while maintaining capability

### 🔒 **Privacy & Security Architecture (Airgap Design)**
- **Document Airgapping**: Process documents locally without exposing content to external LLMs
- **Encryption-Ready**: Built-in encoding/decoding system supports encrypted document transmission
- **Lattice Confidentiality**: Session data can be encrypted before storage (implementation pending)
- **Model Independence**: Switch between LLMs without exposing previous reasoning or context
- **Future-Proof Privacy**: Maintains user confidentiality as AI models evolve

---

## 🏗️ Architecture Overview

```
CognitiveLattice Framework
├── 🧠 Cognitive Lattice (core/cognitive_lattice.py)
│   ├── Session Management & Persistence
│   ├── Active Task State Tracking
│   └── Event Log & History
├── 🔧 Tool Manager (core/tool_manager.py)
│   ├── Dynamic Tool Loading & Selection
│   ├── LLM-Driven Tool Reasoning
│   └── Generic Tool Parameter Extraction
├── 🌐 External API Client (core/external_api_client.py)
│   ├── OpenAI Integration
│   ├── Task Planning & Execution
│   └── Document Analysis Enhancement
├── 📄 Advanced RAG System (core/CognitiveLattice_advanced_rag.py)
│   ├── Document Processing & Chunking
│   ├── Semantic Search & Retrieval
│   └── Session-Based Storage Management
└── 🎯 Interactive Main Agent (main.py)
    ├── Intent Detection & Routing
    ├── Task Lock & Context Management
    └── Multi-Modal Response Handling
```

---

## 🔧 Available Tools

CognitiveLattice includes a modular tool system that currently supports:

### 📄 **Document Processing Tools**
- `document_processor`: Process and analyze new documents
- `document_query`: Query already processed documents

### ✈️ **Travel Planning Tools** (Example Domain)
- `flight_planner`: Search and compare flight options
- `flight_selector`: Select specific flights from options
- `hotel_planner`: Find accommodation options
- `hotel_selector`: Book specific hotels
- `restaurant_planner`: Discover dining options
- `restaurant_selector`: Make restaurant reservations

**Note**: The travel tools are just one example domain. The framework is designed to work with **any tools** - document analysis, project management, data processing, etc.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- **Local LLaMA Server** (for intent detection and local processing)
- OpenAI API key (optional, for enhanced capabilities)

### Installation
```bash
# Clone the repository
git clone https://github.com/Sean-V-Dev/CognitiveLattice-Framework.git
cd CognitiveLattice-Framework

# Install dependencies
pip install -r requirements.txt

# Set up LLaMA Server (Required)
# Download and run a local LLaMA model server
# Example using llama.cpp or similar:
# ./llama-server --model your-model.gguf --port 8080

# Set up your OpenAI API key (optional)
# Create a .env file or set environment variable
export OPENAI_API_KEY="your-api-key-here"
```

### Running CognitiveLattice
```bash
# 1. Start your LLaMA server first
./llama-server --model your-model.gguf --port 8080

# 2. Then start CognitiveLattice
python main.py
```

### Example Interactions
```
🧠 CognitiveLattice Interactive Agent
Enter your request: Process my research document

🔧 Tool detected: document_processor
📄 Document processed successfully! Ready for analysis.

Your request: What are the key findings in the document?

🔧 Tool detected: document_query
📊 Based on your document, the key findings include...

Your request: Help me plan a research presentation

📋 Task plan created with 5 steps:
   1. Outline presentation structure
   2. Extract key data points
   3. Create visual aids
   4. Prepare speaker notes
   5. Schedule practice sessions

🎯 Ready to execute step 1: Outline presentation structure
```

---

## 🎯 Core Design Philosophy

### **Context is Intelligence**
CognitiveLattice treats context as the foundation of intelligence. The system:
- Never forgets what happened in a session
- Builds dynamic context from actual interactions
- Provides comprehensive task summaries on demand
- Adapts tool selection based on session history

### **Privacy Through Airgapping**
CognitiveLattice implements a unique airgap architecture that solves critical AI confidentiality problems:
- **Document Privacy**: Process sensitive documents locally without external LLM exposure
- **Reasoning Isolation**: Previous model reasoning doesn't contaminate new models
- **Model Portability**: Switch between any LLM (internal, external, new releases) while preserving all work
- **Future-Proof Security**: Protects against evolving AI privacy concerns

### **Generic, Not Hardcoded**
Unlike frameworks that hardcode specific use cases, CognitiveLattice:
- Works with any domain (travel, documents, projects, etc.)
- Detects tool needs dynamically based on conversation context
- Extracts parameters generically from any tool result structure
- Scales to new tools without code changes

### **AI-First Tool Selection**
Rather than keyword matching or rigid rules, CognitiveLattice:
- Uses LLM reasoning to select appropriate tools
- Considers full conversation context for tool decisions
- Adapts to user intent and task progression
- Falls back gracefully when external AI unavailable

### **Persistent Memory Architecture**
CognitiveLattice implements a sophisticated memory system that:
- Maintains active task state as single source of truth
- Logs all events for comprehensive audit trail
- Enables cross-session context restoration (file-based loading coming soon)
- Supports complex multi-step task management

---

## 📁 Project Structure

```
CognitiveLattice/
├── main.py                      # Main interactive agent
├── core/                        # Core framework components
│   ├── cognitive_lattice.py     # Memory & session management
│   ├── tool_manager.py          # Tool orchestration
│   ├── external_api_client.py   # AI service integration
│   ├── CognitiveLattice_advanced_rag.py # Document processing
│   └── rag_manager.py           # RAG system management
├── tools/                       # Modular tool implementations
│   ├── document_processor_tool.py
│   ├── flight_planner_tool.py
│   └── [other tools...]
├── applications/                # Domain-specific applications
│   ├── document_analysis/
│   └── demos/
├── config/                      # Configuration files
├── data/                        # Document storage
├── cache/                       # Processing cache
└── tests/                       # Test suites
```

---

## 🔮 Advanced Capabilities

### **Task Continuity**
```
Session 1:
User: "Help me plan a vacation to Paris"
Agent: Creates 6-step plan, completes steps 1-3

Session 2 (later):
User: "Continue with my Paris trip planning"
Agent: Remembers context, resumes at step 4
```

### **Cross-Tool Intelligence**
```
User: "Process this contract and plan my review meeting"
Agent: 
1. Uses document_processor for contract analysis
2. Extracts key dates and stakeholders
3. Uses calendar_tool to schedule meetings
4. Provides integrated summary with all context
```

### **Model Migration & Future-Proofing**
```
Company Problem: New AI model released, but all previous work is trapped in old model
CognitiveLattice Solution:
1. Export lattice with complete task history and context
2. Point new model at existing lattice file
3. New model has full context without contamination from old model's reasoning
4. Zero work lost, seamless AI evolution
```

### **Enterprise Privacy Protection**
```
Enterprise Need: Process sensitive documents with AI assistance while maintaining confidentiality
CognitiveLattice Solution:
1. Documents processed locally with encryption
2. Only encrypted/encoded summaries sent to external LLMs
3. Lattice memory can be encrypted at rest
4. Full audit trail without exposing raw content
```

---

## 🛠️ Extending CognitiveLattice

### Adding New Tools
1. Create tool file in `tools/` directory
2. Implement standard tool interface
3. Tool manager automatically discovers and integrates
4. No code changes needed in core framework

### Custom Applications
1. Create application directory under `applications/`
2. Leverage core components (lattice, tool manager, RAG)
3. Implement domain-specific logic and workflows

### Integration with Other AI Services
1. Extend `external_api_client.py`
2. Add new service configurations
3. Maintain fallback compatibility

---

## 📊 Recent Achievements

- ✅ **Dynamic Context System**: Eliminated hardcoded assumptions, now works for any task type
- ✅ **LLM-Driven Tool Selection**: Intelligent tool selection based on conversation context
- ✅ **Session Persistence**: Session files maintain context (user-selectable loading in development)
- ✅ **Generic Tool Architecture**: Tools work for any domain, not just travel planning
- ✅ **Enhanced RAG Integration**: Sophisticated document processing with external AI enhancement
- ✅ **Task Progress Summarization**: Comprehensive "what have we done" capabilities
- ✅ **Airgap Architecture**: Privacy-first design with encryption-ready document processing
- ✅ **Model Agnostic Memory**: Lattice works with any LLM - switch models without losing work

---

## 🌟 Why CognitiveLattice?

**For Developers:**
- Clean, modular architecture that's easy to extend
- No vendor lock-in - works with multiple AI services
- Comprehensive logging and debugging capabilities
- Generic patterns that scale to any domain

**For Users:**
- Remembers context and maintains conversation continuity
- Handles complex multi-step tasks intelligently
- Provides transparent progress tracking
- Adapts to your working style and preferences

**For Organizations:**
- Scalable framework for building domain-specific AI agents
- **Model Migration Protection**: Switch AI providers without losing work or context
- **Privacy-First Architecture**: Process sensitive data without external exposure
- Tool modularity allows gradual capability expansion
- Context awareness reduces training overhead
- **Future-Proof Investment**: Lattice data works with any current or future AI model

---

## 🚧 Roadmap

### Short Term
- [ ] User-selectable lattice loading (resume previous sessions)
- [ ] Enhanced lattice encryption for sensitive data
- [ ] Enhanced tool parameter validation
- [ ] Improved error handling and recovery
- [ ] Performance optimization for large sessions
- [ ] Additional document format support

### Medium Term
- [ ] Full lattice encryption and security hardening
- [ ] Model marketplace integration (easily switch between AI providers)
- [ ] Multi-user session management
- [ ] Advanced tool chaining and workflows
- [ ] Integration with more AI services
- [ ] Web interface and API endpoints

### Long Term
- [ ] Distributed agent coordination
- [ ] Machine learning-enhanced tool selection
- [ ] Enterprise security and compliance features
- [ ] Marketplace for community-contributed tools



## 👋 About

CognitiveLattice was created by Sean VanWinkle. I started this entire thing as just a side project to attempt to add to my resume to help me find a job. I'm currently, July 2025, still a student in university for software engineering. It started as just a way to break down documents to help the LLM ingest better because of a problem I had when I tried to give three different LLMs a 75 question quiz and asked it to help me study. After question 25 they all drifted and started to hallucinate. I thought I could help fix that problem, and that is when CognitiveLattice was born. But the project grew from there in to the architecture you see above you. I hope my project will be useful to people out there and advance the world of AI.



---

## 📄 License

MIT License - Feel free to use, modify, and distribute. See [LICENSE](LICENSE) for details.

---

## 🌐 Contact & Links

- **GitHub**: [CognitiveLattice-Framework](https://github.com/Sean-V-Dev/CognitiveLattice-Framework)
- **Issues**: [GitHub Issues](https://github.com/Sean-V-Dev/CognitiveLattice-Framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Sean-V-Dev/CognitiveLattice-Framework/discussions)

---

*CognitiveLattice: Building AI agents that remember, reason, and evolve with you.*
