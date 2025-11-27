# Environment Variables Setup

This project requires environment variables to be configured for both local development and Vercel deployment.

## Local Development

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your actual values:
   ```
   OPENAI_API_KEY=sk-your-openai-api-key
   PINECONE_API_KEY=your_actual_api_key
   PINECONE_INDEX_NAME=your_actual_index_name
   ```

3. The `.env` file is automatically loaded by the application and is ignored by git.

## Vercel Deployment

For Vercel deployment, you need to set environment variables in the Vercel dashboard:

1. Go to your project in the Vercel dashboard
2. Navigate to **Settings** → **Environment Variables**
3. Add the following variables:
   - `OPENAI_API_KEY`: Your OpenAI API key (for GPT)
   - `PINECONE_API_KEY`: Your Pinecone API key
   - `PINECONE_INDEX_NAME`: Your Pinecone index name

4. Make sure to set these variables for the appropriate environments (Production, Preview, Development)

## Required Environment Variables

| Variable | Description | Required | Used By |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key for GPT (starts with `sk-`) | Yes | Bot Service (intent extraction, chat) |
| `PINECONE_API_KEY` | Your Pinecone API key | Yes | Pinecone Search Service |
| `PINECONE_INDEX_NAME` | Your Pinecone index name | Yes | Pinecone Search Service |

## Service Architecture

This project uses a **Bot Service** that orchestrates conversation and search:

```
User Message → Bot Service → Intent Understanding (GPT) → Action Decision
                    ↓                                            ↓
              Session Management                         Search Service
                                                              ↓
                                                        Pinecone Search
```

### Bot Service Features
- 🧠 Understands user intent using GPT
- 🔍 Intelligently searches products
- 💬 Maintains conversation context
- ✨ Generates natural responses
- 🎯 Formats product data for frontend

## Testing

Run the test suite to verify the bot service is working:
```bash
python api/test_bot_service.py
```

## Security Note

⚠️ **Never commit the `.env` file to version control!** It contains sensitive credentials.

The `.env` file is already added to `.gitignore` to prevent accidental commits.
