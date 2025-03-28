# PR Review Bot

A bot that automatically reviews pull requests against documentation in the repository's root directory.

## Features

- **Locally hosted** FastAPI server (not Modal cloud service)
- **Webhook support** for immediate PR reviews
- **GitHub API integration** using Personal Access Token
- **Markdown analysis** of root directory documentation files
- **Intelligent PR review** using Codegen
- **Auto-approval** for compliant PRs
- **Dynamic webhook management** for all repositories
- **Automatic ngrok integration** for local development
- **Cloudflare Workers integration** for stable production deployments

## Requirements

- Python 3.10 or higher
- GitHub Personal Access Token with `repo` and `admin:repo_hook` scopes
- ngrok account (free tier works) for local development
- Cloudflare account (optional, for production deployments)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pixeliumperfecto/codegen.git
   cd codegen/Applications/PR_Review
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

3. Create a `.env` file with your configuration:
   ```
   # Required
   GITHUB_TOKEN=your_github_token_here
   
   # For ngrok (local development)
   NGROK_AUTH_TOKEN=your_ngrok_auth_token_here
   USE_NGROK=true
   
   # For Cloudflare (production)
   USE_CLOUDFLARE=false
   CLOUDFLARE_API_TOKEN=your_cloudflare_api_token_here
   CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
   
   # Server configuration
   PORT=8000
   ```

## Usage

1. Start the bot:
   ```bash
   python app.py
   ```

2. The bot will:
   - Start a local server
   - Set up a tunnel (ngrok or Cloudflare Workers) to expose your local server
   - Set up webhooks for all repositories accessible by your GitHub token
   - Begin reviewing PRs as they are opened or updated

3. You can also manually trigger a review:
   ```
   curl -X POST http://localhost:8000/review/{owner}/{repo}/{pr_number}
   ```

## How It Works

1. **Webhook Setup**: The bot automatically sets up webhooks for all repositories accessible by your GitHub token.

2. **PR Review Process**:
   - When a PR is opened or updated, GitHub sends a webhook event to the bot
   - The bot analyzes the PR against documentation in the repository's root directory
   - It checks if the PR complies with the documentation requirements
   - It posts a review comment with issues and suggestions
   - It approves the PR if it complies, or requests changes if it doesn't

3. **Codegen Integration**:
   - The bot uses Codegen's AI capabilities to analyze PRs
   - It leverages Codegen's GitHub tools for PR interaction
   - It provides detailed, context-aware reviews

## Ngrok Authentication Setup (Local Development)

1. Sign up for a free ngrok account at https://dashboard.ngrok.com/signup
2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
3. Add it to your `.env` file as `NGROK_AUTH_TOKEN=your_token_here`

## Cloudflare Workers Setup (Production)

1. Sign up for a Cloudflare account at https://dash.cloudflare.com/sign-up
2. Create an API token with the following permissions:
   - Account-level: `Workers Scripts:Edit`
   - Zone-level: `Workers Routes:Edit` (if using a custom domain)
3. Get your account ID from the Cloudflare dashboard URL (e.g., `https://dash.cloudflare.com/abc123` where `abc123` is your account ID)
4. Add to your `.env` file:
   ```
   USE_CLOUDFLARE=true
   CLOUDFLARE_API_TOKEN=your_api_token_here
   CLOUDFLARE_ACCOUNT_ID=your_account_id_here
   ```
5. For custom domain (optional):
   ```
   CLOUDFLARE_ZONE_ID=your_zone_id_here
   CLOUDFLARE_WORKER_ROUTE=your_domain.com/webhook/*
   ```

## Troubleshooting

### Webhook Issues

- **Webhook creation fails**: Make sure your GitHub token has the `admin:repo_hook` scope
- **Webhook not receiving events**: Check that your tunnel (ngrok or Cloudflare) is running and accessible
- **500 errors in webhook logs**: Check the bot's logs for detailed error information

### Ngrok Issues

- **Ngrok fails to start**: Make sure you've set your auth token in the `.env` file
- **Ngrok URL changes**: The bot automatically updates webhook URLs when ngrok restarts
- **Ngrok connection errors**: Check your internet connection and firewall settings

### Cloudflare Issues

- **Worker creation fails**: Make sure your API token has the `Workers Scripts:Edit` permission
- **Route creation fails**: Make sure your API token has the `Workers Routes:Edit` permission
- **Worker not receiving requests**: Check that your local server is running and accessible from Cloudflare

## Advanced Configuration

You can customize the bot's behavior by modifying the following files:

- `app.py`: Main application logic and webhook handling
- `helpers.py`: PR review logic and Codegen integration
- `webhook_manager.py`: GitHub webhook management
- `ngrok_manager.py`: ngrok tunnel management
- `cloudflare_manager.py`: Cloudflare Workers management

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.