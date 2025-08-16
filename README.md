# EventAIde (Event + AI + Aide)

EventAIde is a chatbot that helps you discover all available events and explore different genres in any city. It's the perfect companion for staying updated on what's happening locally or in new places when you travel—making it easy to find concerts, sports, festivals, and more, wherever you are.

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

## Run Instructions

1. **Run Data/API Initialization Notebooks First**

   - Open and execute all cells in `events_api.ipynb`:

     ```bash
     jupyter lab events_api.ipynb
     ```

   - *If you have another required notebook for initialization, such as `events_genres.ipynb`, add this here as well:*

     ```bash
     jupyter lab events_genres.ipynb
     ```

2. **Run the Main Application Notebook**

   - After initializing required files, run the app:

     ```bash
     jupyter lab app.ipynb
     ```

   - Or, if the app is runnable with Gradio via a Python script:

     ```bash
     python -m gradio app.ipynb
     ```

**Notes:**
- It's important to run the initialization notebooks first to ensure all required data/preprocessing is complete before starting the main application.
- If you add new notebooks or change file names, update these steps accordingly.
- Make sure you have working API keys and all dependencies installed per `environment.yaml`.
