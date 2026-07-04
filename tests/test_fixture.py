"""Run all generators against the adversarial fixture and validate output."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "adversarial.md")


def test_ast_parse():
    from app.document_generation.markdown_ast import parse
    with open(FIXTURE, encoding="utf-8") as f:
        md = f.read()
    ast = parse(md)
    assert isinstance(ast, list), "AST should be a list"
    assert len(ast) > 0, "AST should not be empty"
    types = [b["type"] for b in ast]
    assert "heading" in types, "Should have headings"
    assert "paragraph" in types, "Should have paragraphs"
    assert "list" in types, "Should have lists"
    assert "table" in types, "Should have tables"
    assert "block_code" in types, "Should have code blocks"
    assert "block_quote" in types, "Should have blockquotes"
    assert "thematic_break" in types, "Should have horizontal rules"
    print(f"AST: {len(ast)} blocks, types: {types}")
    return ast


def test_docx_v2():
    from app.document_generation.generators.docx_generator_v2 import DOCXGeneratorV2
    with open(FIXTURE, encoding="utf-8") as f:
        md = f.read()
    gen = DOCXGeneratorV2()
    result = gen.generate(md, {"name": "Test"})
    assert isinstance(result, bytes)
    assert len(result) > 0
    print(f"DOCX v2: {len(result)} bytes")


if __name__ == "__main__":
    test_ast_parse()
    test_docx_v2()
    print("All tests passed!")
