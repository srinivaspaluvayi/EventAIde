# EventAIde (Event + AI + Aide)
EventAIde is a chatbot that helps you discover all available events and explore different genres in any city. It's the perfect companion for staying updated on what's happening locally or in new places when you travel—making it easy to find concerts, sports, festivals, and more, wherever you are.

## Tech Stack

• **Python** - Core programming language (3.11)
• **Conda** - Environment and dependency management
• **Jupyter Notebook** - Interactive development environment
• **Gradio** - Web interface for the chatbot application
• **Ticketmaster API** - Real-time event data integration
• **OpenAI** - AI/LLM integration for chatbot functionality
• **Pandas** - Data manipulation and analysis
• **NumPy** - Numerical computing
• **Scikit-learn** - Machine learning capabilities
• **Requests** - HTTP library for API calls
• **BeautifulSoup4** - Web scraping and HTML parsing
• **Gensim** - Natural language processing and topic modeling
• **Matplotlib** - Data visualization
• **Python-dotenv** - Environment variable management

## Setup
### 1. Clone the repository
```bash
git clone https://github.com/srinivaspaluvayi/EventAIde.git
cd EventAIde
```
### 2. Install dependencies
This project uses **Conda** for environment management.
```bash
conda env create -f environment.yaml
conda activate eventaide
```
*If you use pip, check `environment.yaml` for dependencies and install them manually.*
### 3. Configure Environment Variables
- Create a `.env` file in the root directory.
- Add your Ticketmaster API key:
  ```
  TICKETMASTER_API_KEY=your_api_key_here
  ```

**Notes:**
- It's important to run the initialization notebooks first to ensure all required data/preprocessing is complete before starting the main application.
- If you add new notebooks or change file names, update these steps accordingly.
- Make sure you have working API keys and all dependencies installed per `environment.yaml`.
