# AVA - Romance Chatbot

AVA is an AI-powered romance chatbot designed to engage users in meaningful, flirtatious, and emotionally intelligent conversations. Whether you're looking for companionship, playful banter, or heartfelt dialogue, AVA delivers a warm and personalized chat experience.

## Features

- **Natural Conversation** - Engaging, human-like dialogue that flows naturally
- **Emotional Intelligence** - Recognizes and responds to user sentiment and mood
- **Personalized Interactions** - Remembers preferences and adapts to each user's conversational style
- **Playful & Flirtatious Tone** - Light-hearted, charming responses that keep conversations fun

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (must be running)
- [Node.js](https://nodejs.org/) (v18+)
- [Ollama](https://ollama.com/) (for local LLM)

## Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/your-org/ava.git
cd ava
```

### 2. Set up Ollama (local LLM)
Install Ollama, then pull the required models:
```bash
ollama pull mistral
ollama pull phi3:mini
```
Make sure Ollama is running before starting the backend.

### 3. Configure environment
```bash
cp backend/.env.example backend/.env
```
Edit `backend/.env` if you need to change any defaults.

### 4. Start backend + databases (Docker)
```bash
cd infra
docker-compose up --build
```
This starts the FastAPI backend, PostgreSQL, and Qdrant. Wait until you see the Uvicorn startup log.

### 5. Run database migrations
In a separate terminal, run the Alembic migration inside the backend container:
```bash
docker exec -it infra-backend-1 alembic upgrade head
```
> If the container name differs, check with `docker ps`.

### 6. Start the frontend (local)
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```

### 7. Open the app
Go to [http://localhost:3000](http://localhost:3000), create an account, and start chatting.

## Usage

Once running, you can interact with AVA through the chat interface. AVA will respond conversationally and adjust her tone based on the flow of the dialogue.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request if you'd like to improve AVA.

## License

This project is licensed under the MIT License.
