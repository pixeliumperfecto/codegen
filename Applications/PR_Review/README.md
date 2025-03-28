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

## Configuration Options

- Webhook support for immediate reviews
- Port configuration for local server

## User Experience

- Clear logs of PR review process
- Detailed comments on PR issues
- Auto-approval for compliant PRs

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/pr-review-bot.git
   cd pr-review-bot
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
   WEBHOOK_SECRET="your_webhook_secret_here"
   
   # Codegen Configuration
   ANTHROPIC_API_KEY="your_anthropic_api_key_here"
   OPENAI_API_KEY="your_openai_api_key_here"
   ```

## Usage

### Starting the Server

Run the server locally:

```bash
python app.py
```

The server will start on the port specified in your configuration (default: 8000).

### Setting Up GitHub Webhooks

1. Go to your GitHub repository settings
2. Navigate to "Webhooks" and click "Add webhook"
3. Set the Payload URL to your server's URL (e.g., `http://your-server:8000/webhook`)
4. Set Content type to `application/json`
5. Set the Secret to match your `WEBHOOK_SECRET` in the `.env` file
6. Select "Let me select individual events" and choose "Pull requests"
7. Click "Add webhook"

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

1. **Webhook Reception**: The bot receives webhook events from GitHub when PRs are opened or updated
2. **Documentation Analysis**: It extracts content from all markdown files in the repository's root directory
3. **PR Analysis**: Using Codegen, it analyzes the PR against the documentation requirements
4. **Review Generation**: It generates a detailed review with specific issues and suggestions
5. **GitHub Integration**: It posts comments and formal reviews on the PR
6. **Auto-Approval**: If the PR complies with documentation, it automatically approves it