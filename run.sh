# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Check if poetry is installed
if ! command -v poetry &> /dev/null
then
    echo "Poetry could not be found, installing poetry"
    curl -sSL https://install.python-poetry.org | python3 -
fi

poetry install
poetry run python "$DIR"/github_pr_watcher/main.py