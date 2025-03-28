PR Review Bot Requirements
Core Functionality

Monitor all incoming PRs to specified GitHub repositories
Review PRs against documentation in root directory (.md files)
Auto-approve PRs that comply with documentation
Suggest changes for non-compliant PRs

Technical Requirements

Locally hosted (not Modal cloud service)
Support for webhook mode
Authentication via GitHub Personal Access Token
Analyze PRs against README.md and other root-level .md files
Python-based implementation using FastAPI

Implementation Details

GitHub API integration for PR monitoring and interaction
Codegen integration for intelligent PR review
Root directory markdown file analysis
Automated commenting and approvals

Configuration Options

Webhook support for immediate reviews
Port configuration for local server

User Experience

Clear logs of PR review process
Detailed comments on PR issues
Auto-approval for compliant PRs