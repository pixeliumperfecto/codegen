"""Tests for codebase tools."""

import pytest

from codegen.extensions.tools import (
    create_file,
    create_pr,
    create_pr_comment,
    create_pr_review_comment,
    delete_file,
    edit_file,
    list_directory,
    move_symbol,
    rename_file,
    replacement_edit,
    reveal_symbol,
    run_codemod,
    search,
    semantic_edit,
    semantic_search,
    view_file,
    view_pr,
)
from codegen.sdk.codebase.factory.get_session import get_codebase_session


@pytest.fixture
def codebase(tmpdir):
    """Create a simple codebase for testing."""
    # language=python
    content = """
def hello():
    print("Hello, world!")

class Greeter:
    def greet(self):
        hello()
"""
    with get_codebase_session(tmpdir=tmpdir, files={"src/main.py": content}) as codebase:
        yield codebase


def test_view_file(codebase):
    """Test viewing a file."""
    result = view_file(codebase, "src/main.py")
    assert "error" not in result
    assert result["filepath"] == "src/main.py"
    assert "hello()" in result["content"]


def test_list_directory(codebase):
    """Test listing directory contents."""
    result = list_directory(codebase, "./")
    assert "error" not in result
    assert "src" in result["subdirectories"]


def test_search(codebase):
    """Test searching the codebase."""
    result = search(codebase, "hello")
    assert "error" not in result
    assert len(result["results"]) > 0


def test_edit_file(codebase):
    """Test editing a file."""
    result = edit_file(codebase, "src/main.py", "print('edited')")
    assert "error" not in result
    assert result["content"] == "1|print('edited')"


def test_create_file(codebase):
    """Test creating a file."""
    result = create_file(codebase, "src/new.py", "print('new')")
    assert "error" not in result
    assert result["filepath"] == "src/new.py"
    assert result["content"] == "1|print('new')"


def test_delete_file(codebase):
    """Test deleting a file."""
    result = delete_file(codebase, "src/main.py")
    assert "error" not in result
    assert result["status"] == "success"


def test_rename_file(codebase):
    """Test renaming a file."""
    result = rename_file(codebase, "src/main.py", "src/renamed.py")
    assert "error" not in result
    assert result["status"] == "success"
    assert result["new_filepath"] == "src/renamed.py"


def test_move_symbol(codebase):
    """Test moving a symbol between files."""
    # Create target file first
    create_file(codebase, "src/target.py", "")

    result = move_symbol(
        codebase,
        source_file="src/main.py",
        symbol_name="hello",
        target_file="src/target.py",
    )
    assert "error" not in result
    assert result["status"] == "success"


def test_reveal_symbol(codebase):
    """Test revealing symbol relationships."""
    result = reveal_symbol(
        codebase,
        symbol_name="hello",
        max_depth=1,
    )
    assert "error" not in result
    assert not result["truncated"]


@pytest.mark.skip("TODO")
def test_semantic_edit(codebase):
    """Test semantic editing."""
    edit_spec = """
# ... existing code ...
def hello():
    print("Hello from semantic edit!")
# ... existing code ...
"""
    result = semantic_edit(codebase, "src/main.py", edit_spec)
    assert "error" not in result
    assert result["status"] == "success"


@pytest.mark.skip("TODO")
def test_semantic_search(codebase):
    """Test semantic search."""
    result = semantic_search(codebase, "function that prints hello")
    assert "error" not in result
    assert result["status"] == "success"


@pytest.mark.skip("TODO: Github tests")
def test_create_pr(codebase):
    """Test creating a PR."""
    result = create_pr(codebase, "Test PR", "This is a test PR")
    assert "error" not in result
    assert result["status"] == "success"


@pytest.mark.skip("TODO: Github tests")
def test_view_pr(codebase):
    """Test viewing a PR."""
    result = view_pr(codebase, 1)
    assert "error" not in result
    assert result["status"] == "success"
    assert "modified_symbols" in result
    assert "patch" in result


@pytest.mark.skip("TODO: Github tests")
def test_create_pr_comment(codebase):
    """Test creating a PR comment."""
    result = create_pr_comment(codebase, 1, "Test comment")
    assert "error" not in result
    assert result["status"] == "success"
    assert result["message"] == "Comment created successfully"


@pytest.mark.skip("TODO: Github tests")
def test_create_pr_review_comment(codebase):
    """Test creating a PR review comment."""
    result = create_pr_review_comment(
        codebase,
        pr_number=1,
        body="Test review comment",
        commit_sha="abc123",
        path="src/main.py",
        line=1,
    )
    assert "error" not in result
    assert result["status"] == "success"
    assert result["message"] == "Review comment created successfully"


def test_replacement_edit(codebase):
    """Test regex-based replacement editing."""
    # Test basic replacement
    result = replacement_edit(
        codebase,
        filepath="src/main.py",
        pattern=r'print\("Hello, world!"\)',
        replacement='print("Goodbye, world!")',
    )
    assert "error" not in result
    assert result["status"] == "success"
    assert 'print("Goodbye, world!")' in result["new_content"]

    # Test with line range
    result = replacement_edit(
        codebase,
        filepath="src/main.py",
        pattern=r"Greeter",
        replacement="Welcomer",
        start=5,  # Class definition line
        end=7,
    )
    assert "error" not in result
    assert result["status"] == "success"
    assert "class Welcomer" in result["new_content"]

    # Test with regex groups
    result = replacement_edit(
        codebase,
        filepath="src/main.py",
        pattern=r"def (\w+)\(\):",
        replacement=r"def \1_function():",
    )
    assert "error" not in result
    assert result["status"] == "success"
    assert "def hello_function():" in result["new_content"]

    # Test with count limit
    result = replacement_edit(
        codebase,
        filepath="src/main.py",
        pattern=r"def",
        replacement="async def",
        count=1,  # Only replace first occurrence
    )
    assert "error" not in result
    assert result["status"] == "success"
    assert result["new_content"].count("async def") == 1

    # Test no matches
    result = replacement_edit(
        codebase,
        filepath="src/main.py",
        pattern=r"nonexistent_pattern",
        replacement="replacement",
    )
    assert result["status"] == "unchanged"
    assert "No matches found" in result["message"]


def test_run_codemod(codebase):
    """Test running custom codemods."""
    # Test adding type hints
    codemod_source = """
def run(codebase: Codebase):
    for file in codebase.files:
        file.edit('# hello, world!' + file.content)
"""
    result = run_codemod(codebase, codemod_source)
    assert result["status"] == "success"
    assert "+# hello, world" in result["diff"]
