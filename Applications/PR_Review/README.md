# PR Review Bot

## Core Functionality

- Monitor all incoming PRs to any GitHub repository
- Review PRs against documentation in root directory (.md files)
- Auto-approve PRs that comply with documentation
- Suggest changes for non-compliant PRs

## Technical Requirements

- Locally hosted (not Modal cloud service)
- Support for webhook mode
- Authentication via GitHub Personal Access Token
- Analyze PRs against README.md and other root-level .md files
- Python-based implementation using FastAPI

## Implementation Details

- GitHub API integration for PR monitoring and interaction
- Codegen integration for intelligent PR review
- Root directory markdown file analysis
- Automated commenting and approvals
- Dynamic webhook management for all repositories

## Configuration Options

- Webhook support for immediate reviews
- Port configuration for local server
- Automatic webhook setup for all repositories
- Support for ngrok and other tunneling services

## User Experience

- Clear logs of PR review process
- Detailed comments on PR issues
- Auto-approval for compliant PRs
- Automatic webhook management

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pixeliumperfecto/codegen.git
   cd codegen/Applications/PR_Review
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Create a `.env` file based on the template:
   ```bash
   cp .env.template .env
   ```

5. Edit the `.env` file with your configuration:
   ```
   # GitHub Configuration
   GITHUB_TOKEN="your_github_token_here"
   
   # Server Configuration
   PORT=8000
   WEBHOOK_URL="https://your-public-url.ngrok.io/webhook"
   
   # Codegen Configuration
   ANTHROPIC_API_KEY="your_anthropic_api_key_here"
   OPENAI_API_KEY="your_openai_api_key_here"
   ```

## GitHub Token Setup

The PR Review Bot requires a GitHub Personal Access Token with specific permissions to create and manage webhooks:

1. Go to your GitHub account settings: https://github.com/settings/tokens
2. Click "Generate new token" (classic)
3. Give your token a descriptive name (e.g., "PR Review Bot")
4. Select the following scopes:
   - `repo` (Full control of private repositories)
   - `admin:repo_hook` (Full control of repository hooks)
5. Click "Generate token"
6. Copy the token and add it to your `.env` file as `GITHUB_TOKEN`

**Important**: The token must have `admin:repo_hook` scope to create webhooks. If you see permission errors when running the bot, check that your token has the correct scopes.

## Usage

### Starting the Server

Run the server locally:

```bash
python app.py
```

The server will:
1. Check if your GitHub token is valid and has the necessary permissions
2. Detect or use the configured webhook URL
3. Set up webhooks for all repositories accessible by your GitHub token
4. Print the status of each repository's webhook setup
5. Start the FastAPI server on the configured port

### Making Your Server Publicly Accessible

GitHub webhooks require a publicly accessible URL. Here are some options:

#### Option 1: ngrok (Recommended for Development/Testing)

[ngrok](https://ngrok.com/) creates a secure tunnel to your local server:

1. Install ngrok: `pip install pyngrok` or download from [ngrok.com](https://ngrok.com/)
2. In a separate terminal, run: `ngrok http 8000`
3. ngrok will provide a public URL (like `https://abc123.ngrok.io`)
4. Set this URL in your `.env` file: `WEBHOOK_URL="https://abc123.ngrok.io/webhook"`
5. Start the PR Review Bot: `python app.py`

**Note**: Each time you restart ngrok, it will generate a new URL. The PR Review Bot will automatically update all webhook URLs when you restart it with the new ngrok URL.

#### Option 2: Deploy to a Public Server (Recommended for Production)

For a production environment, deploy your FastAPI app to a server with a public IP:
- Cloud providers (AWS, Azure, GCP)
- PaaS solutions (Heroku, Render, Railway)
- Your own server with a public IP

### Troubleshooting Webhook Issues

If you see errors like "Failed to create webhook for repository/name", check the following:

1. **GitHub Token Permissions**: Make sure your token has the `admin:repo_hook` scope
2. **Webhook URL Accessibility**: Your webhook URL must be publicly accessible from the internet
   - Local IP addresses (127.0.0.1, 192.168.x.x, etc.) won't work
   - Use ngrok or a similar service to expose your local server
3. **Repository Permissions**: You must have admin access to the repository to create webhooks

### Automatic Webhook Management

The PR Review Bot automatically manages webhooks for all repositories accessible by your GitHub token:

1. On startup, it will:
   - Fetch all repositories accessible by your token
   - Check if each repository has a webhook for PR reviews
   - Create webhooks for repositories that don't have one
   - Update webhook URLs for repositories with outdated URLs
   - Print the status of each repository's webhook setup

2. You can also manually trigger webhook setup:
   ```
   POST /setup-webhooks
   ```

3. Check webhook status:
   ```
   GET /webhook-status
   ```

4. When new repositories are created, the bot will automatically add webhooks to them and print the status.

### Manual PR Review

You can also trigger a review manually by making a POST request to:

```
POST /review/{repo_owner}/{repo_name}/{pr_number}
```

Example using curl:

```bash
curl -X POST http://localhost:8000/review/pixeliumperfecto/codegen/123
```

## How It Works

1. **Webhook Management**: The bot automatically sets up and maintains webhooks for all repositories
2. **Webhook Reception**: It receives webhook events from GitHub when PRs are opened or updated
3. **Documentation Analysis**: It extracts content from all markdown files in the repository's root directory
4. **PR Analysis**: Using Codegen, it analyzes the PR against the documentation requirements
5. **Review Generation**: It generates a detailed review with specific issues and suggestions
6. **GitHub Integration**: It posts comments and formal reviews on the PR
7. **Auto-Approval**: If the PR complies with documentation, it automatically approves it