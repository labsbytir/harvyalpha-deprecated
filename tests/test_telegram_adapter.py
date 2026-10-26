import json
import tempfile
import unittest
from pathlib import Path

from scrape.telegram import (
    atomic_write_json,
    extract_entities,
    extract_poll,
    extract_reactions,
    make_envelope,
    mark_unavailable,
    merge_posts,
)


class FakeReaction:
    def __init__(self, emoji=None, doc_id=None, count=3):
        self.reaction = type("R", (), {"emoticon": emoji, "document_id": doc_id})()
        self.count = count


class FakeMessage:
    def __init__(self, reactions=None):
        self.reactions = type("R", (), {"results": reactions})()


class TestTelegramHelpers(unittest.TestCase):
    def test_merge_posts_newest_wins(self):
        old = [{"id": 1, "text": "old", "fetched_unixtime": 10}]
        new = [{"id": 1, "text": "new", "fetched_unixtime": 20}, {"id": 2, "text": "b"}]
        merged = merge_posts(old, new)
        self.assertEqual([p["id"] for p in merged], [1, 2])
        self.assertEqual(merged[0]["text"], "new")

    def test_atomic_write_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            atomic_write_json(path, {"a": 1})
            self.assertEqual(json.loads(path.read_text()), {"a": 1})

    def test_mark_unavailable_preserves_posts(self):
        with tempfile.TemporaryDirectory() as tmp:
            handle = "@gone"
            chan = Path(tmp) / handle
            (chan / "media").mkdir(parents=True)
            (chan / "posts.json").write_text(json.dumps({"posts": [{"id": 1}]}))
            result = mark_unavailable(tmp, "gone", "not_found")
            self.assertEqual(result["status"], "unavailable")
            saved = json.loads((chan / "posts.json").read_text())
            self.assertEqual(saved["posts"], [{"id": 1}])
            meta = json.loads((chan / "channel.json").read_text())
            self.assertEqual(meta["availability"], "unavailable")

    def test_reactions_keep_custom_emoji(self):
        msg = FakeMessage([FakeReaction(None, 999, 5)])
        reactions, counts = extract_reactions(msg)
        self.assertEqual(reactions[0]["custom_emoji_id"], 999)
        self.assertEqual(counts, {})

    def test_poll_from_media_shape(self):
        opt = type("O", (), {"text": "yes", "option": b"a", "voters": 4})()
        inner = type("P", (), {"question": "Q?", "answers": [opt]})()
        media = type("M", (), {"poll": type("W", (), {"poll": inner, "results": None})()})()
        msg = type("Msg", (), {"poll": None, "media": media})()
        poll = extract_poll(msg)
        self.assertEqual(poll["question"], "Q?")
        self.assertEqual(poll["answers"][0]["voters"], 4)

    def test_entities_keep_document_id(self):
        ent = type("E", (), {"offset": 0, "length": 4, "document_id": 123})()
        msg = type("Msg", (), {"entities": [ent]})()
        out = extract_entities(msg)
        self.assertEqual(out[0]["document_id"], 123)

    def test_envelope_shape(self):
        env = make_envelope("jid", "@Durov", 0, "2")
        self.assertEqual(env["kind"], "telegram_channel")
        self.assertEqual(env["account_slot"], "2")
        self.assertEqual(env["protocol"], 2)


if __name__ == "__main__":
    unittest.main()
