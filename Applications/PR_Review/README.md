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

## Requirements

- Python 3.10 or higher
- GitHub Personal Access Token with `repo` and `admin:repo_hook` scopes
- ngrok account (free tier works) for local development

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

3. Create a `.env` file with your GitHub token and ngrok auth token:
   ```
   GITHUB_TOKEN=your_github_token_here
   NGROK_AUTH_TOKEN=your_ngrok_auth_token_here
   USE_NGROK=true
   PORT=8000
   ```

## Usage

1. Start the bot:
   ```bash
   python app.py
   ```

2. The bot will:
   - Start a local server
   - Start an ngrok tunnel to expose your local server
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

## Ngrok Authentication Setup

1. Sign up for a free ngrok account at https://dashboard.ngrok.com/signup
2. Get your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken
3. Add it to your `.env` file as `NGROK_AUTH_TOKEN=your_token_here`

## Troubleshooting

### Webhook Issues

- **Webhook creation fails**: Make sure your GitHub token has the `admin:repo_hook` scope
- **Webhook not receiving events**: Check that your ngrok tunnel is running and accessible
- **500 errors in webhook logs**: Check the bot's logs for detailed error information

### Ngrok Issues

- **Ngrok fails to start**: Make sure you've set your auth token in the `.env` file
- **Ngrok URL changes**: The bot automatically updates webhook URLs when ngrok restarts
- **Ngrok connection errors**: Check your internet connection and firewall settings

## Advanced Configuration

You can customize the bot's behavior by modifying the following files:

- `app.py`: Main application logic and webhook handling
- `helpers.py`: PR review logic and Codegen integration
- `webhook_manager.py`: GitHub webhook management
- `ngrok_manager.py`: ngrok tunnel management

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.