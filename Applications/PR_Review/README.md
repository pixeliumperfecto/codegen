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
- **Cloudflare Workers integration** for stable production deployment

## Requirements

- Python 3.10 or higher
- GitHub Personal Access Token with `repo` and `admin:repo_hook` scopes
- For local development: ngrok account (free tier works)
- For production: Cloudflare account with Workers capability

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
   
   # For local development with ngrok
   USE_NGROK=true
   NGROK_AUTH_TOKEN=your_ngrok_auth_token_here
   
   # For production with Cloudflare
   USE_CLOUDFLARE=true
   CLOUDFLARE_API_TOKEN=your_cloudflare_api_token_here
   CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
   ```

## Usage

1. Start the bot:
   ```bash
   python app.py
   ```

2. The bot will:
   - Start a local server
   - Set up a public endpoint (using ngrok or Cloudflare Workers)
   - Set up webhooks for all repositories accessible by your GitHub token
   - Begin reviewing PRs as they are opened or updated

3. You can also manually trigger a review:
   ```
   curl -X POST http://localhost:8000/review/{owner}/{repo}/{pr_number}
   ```

## Deployment Options

### Local Development with ngrok

For local development or testing, the bot uses ngrok to expose your local server to the internet:

1. Set `USE_NGROK=true` in your `.env` file
2. Provide your ngrok auth token: `NGROK_AUTH_TOKEN=your_token_here`
3. Run the bot: `python app.py`

The bot will automatically start ngrok, get a public URL, and set up webhooks for all repositories.

### Production Deployment with Cloudflare Workers

For a more stable production deployment, the bot can use Cloudflare Workers:

1. Set `USE_CLOUDFLARE=true` in your `.env` file
2. Provide your Cloudflare API token and account ID:
   ```
   CLOUDFLARE_API_TOKEN=your_api_token_here
   CLOUDFLARE_ACCOUNT_ID=your_account_id_here
   ```
3. Run the bot: `python app.py`

The bot will:
- Create a Cloudflare Worker that forwards webhook requests to your local server
- Set up webhooks for all repositories to point to the Cloudflare Worker URL
- Automatically handle webhook verification and security

#### Using a Custom Domain with Cloudflare

To use a custom domain for your webhook endpoint:

1. Add your zone ID and route pattern to your `.env` file:
   ```
   CLOUDFLARE_ZONE_ID=your_zone_id_here
   CLOUDFLARE_WORKER_ROUTE=your_domain.com/webhook/*
   ```
2. Run the bot: `python app.py`

The bot will create a route for your worker on your custom domain.

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

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /webhook` - GitHub webhook endpoint
- `POST /review/{owner}/{repo}/{pr_number}` - Manually trigger a PR review
- `POST /setup-webhooks` - Manually trigger webhook setup for all repositories
- `GET /webhook-status` - Get the status of webhooks for all repositories
- `POST /setup-cloudflare` - Manually set up Cloudflare Worker
- `GET /test-cloudflare` - Test the connection to the Cloudflare Worker

## Troubleshooting

### Webhook Issues

- **Webhook creation fails**: Make sure your GitHub token has the `admin:repo_hook` scope
- **Webhook not receiving events**: Check that your public endpoint (ngrok or Cloudflare) is accessible
- **500 errors in webhook logs**: Check the bot's logs for detailed error information

### Ngrok Issues

- **Ngrok fails to start**: Make sure you've set your auth token in the `.env` file
- **Ngrok URL changes**: The bot automatically updates webhook URLs when ngrok restarts
- **Ngrok connection errors**: Check your internet connection and firewall settings

### Cloudflare Issues

- **Worker creation fails**: Make sure your Cloudflare API token has the Workers and DNS permissions
- **Worker not receiving requests**: Check that your local server is running and accessible
- **Custom domain not working**: Make sure your zone ID and route pattern are correct

## Advanced Configuration

You can customize the bot's behavior by modifying the following files:

- `app.py`: Main application logic and webhook handling
- `helpers.py`: PR review logic and Codegen integration
- `webhook_manager.py`: GitHub webhook management
- `ngrok_manager.py`: ngrok tunnel management
- `cloudflare_manager.py`: Cloudflare Workers integration

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.