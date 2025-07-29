# TokenSight Framework

**Advanced Document Processing with Cognitive Lattice Architecture**

TokenSight is a sophisticated document processing framework that combines steganographic encoding, multi-modal analysis, and intelligent routing with a persistent "cognitive lattice" memory system for complex task execution.

## 🏗️ Architecture Overview

The framework operates on multiple interconnected layers:

1. **Core Processing Pipeline**: Document ingestion → Steganographic encoding → Chunking → Analysis
2. **Cognitive Lattice**: Persistent session memory for stepwise task execution
3. **Intent-Based Routing**: Smart classification and routing of user queries
4. **Multi-RAG Systems**: Specialized retrieval systems for different document types
5. **External API Integration**: Enhanced analysis through external LLMs

## 📁 Core Components

### 🧠 Cognitive Architecture (`main.py`)

**Primary Entry Point** - Orchestrates the entire system with intelligent session management.

**Key Classes:**
- `CognitiveLattice`: Persistent memory system that stores session nodes for stepwise task execution
- `SessionManager`: Manages lattice persistence and session file operations

**Intent-Based Routing Logic:**
```
User Query → Intent Detection → Route to Handler:
├── Chat/Conversation → Direct External API
├── Simple Query → Direct External API  
├── Document Analysis → Advanced RAG Pipeline
└── Structured Task → Cognitive Lattice (stepwise execution)
```

**Routing Conditions:**
- **Chat**: `intent=["chat", "simple", "conversation"]`
- **Simple Query**: `intent="query" AND action=["query", "question", "ask", "simple_question_answering"]`
- **Document Analysis**: `intent=["analysis", "summarize", "broad"]` OR `intent="query" AND action=["extract", "analyze", "review"]`
- **Structured Task**: `intent=["task", "structured_task", "plan", "planner"]` OR `intent="query" AND action=["plan", "planning", "step_by_step", "itinerary"]`

### 🔐 Steganographic Processing

**Text Encoder** (`encoder/text_to_image.py`)
- Converts text to encrypted pixel data using dictionary mapping
- Each word/token maps to unique RGB values
- Preserves formatting (newlines, spaces, punctuation)

**Text Decoder** (`decoder/image_to_text.py`)  
- Reverses the encoding process from pixel data back to text
- Uses the same dictionary for decryption

**Dictionary Management** (`utils/dictionary_manager.py`)
- Dynamic dictionary expansion for new tokens
- RGB color generation and collision prevention
- Persistent storage in `config/dictionary.json`

### 📄 Document Processing Pipeline

**File Handler** (`file_handler.py`)
- Multi-format support (PDF, TXT) with encoding fallbacks
- PDF text extraction using `pdfplumber`
- Text sanitization and line processing

**Text Processor** (`text_processor.py`)
- Intelligent paragraph extraction and sentence splitting
- Flexible chunking with token limits and overflow handling
- Context-aware chunk boundaries

**Page Extractor** (`page_extractor.py`)
- PDF page-to-image conversion for visual content
- Visual keyword extraction and metadata generation
- Integration with multimodal processing pipeline

### 🤖 AI Integration Layer

**LLaMA Client** (`llama_client.py`)
- Local LLM interface for intent detection and content analysis  
- Template-based summarization by document type
- Content classification and key fact extraction

**External API Client** (`external_api_client.py`)
- OpenAI GPT integration with date-aware context
- Direct query handling for simple requests
- Chunk analysis with JSON response formatting
- Analysis summarization across multiple chunks

### 🔍 Advanced RAG Systems

**TokenSight Advanced RAG** (`tokensight_advanced_rag.py`)
- Integration layer between bidirectional RAG and external APIs
- Document chunk processing with audit capabilities
- Safety thresholds and risk assessment

**Bidirectional RAG** (`bidirectional_rag.py`)
- Multi-specialized embedding models for different domains
- Document type detection and intelligent routing
- Safety auditing with hallucination detection

**Integrated JSON RAG** (`integrated_json_rag.py`)
- Massive JSON file processing with streaming support
- Domain-specific model selection (medical, technical, scientific)
- Semantic search with specialized embeddings

### 💾 Memory & Storage

**Memory Manager** (`memory_manager.py`)
- Semantic and literal search across processed chunks
- Integration with embedding models for intelligent retrieval
- Legacy compatibility with simple keyword search

**Session Persistence**
- Cognitive lattice state saved as JSON files
- Interactive session tracking with query history
- Audit trail for all processing steps

## 🔄 Data Flow

### 1. Document Ingestion
```
Raw Document → File Handler → Text Lines → Paragraph Extraction → Chunk Creation
```

### 2. Steganographic Processing
```
Text Chunks → Dictionary Expansion → RGB Encoding → Image Generation → Image Decoding → Verified Text
```

### 3. Analysis Pipeline
```
Verified Chunks → Content Classification → RAG System Selection → Embedding Generation → Vector Storage
```

### 4. Query Processing
```
User Query → Intent Detection → Route Selection → Processing (Direct API | RAG | Task Planning) → Response
```

### 5. Cognitive Lattice (Structured Tasks)
```
Complex Query → Task Planning → Step Decomposition → Sequential Execution → Progress Tracking → Completion
```

## 🎯 Specialized Components

### FDA/Medical Processing
- **FDA JSON Integration** (`fda_json_integration.py`): Specialized processor for FDA drug label data
- **Massive JSON Processor** (`massive_json_processor.py`): Streaming processor for multi-gigabyte datasets
- **Search FDA** (`search_fda.py`): Medical document search interface with specialized embeddings

### Testing & Validation
- **Advanced RAG Tests** (`test_advanced_rag.py`): Integration testing for RAG systems
- **Specialized Model Tests** (`test_specialized_models.py`): Domain-specific embedding validation
- **Pediatric Query Tests** (`test_pediatric_query.py`): Medical query accuracy testing

### Utilities & Analysis
- **Cost Analysis** (`cost_analysis.py`): API usage and token consumption tracking
- **Usage Checker** (`check_usage.py`): Token usage analysis across processing runs
- **Cleanup Analysis** (`cleanup_analysis.py`): Data maintenance and optimization
- **Visual Extraction** (`extract_all_visuals.py`): PDF visual content extraction

## 🧩 Component Interconnections

### Primary Data Flow
1. **Document Input** → `file_handler.py` → `text_processor.py`
2. **Steganographic Layer** → `encoder/` → `decoder/` → `utils/dictionary_manager.py`
3. **AI Analysis** → `llama_client.py` → `external_api_client.py`
4. **Cognitive Processing** → `main.py` (CognitiveLattice) → `tokensight_advanced_rag.py`
5. **Specialized RAG** → `bidirectional_rag.py` → `integrated_json_rag.py`

### Session Management Flow
1. **Session Start** → `SessionManager` creates cognitive lattice
2. **Query Processing** → Intent detection → Route to appropriate handler
3. **State Persistence** → Lattice nodes saved to JSON files
4. **Task Execution** → Stepwise processing with external API integration

### Memory & Search Integration
1. **Chunk Storage** → `memory_manager.py` maintains searchable index
2. **Semantic Search** → Embedding models provide similarity search
3. **Query Routing** → Intent-based selection of processing pipeline
4. **Response Generation** → Combination of local and external AI analysis

## 🚀 Key Features

- **Steganographic Security**: Text encrypted as pixel data for secure processing
- **Cognitive Persistence**: Human-like stepwise task execution with memory
- **Intent Classification**: Smart routing based on query complexity and type
- **Multi-Modal Support**: Text, visual, and structured data processing
- **Specialized RAG**: Domain-specific embeddings for medical, technical, and scientific content
- **Scalable Processing**: Streaming support for massive datasets (multi-GB JSON files)
- **Audit Trail**: Complete processing history with safety validation
- **External API Integration**: Enhanced analysis through GPT models with cost tracking

## 🔧 Configuration

- **Multimodal Settings**: `config/multimodal_config.json`
- **Dictionary Storage**: `config/dictionary.json` 
- **API Keys**: Environment variables (OPENAI_API_KEY)
- **Processing Parameters**: Configurable chunk sizes, token limits, and thresholds

## 📊 Current Status

The framework demonstrates successful integration of:
- ✅ Cognitive lattice with stepwise task execution
- ✅ Intent-based routing for different query types  
- ✅ Date-aware external API integration
- ✅ Multi-domain RAG system with specialized embeddings
- ✅ Massive dataset processing capabilities
- ✅ Session persistence and audit trails

## 🎯 Use Cases

1. **Document Analysis**: Complex technical document processing with visual elements
2. **Medical Research**: FDA drug data analysis with specialized medical embeddings
3. **Structured Planning**: Multi-step task execution (trip planning, research workflows)
4. **Knowledge Management**: Persistent session memory across complex workflows
5. **Secure Processing**: Steganographic encoding for sensitive document handling

---

## 🔍 Core Design Philosophy

TokenSight addresses fundamental challenges in LLM processing:

> 🎯 *Watch every token. Limit waste. Maximize meaning.*

**Key Principles:**
- **Surgical Input Management**: Only relevant data reaches large models
- **Steganographic Security**: Sensitive content encrypted during processing  
- **Cognitive Persistence**: Human-like memory for complex multi-step tasks
- **Intent-Aware Routing**: Smart processing pipeline selection
- **Audit-First Design**: Complete traceability of all processing steps

**Benefits:**
- ✅ Reduced hallucination through filtered input
- ✅ Enhanced privacy via encryption layer
- ✅ Lower token consumption through smart routing
- ✅ Persistent task memory across sessions
- ✅ Specialized processing for different domains

---

## 🛠️ Recent Milestones

- ✅ **Cognitive Lattice Implementation**: Persistent stepwise task execution system
- ✅ **Intent-Based Routing**: Smart query classification and processing pipeline selection
- ✅ **Date-Aware External APIs**: Context-aware GPT integration with current date
- ✅ **Multi-Domain RAG Systems**: Specialized embeddings for medical, technical, and scientific content
- ✅ **Massive Dataset Processing**: Streaming support for multi-gigabyte JSON files (FDA data)
- ✅ **Session Persistence**: Complete audit trail with cognitive lattice state management

---

## 👋 About the Builder

Hi, I'm Sean — a systems architect with a passion for frictionless design. TokenSight wasn't born just to process documents — it was built to solve the deeper challenge of creating AI systems that think and remember like humans do, with persistent memory across complex multi-step tasks.

The cognitive lattice concept emerged from observing how humans naturally break down complex problems into manageable steps, maintaining context and progress across time. This framework makes that approach available to AI systems.

---

## 📜 License

MIT — fork freely, contribute generously, break things carefully.

---

## 🌐 Contact

LinkedIn coming soon.  
Feel free to open issues or drop feedback directly in the repo.

---

*TokenSight Framework - Combining human-like cognitive persistence with advanced AI processing capabilities*
