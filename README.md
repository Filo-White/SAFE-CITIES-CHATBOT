# SAFE-CITIES Chatbot
![ciao](https://github.com/Filo-White/Safe_Cities_Hackathon/blob/main/image/Screenshot%202025-01-11%20175708.png)

A specialized chatbot for urban security and emergency planning, with focus on the SVA (Structural Vulnerability Assessment) framework and cross-border event management in Piazza Transalpina, Gorizia.

## Overview

The SAFE-CITIES Chatbot is an AI-powered assistant designed to help with public event security planning and emergency scenario simulations. It provides expert guidance based on the Structural Vulnerability Assessment (SVA) framework and offers specialized knowledge for the cross-border area of Piazza Transalpina between Gorizia (Italy) and Nova Gorica (Slovenia).

## Features

- **SVA Framework Information**: Access and query detailed information about the SVA framework for safe cities
- **Event Planning Assistance**: Get specific advice for organizing safe events in Piazza Transalpina
- **Emergency Simulation**: Generate realistic emergency scenarios with detailed timelines and response procedures
- **Conversation Memory**: The chatbot remembers previous interactions within a session
- **Document-based Knowledge**: Responses are grounded in documents about the SVA framework and Gorizia
- **Multiple Chat Modes**: Auto-detection of query intent or manual selection of specialized modes
- **Customizable Parameters**: Adjust event type, location, attendance, and severity level for simulations

## Getting Started

### Prerequisites

- Python 3.9 or higher
- OpenAI API key

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Filo-White/SAFE-CITIES-CHATBOT.git
   cd SAFE-CITIES-CHATBOT
   ```

2. Create a virtual environment and activate it:
   ```bash
   # Windows
   python -m venv safe-cities
   safe-cities\Scripts\activate

   # Linux/macOS
   python -m venv safe-cities
   source safe-cities/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key (choose one method):
   - Create a `.api_keys` file in the `config` directory with your API key, OR
   - Set the `OPENAI_API_KEY` environment variable:
     ```bash
     # Windows
     set OPENAI_API_KEY=your-key-here
     
     # Linux/macOS
     export OPENAI_API_KEY=your-key-here
     ```
   - Enter your API key directly in the app's sidebar when prompted

### Running the Chatbot

Launch the Streamlit interface:
```bash
streamlit run app.py
```

The chatbot will be available at `http://localhost:8501` in your web browser.

When you first start the application:

1. You'll need to provide your OpenAI API key if not already configured
2. Select a conversation mode in the sidebar
3. Configure any specific parameters for your chosen mode
4. Start asking questions or requesting simulations

## Project Structure

```
SAFE-CITIES-CHATBOT/
├── app.py                      # Streamlit application
├── assets/
│   └── logo.png                # Logo image for the UI
├── chatbot/
│   ├── __init__.py             # Package exports
│   ├── chatbot_main.py         # Main chatbot class (SafeCitiesChatbot)
│   ├── document_store.py       # Document management and search
│   ├── memory.py               # Conversation memory system
│   ├── openai_client.py        # OpenAI API client
│   └── simulation.py           # Simulation generation engine
├── config/
│   ├── config.yaml             # Main configuration
│   └── prompts.yaml            # Prompt templates
├── docs/
│   ├── sva_framework/          # SVA framework documents
│   └── gorizia_event/          # Documents about Piazza Transalpina
├── templates/
│   └── simulations/            # Simulation scenario templates
│       ├── terrorism.md
│       ├── violence.md
│       ├── weather.md
│       ├── medical.md
│       └── generic.md
├── data/                       # Data storage (created automatically)
│   ├── embeddings.json         # Document embeddings (optional)
│   └── conversations/          # Saved conversations
├── requirements.txt            # Project dependencies
└── README.md                   # This file
```

## Usage

The chatbot has four main conversation modes, which can be selected from the sidebar:

1. **Auto-detect Mode**: The system automatically determines the most appropriate response type based on your query.

2. **SVA Framework Information Mode**: Ask questions about the SVA (Structural Vulnerability Assessment) framework and get responses based on the documentation.

3. **Event Planning Mode**: Get specific advice for organizing events in Piazza Transalpina, considering its cross-border location and security requirements.

4. **Simulation Mode**: Generate detailed simulations of emergency scenarios (terrorism, extreme weather, etc.) with customizable settings for number of participants, event type, and severity.

### Conversation Modes and Settings

Each mode has specific settings available in the sidebar:

- **Event Planning Mode**:
  - Location selection (including Piazza Transalpina or custom locations)
  - Event type (concert, cultural event, festival, etc.)
  - Estimated attendance (100-10,000 people)

- **Simulation Mode**:
  - Scenario type selection (terrorism, weather, medical, violence, etc.)
  - Event severity rating (1-5 scale)
  - Inherits attendance and location settings from Event Planning

### Example Queries

**SVA Framework queries:**
- "What are the key principles of the SVA framework?"
- "How does SVA handle risk assessment for public spaces?"
- "What security measures are recommended by the SVA framework?"

**Event Planning queries:**
- "What security measures are needed for a concert with 3000 people in Piazza Transalpina?"
- "How should emergency exits be arranged in Piazza Transalpina?"
- "What coordination is required between Italian and Slovenian authorities for an event?"

**Simulation queries:**
- "Simulate a terrorist attack during a concert in Piazza Transalpina"
- "Create a scenario for a severe weather emergency during an event"
- "Simulate a medical emergency with 5000 attendees"

### Conversation Management

The chatbot interface allows you to:
- Save your conversation for future reference (click "Save Conversation" in sidebar)
- Reset the chat history while maintaining your settings (click "Reset Chat" in sidebar)

## Configuration

You can customize the chatbot by editing the configuration files:

- `config/config.yaml`: Main settings for models, paths, and default parameters
- `config/prompts.yaml`: Prompt templates for different query types

### Key Configuration Options

In `config/config.yaml`:

```yaml
# Model configuration
models:
  chat_model: "gpt-4o"  # Choose your preferred OpenAI model
  temperature: 0.7     # Adjust for more deterministic or creative responses
  max_tokens: 2000     # Maximum response length

# Simulation parameters
simulation:
  default_participants: 2000  # Default number of participants
  default_severity: 3         # Default severity level (1-5)
  available_scenarios:
    - "terrorism"
    - "violence"
    - "weather"
    - "medical_emergency"
    - "generic"
    # Add more scenarios as needed

# API key configuration
api_keys:
  openai: ""  # Can be left empty to use other methods
  api_key_file: "config/.api_keys"  # File to save API keys
  remember_key: false  # Whether to save API key for future sessions
```

## Adding Documents

To add your own documents:

1. Place SVA framework documents in the `docs/sva_framework/` directory
2. Place Gorizia/Piazza Transalpina documents in the `docs/gorizia_event/` directory

The chatbot supports PDF and markdown files (`.pdf`, `.md`).

## Adding New Simulation Templates

To add a new simulation scenario type:

1. Create a Markdown template file in `templates/simulations/` (e.g., `earthquake.md`)
2. Follow the structure of existing templates
3. Add the scenario name to the `available_scenarios` list in `config/config.yaml`

## License

This project is part of the SAFE-CITIES initiative.

## Acknowledgments

- SVA Framework documentation
- OpenAI for API access
- Streamlit for the web interface
