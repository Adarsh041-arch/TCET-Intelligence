"""Run all v2 generators against the adversarial fixture and validate output."""
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
    for required in ("heading", "paragraph", "list", "table", "block_code", "block_quote", "thematic_break"):
        assert required in types, f"Missing block type: {required}"
    print(f"[AST] OK — {len(ast)} blocks, {len(set(types))} types")
    return ast


def test_docx_v2():
    from app.document_generation.generators.docx_generator_v2 import DOCXGeneratorV2
    with open(FIXTURE, encoding="utf-8") as f:
        md = f.read()
    gen = DOCXGeneratorV2()
    result = gen.generate(md, {"name": "Test"})
    assert isinstance(result, bytes) and len(result) > 0
    print(f"[DOCX v2] OK — {len(result)} bytes")


def test_pptx_v2():
    from app.document_generation.generators.pptx_generator_v2 import PPTXGeneratorV2
    with open(FIXTURE, encoding="utf-8") as f:
        md = f.read()
    gen = PPTXGeneratorV2()
    result = gen.generate(md, {"name": "Test"})
    assert isinstance(result, bytes) and len(result) > 0
    print(f"[PPTX v2] OK — {len(result)} bytes")


def test_xlsx_v2():
    from app.document_generation.generators.xlsx_generator_v2 import XLSXGeneratorV2
    with open(FIXTURE, encoding="utf-8") as f:
        md = f.read()
    gen = XLSXGeneratorV2()
    result = gen.generate(md, {"name": "Test"})
    assert isinstance(result, bytes) and len(result) > 0
    print(f"[XLSX v2] OK — {len(result)} bytes")


def test_registry():
    # Import routes to trigger _register_generators()
    import app.document_generation.api.routes
    from app.document_generation.registry import GeneratorRegistry
    for fmt in ("docx-v2", "pptx-v2", "xlsx-v2"):
        gen = GeneratorRegistry.get(fmt)
        assert gen is not None
        print(f"[Registry] OK — {fmt}")


if __name__ == "__main__":
    test_ast_parse()
    test_docx_v2()
    test_pptx_v2()
    test_xlsx_v2()
    test_registry()
    print("\nAll tests passed!")
