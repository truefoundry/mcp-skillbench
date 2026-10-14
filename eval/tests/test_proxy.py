from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL / "proxy"))
sys.path.insert(0, str(EVAL / "scripts"))

from cache import CacheEntry, ReplayCache, cache_key, normalize  # noqa: E402
from cursor_adapter import build_prompt, seed_workspace  # noqa: E402
from experiment import load_experiment  # noqa: E402
from policy import is_write  # noqa: E402
from run_eval import render  # noqa: E402
from report import passes  # noqa: E402
from score import score_item  # noqa: E402
from server import ReplayServer  # noqa: E402


class CacheTests(unittest.TestCase):
    def test_normalize_ignores_only_nonsemantic_controls(self) -> None:
        args = {
            "query": "launch",
            "limit": 20,
            "cursor": "opaque",
            "after": "2026-01-01",
        }
        self.assertEqual(
            normalize(args),
            {"after": "2026-01-01", "query": "launch"},
        )

    def test_cache_key_is_stable_across_key_order_and_limit(self) -> None:
        first = cache_key("linear", "list_issues", {"query": "x", "limit": 10})
        second = cache_key("linear", "list_issues", {"limit": 99, "query": "x"})
        self.assertEqual(first, second)

    def test_cache_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = ReplayCache(Path(directory))
            entry = CacheEntry("linear", "get_issue", {"id": "ENG-1"}, {"id": "1"})
            cache.put(entry)
            self.assertEqual(
                cache.get("linear", "get_issue", {"id": "ENG-1"}),
                {"id": "1"},
            )


class PolicyTests(unittest.TestCase):
    def test_write_classification(self) -> None:
        self.assertTrue(is_write("linear", "save_issue"))
        self.assertTrue(is_write("linear", "merge_diff"))
        self.assertTrue(is_write("linear", "prepare_attachment_upload"))
        self.assertTrue(is_write("slack", "slack_send_message_draft"))
        self.assertTrue(is_write("slack", "slack_get_file_upload_url"))
        self.assertFalse(is_write("linear", "get_issue"))
        self.assertFalse(is_write("slack", "slack_read_channel"))


class RunnerTests(unittest.TestCase):
    def test_fixture_rendering_requires_every_value(self) -> None:
        self.assertEqual(render("Issue {{issue_id}}", {"issue_id": "ENG-1"}), "Issue ENG-1")
        with self.assertRaises(KeyError):
            render("Issue {{issue_id}}", {})

    def test_skill_text_is_never_inlined_in_prompt(self) -> None:
        baseline = build_prompt({"prompt": "task", "skill_path": None})
        treatment = build_prompt({"prompt": "task", "skill_path": "/skill.md"})
        self.assertEqual(baseline, treatment)
        self.assertNotIn("<operational_skills>", treatment)

    def test_prompt_distinguishes_requested_writes_from_destructive_actions(self) -> None:
        prompt = build_prompt({"prompt": "task"})
        self.assertIn("send, draft, schedule, upload, create, or update", prompt)
        self.assertIn("delete existing data or merge a pull", prompt)

    def test_only_treatment_seeds_native_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "linear"
            (source / "references").mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: test\n---\nbody\n")
            (source / "references" / "planning.md").write_text("cycle id\n")
            baseline = root / "baseline"
            treatment = root / "treatment"
            baseline.mkdir()
            treatment.mkdir()
            self.assertIsNone(
                seed_workspace(
                    baseline,
                    {"skill_path": None, "skill_directory": "linear-app-skill"},
                )
            )
            installed = seed_workspace(
                treatment,
                {
                    "skill_path": str(source),
                    "skill_directory": "linear-app-skill",
                },
            )
            skill_dir = treatment / ".cursor/skills/linear-app-skill"
            self.assertEqual(installed, skill_dir / "SKILL.md")
            self.assertFalse((baseline / ".cursor").exists())
            self.assertEqual(installed.read_text(), (source / "SKILL.md").read_text())
            self.assertEqual(
                (skill_dir / "references" / "planning.md").read_text(),
                "cycle id\n",
            )

    def test_single_file_skill_installs_as_skill_md(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "linear.md"
            source.write_text("---\nname: test\n---\nbody\n")
            workspace = root / "treatment"
            workspace.mkdir()
            installed = seed_workspace(
                workspace,
                {
                    "skill_path": str(source),
                    "skill_directory": "linear-app-skill",
                },
            )
            self.assertEqual(
                installed,
                workspace / ".cursor/skills/linear-app-skill/SKILL.md",
            )
            self.assertEqual(installed.read_text(), source.read_text())
            self.assertFalse(
                (workspace / ".cursor/skills/linear-app-skill/references").exists()
            )

    def test_confirmation_marker_counts_without_destructive_call(self) -> None:
        question = {
            "id": "delete",
            "gold": {
                "resolution_prefix_allowed": ["get_issue"],
                "primary_tools": ["delete_attachment"],
                "acceptable_sequences": [["delete_attachment"]],
                "forbidden_first_tools": ["save_issue"],
                "required_arguments": {},
                "must_confirm": True,
            },
        }
        run = {
            "tool_calls": [],
            "confirmation_requested": True,
            "confirmation_tool": "delete_attachment",
        }
        scored = score_item(question, run)
        self.assertTrue(scored["passed_process"])
        self.assertEqual(scored["scores"]["goal_effectiveness"], 1.0)


class SequenceScoreTests(unittest.TestCase):
    def test_resolution_prefixes_do_not_reduce_efficiency(self) -> None:
        question = {
            "id": "resolved-write",
            "gold": {
                "resolution_prefix_allowed": ["slack_search_channels"],
                "primary_tools": ["slack_send_message_draft"],
                "acceptable_sequences": [["slack_send_message_draft"]],
                "forbidden_first_tools": [],
                "forbidden_tools": [],
                "required_arguments": {},
                "must_confirm": False,
            },
        }
        run = {
            "tool_calls": [
                {"tool": "slack_search_channels"},
                {"tool": "slack_send_message_draft"},
            ]
        }
        scored = score_item(question, run)
        self.assertEqual(scored["scores"]["execution_efficiency"], 1.0)

    MULTI_HOP = {
        "id": "chain",
        "gold": {
            "resolution_prefix_allowed": ["list_teams"],
            "primary_tools": ["get_issue"],
            "acceptable_sequences": [["get_issue", "list_cycles"]],
            "forbidden_first_tools": ["list_cycles"],
            "forbidden_tools": ["list_issues"],
            "required_arguments": {},
            "must_confirm": False,
        },
    }

    def test_right_first_call_but_incomplete_chain_fails(self) -> None:
        scored = score_item(self.MULTI_HOP, {"tool_calls": [{"tool": "get_issue"}]})
        self.assertEqual(scored["scores"]["discoverability"], 1.0)
        self.assertEqual(scored["scores"]["sequence_adherence"], 0.0)
        self.assertFalse(scored["passed_process"])

    def test_resolution_prefix_does_not_break_the_chain(self) -> None:
        run = {
            "tool_calls": [
                {"tool": "list_teams"},
                {"tool": "get_issue"},
                {"tool": "list_cycles"},
            ]
        }
        self.assertTrue(score_item(self.MULTI_HOP, run)["passed_process"])

    def test_fallback_after_empty_result_is_penalized(self) -> None:
        run = {
            "tool_calls": [
                {"tool": "get_issue"},
                {"tool": "list_cycles"},
                {"tool": "list_issues"},
            ]
        }
        scored = score_item(self.MULTI_HOP, run)
        self.assertEqual(scored["forbidden_tools_used"], ["list_issues"])
        self.assertEqual(scored["scores"]["discoverability"], 0.0)
        self.assertEqual(scored["scores"]["security_policy"], 0.0)
        self.assertFalse(scored["passed_process"])

    def test_capability_gap_passes_only_without_substantive_calls(self) -> None:
        question = {
            "id": "gap",
            "gold": {
                "resolution_prefix_allowed": ["slack_get_reactions"],
                "primary_tools": [],
                "acceptable_sequences": [[]],
                "forbidden_first_tools": ["slack_add_reaction"],
                "forbidden_tools": ["slack_add_reaction"],
                "required_arguments": {},
                "must_confirm": False,
            },
        }
        reported = score_item(question, {"tool_calls": [{"tool": "slack_get_reactions"}]})
        self.assertTrue(reported["passed_process"])
        substituted = score_item(question, {"tool_calls": [{"tool": "slack_add_reaction"}]})
        self.assertFalse(substituted["passed_process"])

    def test_builtin_skill_read_is_not_scored_as_mcp_call(self) -> None:
        run = {
            "tool_calls": [
                {
                    "tool": "read",
                    "source": "builtin",
                    "arguments": {"path": ".cursor/skills/x/SKILL.md"},
                },
                {"tool": "get_issue", "source": "mcp"},
                {"tool": "list_cycles", "source": "mcp"},
            ]
        }
        scored = score_item(self.MULTI_HOP, run)
        self.assertTrue(scored["passed_process"])
        self.assertEqual(scored["substantive_tools"], ["get_issue", "list_cycles"])


class ExperimentIsolationTests(unittest.TestCase):
    def test_linear_snapshot_contains_only_linear_tools(self) -> None:
        experiment = load_experiment("linear")
        snapshot = json.loads(experiment.tools.read_text())
        self.assertEqual(set(snapshot["servers"]), {"linear"})
        names = {
            tool["tool"]
            for server in snapshot["servers"].values()
            for tool in server["tools"]
        }
        self.assertFalse(any(name.startswith("slack_") for name in names))

    def test_linear_bank_and_pilot_have_no_cross_server_items(self) -> None:
        experiment = load_experiment("linear")
        questions = [
            json.loads(line)
            for line in experiment.questions.read_text().splitlines()
            if line.strip()
        ]
        ids = {question["id"] for question in questions}
        self.assertEqual(len(questions), 19)
        self.assertTrue(all(question["servers"] == ["linear"] for question in questions))
        self.assertLessEqual(set(experiment.config["pilot_ids"]), ids)

    def test_slack_snapshot_contains_only_slack_tools(self) -> None:
        experiment = load_experiment("slack")
        snapshot = json.loads(experiment.tools.read_text())
        self.assertEqual(set(snapshot["servers"]), {"slack"})
        names = {
            tool["tool"]
            for server in snapshot["servers"].values()
            for tool in server["tools"]
        }
        self.assertTrue(all(name.startswith("slack_") for name in names))

    def test_slack_bank_and_pilot_have_no_cross_server_items(self) -> None:
        experiment = load_experiment("slack")
        questions = [
            json.loads(line)
            for line in experiment.questions.read_text().splitlines()
            if line.strip()
        ]
        ids = {question["id"] for question in questions}
        self.assertEqual(len(questions), 21)
        self.assertTrue(all(question["servers"] == ["slack"] for question in questions))
        self.assertLessEqual(set(experiment.config["pilot_ids"]), ids)

    def test_report_requires_sequence_adherence(self) -> None:
        result = {
            "scores": {
                "discoverability": 1,
                "sequence_adherence": 0,
                "security_policy": 1,
                "goal_effectiveness": 1,
                "factual_correctness": 1,
                "execution_efficiency": 1,
            }
        }
        self.assertFalse(passes(result))


class ServerTests(unittest.TestCase):
    def test_read_hit_miss_and_write_intercept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = {
                "servers": {
                    "linear": {
                        "tools": [
                            {
                                "tool": "get_issue",
                                "description": "read",
                                "inputSchema": {"type": "object"},
                            },
                            {
                                "tool": "save_issue",
                                "description": "write",
                                "inputSchema": {"type": "object"},
                            },
                        ]
                    },
                    "slack": {"tools": []},
                }
            }
            tools_path = root / "tools.json"
            tools_path.write_text(json.dumps(tools))
            cache = ReplayCache(root / "cache")
            cache.put(CacheEntry("linear", "get_issue", {"id": "ENG-1"}, {"title": "x"}))
            server = ReplayServer(tools_path, root / "cache")

            hit = server.handle(
                {
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "get_issue", "arguments": {"id": "ENG-1"}},
                }
            )
            self.assertFalse(hit["result"]["isError"])

            miss = server.handle(
                {
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "get_issue", "arguments": {"id": "ENG-2"}},
                }
            )
            self.assertTrue(miss["result"]["isError"])

            write = server.handle(
                {
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "save_issue", "arguments": {"title": "x"}},
                }
            )
            body = json.loads(write["result"]["content"][0]["text"])
            self.assertTrue(body["synthetic"])

    def test_default_fallback_serves_unrecorded_query_phrasings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = {
                "servers": {
                    "slack": {
                        "tools": [
                            {
                                "tool": "slack_search_public",
                                "description": "search",
                                "inputSchema": {"type": "object"},
                            }
                        ]
                    }
                }
            }
            tools_path = root / "tools.json"
            tools_path.write_text(json.dumps(tools))
            cache = ReplayCache(root / "cache")
            cache.put_default(
                CacheEntry(
                    "slack",
                    "slack_search_public",
                    {"query": "recorded", "content_types": "files"},
                    {"results": ["canvas"]},
                )
            )
            server = ReplayServer(tools_path, root / "cache")

            rephrased = server.handle(
                {
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "slack_search_public",
                        "arguments": {"query": "different wording", "content_types": "files"},
                    },
                }
            )
            self.assertFalse(rephrased["result"]["isError"])
            self.assertEqual(
                json.loads(rephrased["result"]["content"][0]["text"]),
                {"results": ["canvas"]},
            )

            other_scope = server.handle(
                {
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "slack_search_public",
                        "arguments": {"query": "different wording", "content_types": "messages"},
                    },
                }
            )
            self.assertTrue(other_scope["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
