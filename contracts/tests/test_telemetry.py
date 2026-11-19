import json

from forja_contracts import telemetry as t


def _span(name, attrs, trace="0xaa", span="0x01", start="2026-11-19T10:00:00.000000Z", end="2026-11-19T10:00:02.500000Z"):
    return {
        "name": name,
        "context": {"trace_id": trace, "span_id": span},
        "parent_id": None,
        "attributes": attrs,
        "start_time": start,
        "end_time": end,
    }


def test_load_interactions_e_ultimo_feedback(tmp_path):
    msgs = [{"role": "user", "content": "diff"}]
    coms = [{"arquivo": "a.py", "linha": 3, "severidade": "bug", "comentario": "divide por zero"}]
    spans = [
        _span(
            t.SPAN_LLM,
            {
                t.ATTR_REPO: "eu/repo",
                t.ATTR_PR: 7,
                t.ATTR_FILE: "a.py",
                t.ATTR_MODEL: "qwen",
                t.ATTR_INPUT_MESSAGES: json.dumps(msgs),
                t.ATTR_OUTPUT_TEXT: "{}",
                t.ATTR_COMMENTS: json.dumps(coms),
                t.ATTR_PROBLEMS: "[]",
                t.ATTR_INPUT_TOKENS: 100,
                t.ATTR_OUTPUT_TOKENS: 20,
            },
        ),
        _span(t.SPAN_REVIEW, {}),
        _span(t.SPAN_FEEDBACK, {t.ATTR_REVIEW_TRACE: "aa", t.ATTR_COMMENT_ID: 5, t.ATTR_FEEDBACK_UP: 1}),
        _span(t.SPAN_FEEDBACK, {t.ATTR_REVIEW_TRACE: "aa", t.ATTR_COMMENT_ID: 5, t.ATTR_FEEDBACK_UP: 2}),
    ]
    p = tmp_path / "spans.jsonl"
    p.write_text("\n".join(json.dumps(s) for s in spans) + "\n", encoding="utf-8")
    calls, fb = t.load_interactions(tmp_path)  # diretório também vale
    assert len(calls) == 1
    c = calls[0]
    assert (c.trace_id, c.pr, c.mensagens, c.duracao_s) == ("aa", 7, msgs, 2.5)
    assert c.comentarios[0].severidade == "bug"
    assert [(f.comment_id, f.up) for f in fb] == [(5, 2)]
