import time
import statistics
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.vector_store import vector_store, user_vector_store
from app.services.llm import llm_service
from app.services.embeddings import embedding_service
from app.models.database import db
from app.core.utils import get_password_hash, verify_password
from app.services.auth import create_access_token, decode_token
from app.documents.processor import document_processor


ITERATIONS = 5
SAMPLE_QUERY = "what is the attendance policy for students"
SAMPLE_QUERY_DOC = "show me the full fees structure document"
SAMPLE_TEXT = "The student attendance policy requires a minimum of 75% attendance in each subject to be eligible for semester examinations."
LONG_TEXT = (
    "This is a detailed sample document about TCET college policies. "
    "It covers various aspects of academic regulations including attendance requirements, "
    "examination procedures, grading system, and disciplinary rules. "
    "The college follows a semester-based system with continuous evaluation. "
    "Students are required to maintain a minimum of 75% attendance in each subject. "
    "Those falling short may be given condonation on medical grounds. "
    "The academic year is divided into two semesters with examinations at the end of each. "
    "Internal assessment contributes 40% while semester-end exams contribute 60% to the final grade."
) * 10


def measure(label, fn, *args, iterations=ITERATIONS, **kwargs):
    times = []
    results = []
    for i in range(iterations):
        start = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            results.append(result)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
            results.append(f"ERROR: {e}")

    valid = [t for t in times if t >= 0]
    if not valid:
        print(f"  {'ERROR':>8}ms  | {label}")
        return None

    avg = statistics.mean(valid)
    med = statistics.median(valid)
    mn = min(valid)
    mx = max(valid)
    status = "OK" if not any("ERROR" in str(r) for r in results) else "ERR"
    print(
        f"  {avg:>7.1f}ms  {med:>7.1f}ms  {mn:>7.1f}ms  {mx:>7.1f}ms  [{status}] {label}"
    )
    return {"avg": avg, "median": med, "min": mn, "max": mx, "results": results}


def run_vector_store_tests():
    print("\n=== VECTOR STORE OPERATIONS ===")
    results = {}

    r = measure(
        "Embed single text",
        embedding_service.embed_text,
        SAMPLE_QUERY,
    )
    results["embed_single"] = r

    r = measure(
        "Embed multiple texts",
        embedding_service.embed_texts,
        [SAMPLE_TEXT, SAMPLE_QUERY, LONG_TEXT[:200]],
    )
    results["embed_multi"] = r

    first_run = True
    for i in range(ITERATIONS):
        start = time.perf_counter()
        try:
            vector_store.retrieve_similar(SAMPLE_QUERY)
            elapsed = (time.perf_counter() - start) * 1000
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
        if first_run:
            cold_time = elapsed
            first_run = False

    r = measure(
        "Similarity search (top_k=5)",
        vector_store.retrieve_similar,
        SAMPLE_QUERY,
    )
    results["similarity_search"] = r

    r = measure("Get document count", vector_store.get_document_count)
    results["doc_count"] = r

    r = measure("Get all filenames", vector_store.get_all_filenames)
    results["all_filenames"] = r

    filenames = vector_store.get_all_filenames()
    if filenames:
        r = measure(
            "Get all chunks by filename",
            vector_store.get_all_chunks_by_filename,
            filenames[0],
        )
        results["chunks_by_filename"] = r

    return results


def run_llm_tests():
    print("\n=== LLM OPERATIONS ===")

    r = measure("Check connection", llm_service.check_connection)
    results = {"connection": r}

    r = measure(
        "Decide web search (conversational)",
        llm_service.decide_web_search,
        "hello how are you",
    )
    results["decide_web_conv"] = r

    r = measure(
        "Decide web search (factual)",
        llm_service.decide_web_search,
        "what is the latest news about AI",
    )
    results["decide_web_fact"] = r

    r = measure(
        "Is document query (document)",
        llm_service._is_document_query,
        SAMPLE_QUERY_DOC,
    )
    results["is_doc_query_yes"] = r

    r = measure(
        "Is document query (topic)",
        llm_service._is_document_query,
        SAMPLE_QUERY,
    )
    results["is_doc_query_no"] = r

    try:
        docs = vector_store.retrieve_similar(SAMPLE_QUERY)
        if docs:
            r = measure("Identify document from docs", llm_service._identify_document, docs)
            results["identify_doc"] = r

            r = measure(
                "Generate RAG response (non-stream)",
                llm_service.generate_rag_response,
                SAMPLE_QUERY,
                docs,
            )
            results["rag_response"] = r

            r = measure(
                "Generate RAG response (doc query)",
                llm_service.generate_rag_response,
                SAMPLE_QUERY_DOC,
                docs,
            )
            results["rag_response_doc"] = r
    except Exception as e:
        print(f"  SKIP RAG tests (no docs or error): {e}")

    r = measure(
        "Generate text response (non-stream)",
        llm_service.generate_response,
        "what is 2+2",
    )
    results["text_response"] = r

    return results


def run_database_tests():
    print("\n=== DATABASE OPERATIONS ===")
    results = {}

    r = measure("Get user (admin)", db.get_user, "admin")
    results["get_user"] = r

    r = measure("Get all documents", db.get_all_documents)
    results["get_all_docs"] = r

    sessions = db.get_user_sessions("admin-001")
    r_val = {"avg": 0, "median": 0, "min": 0, "max": 0}
    times = []
    for s in sessions[:3]:
        start = time.perf_counter()
        try:
            db.get_session_messages(s["session_id"])
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        except Exception:
            pass
    if times:
        r_val = {
            "avg": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
        }
        print(
            f"  {r_val['avg']:>7.1f}ms  {r_val['median']:>7.1f}ms  {r_val['min']:>7.1f}ms  {r_val['max']:>7.1f}ms  [OK] Get session messages"
        )
    results["session_messages"] = r_val

    r = measure("Get user sessions", db.get_user_sessions, "admin-001")
    results["user_sessions"] = r

    r = measure("Get session info", db.get_session, sessions[0]["session_id"] if sessions else "none")
    results["get_session"] = r

    r = measure("Get TCET docs", db.get_all_tcet_docs)
    results["tcet_docs"] = r

    return results


def run_auth_tests():
    print("\n=== AUTHENTICATION OPERATIONS ===")
    results = {}

    r = measure("Password hashing", get_password_hash, "test_password_123")
    results["hash_pw"] = r

    hashed = get_password_hash("test_password_123")
    r = measure("Password verification", verify_password, "test_password_123", hashed)
    results["verify_pw"] = r

    r = measure(
        "Create JWT token",
        create_access_token,
        {"user_id": "admin-001", "username": "admin"},
    )
    results["create_token"] = r

    token = create_access_token({"user_id": "admin-001", "username": "admin"})
    r = measure("Decode JWT token", decode_token, token)
    results["decode_token"] = r

    return results


def run_doc_processing_tests():
    print("\n=== DOCUMENT PROCESSING OPERATIONS ===")
    results = {}

    r = measure("Chunk long text", document_processor._chunk_text, LONG_TEXT)
    results["chunk_text"] = r

    return results


def main():
    print("=" * 72)
    print("  TCET CHATBOT - LATENCY BENCHMARK")
    print(f"  Iterations per test: {ITERATIONS}")
    print(f"  Timings in milliseconds (lower is better)")
    print("=" * 72)

    print(f"\n{'':>10}  {'AVG':>7}  {'MEDIAN':>7}  {'MIN':>7}  {'MAX':>7}  STATUS  TEST")
    print("-" * 72)

    all_results = {}

    all_results["vector_store"] = run_vector_store_tests()
    all_results["llm"] = run_llm_tests()
    all_results["database"] = run_database_tests()
    all_results["auth"] = run_auth_tests()
    all_results["doc_processing"] = run_doc_processing_tests()

    print("\n" + "=" * 72)
    print("  SUMMARY BY CATEGORY (avg ms)")
    print("-" * 72)
    categories = {
        "Vector Store": all_results.get("vector_store", {}),
        "LLM": all_results.get("llm", {}),
        "Database": all_results.get("database", {}),
        "Auth": all_results.get("auth", {}),
        "Doc Processing": all_results.get("doc_processing", {}),
    }
    for cat_name, cat_results in categories.items():
        avgs = [v["avg"] for v in cat_results.values() if v and "avg" in v]
        if avgs:
            print(f"  {cat_name:20s}  {statistics.mean(avgs):>8.1f}ms  (over {len(avgs)} tests)")
        else:
            print(f"  {cat_name:20s}  {'N/A':>8}")

    print("\n  Done.")


if __name__ == "__main__":
    main()
