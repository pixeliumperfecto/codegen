#!/bin/bash

# Install Python 3.13 from deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.13 python3.13-venv python3.13-dev

# Create virtual environment in /home/l
cd /home/l
python3.13 -m venv py313_env

# Add alias to .bashrc for easy activation
echo '
# Python 3.13 venv quick activation
function activate_py313() {
    read -p "Press 1 to activate Python 3.13 venv: " choice
    if [ "$choice" = "1" ]; then
        source /home/l/py313_env/bin/activate
        echo "Python 3.13 environment activated!"
    fi
}

# Show activation prompt on terminal startup
activate_py313

# Alias for quick activation anytime
alias py3="source /home/l/py313_env/bin/activate"
' >> ~/.bashrc

# Apply changes to current session
source ~/.bashrc

echo "Setup complete! Python 3.13 installed and venv created at /home/l/py313_env"
echo "Terminal will now prompt for venv activation on startup"
echo "You can also use the 'py3' command anytime to activate it"
