from codegen.sdk.codebase.factory.get_session import get_codebase_graph_session
from codegen.shared.enums.programming_language import ProgrammingLanguage


def test_comment_inline(tmpdir) -> None:
    content = """
const symbol = 1;  // this is an inline comment
"""
    with get_codebase_graph_session(tmpdir=tmpdir, programming_language=ProgrammingLanguage.TYPESCRIPT, files={"test.ts": content}) as ctx:
        file = ctx.get_file("test.ts")

        symbol = file.get_symbol("symbol")
        assert symbol.comment is None
        assert symbol.inline_comment.source == "// this is an inline comment"
        assert symbol.inline_comment.text == "this is an inline comment"


def test_comment_inline_block(tmpdir) -> None:
    content = """
const symbol = 1;  /* this is an inline comment */
"""
    with get_codebase_graph_session(tmpdir=tmpdir, programming_language=ProgrammingLanguage.TYPESCRIPT, files={"test.ts": content}) as ctx:
        file = ctx.get_file("test.ts")

        symbol = file.get_symbol("symbol")
        assert symbol.comment is None
        assert symbol.inline_comment.source == "/* this is an inline comment */"
        assert symbol.inline_comment.text == "this is an inline comment"
