from engine.generator.knowledge_document_generator import KnowledgeDocumentGenerator


def test_generator_preserves_analyzer_language_keywords_and_entities():
    result = KnowledgeDocumentGenerator().generate(
        {"object_id": "OBJ-1", "object_code": "DOCUMENT"},
        {"generated_identifier": "DOC-1"},
        {
            "analyzer_result": {
                "text": "sample text",
                "language_code": "en",
                "keywords": [{"keyword": "sample", "frequency": 1}],
                "entities": [{"text": "OpenAI", "type": "ORG"}],
            }
        },
    )

    assert result["language_code"] == "en"
    assert result["knowledge"]["keywords"] == [{"keyword": "sample", "frequency": 1}]
    assert result["knowledge"]["entities"] == [{"text": "OpenAI", "type": "ORG"}]


def test_fallback_keyword_extraction_uses_only_analyzer_supplied_stopwords():
    result = KnowledgeDocumentGenerator().generate(
        {"object_id": "OBJ-1", "object_code": "DOCUMENT"},
        {"generated_identifier": "DOC-1"},
        {
            "analyzer_result": {
                "text": "the data data and",
                "language_code": "en",
                "stopwords": ["the", "and"],
            }
        },
    )

    assert result["language_code"] == "en"
    assert result["knowledge"]["keywords"] == [{"keyword": "data", "frequency": 2}]


def test_unknown_language_is_not_assumed_to_be_korean():
    result = KnowledgeDocumentGenerator().generate(
        {"object_id": "OBJ-1", "object_code": "DOCUMENT"},
        {"generated_identifier": "DOC-1"},
        {"analyzer_result": {"text": "some words"}},
    )

    assert result["language_code"] == "und"
