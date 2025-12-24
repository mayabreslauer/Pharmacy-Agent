# Pharmacy-Agent 
This is an AI-powered pharmacist assistant for a retail pharmacy chain. The agent will serve customers through chat, using data from the pharmacy’s internal systems. It will help you to get information about medications, prescriptions and stock availability.
For every request the agent will use a tool, except requests he can't do.

## Features - Tools
* Get information about medications
* Check if the medication available in stock
* Get information about dosage and usage of medications
* Check your active prescriptions
* Check your medications alergies - only when making a reservation, to avoid recommendations
* Make a reservation for a chosen medication

## Requirements
* fastapi
* uvicorn[standard]
* pydantic
* openai
* python-dotenv
* Docker + Docker compose
  
## Installation
* Clone the repository 
  ```git clone https://github.com/mayabreslauer/Pharmacy-Agent.git
    cd Pharmacy-Agent```
* Download Docker Desktop: https://www.docker.com/products/docker-desktop
* Enter to Pharmacy-Agent folder via explorer
* Add to .env file yor OPENAI_API_KEY
* Enter Pharmacy-Agent folder via terminal
* ```docker-compose up --build```
* open in explorer: http://localhost:80 to use the agent

## Files in the Repository
* requirements.txt
* .env
* docker-compose.yml
* README.md
* evaluation.md
### Backend Folder
* agent.py
* api.py
* database.py
* tools.py
* Dockfile
#### Data
* medications.json
* users.json

### Frontend Folder
* index.html
* Dockfile

## Example of Chat With The Agent
```User: What medications contain Ibuprofen?
Agent: Calls tool get_medication_info("Ibuprofen")
Tool: returns: Nurofen 400mg, non-prescription
Agent: Nurofen contains Ibuprofen...```

