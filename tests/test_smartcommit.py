import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import subprocess
import sys
from io import StringIO
import importlib.util

sys.path.insert(0, '..')

spec = importlib.util.find_spec('apple_fm_sdk')
if spec is None:
    sys.modules['apple_fm_sdk'] = MagicMock()

from smartcommit import (
    quick_mode,
    detailed_mode,
    analyze_scope,
    analyze_intent,
    analyze_changes,
    synthesize_message,
    commit_flow,
)


class MockLanguageModelSession:
    def __init__(self):
        pass

    async def respond(self, prompt: str) -> str:
        if "SCOPE" in prompt:
            return "user_auth.py, login.py, auth module"
        elif "INTENT" in prompt:
            return "To improve user authentication security"
        elif "SPECIFIC CHANGES" in prompt:
            return "added hashPassword function, updated validation"
        elif "synthesize" in prompt.lower() or "generate" in prompt.lower():
            return "feat: add hashPassword function for secure auth"
        else:
            return "feat: update authentication module"


class MockSystemLanguageModel:
    def is_available(self):
        return True, ""


class TestQuickMode(unittest.IsolatedAsyncioTestCase):
    @patch('smartcommit.subprocess.run')
    @patch('smartcommit.fm.SystemLanguageModel')
    @patch('smartcommit.fm.LanguageModelSession')
    def test_quick_mode_no_staged_changes(self, mock_session, mock_model, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        
        result = asyncio.run(quick_mode())
        
        self.assertIsNone(result)

    @patch('smartcommit.subprocess.run')
    @patch('smartcommit.fm.SystemLanguageModel')
    @patch('smartcommit.fm.LanguageModelSession')
    def test_quick_mode_success(self, mock_session, mock_model, mock_run):
        mock_run.return_value = MagicMock(stdout="+ def new_func(): pass")
        mock_model.return_value = MockSystemLanguageModel()
        mock_session.return_value = MockLanguageModelSession()
        
        result = asyncio.run(quick_mode())
        
        self.assertIsNotNone(result)
        self.assertIn("feat:", result)

    @patch('smartcommit.subprocess.run')
    @patch('smartcommit.fm.SystemLanguageModel')
    @patch('smartcommit.fm.LanguageModelSession')
    def test_quick_mode_with_context(self, mock_session, mock_model, mock_run):
        mock_run.return_value = MagicMock(stdout="+ def new_func(): pass")
        mock_model.return_value = MockSystemLanguageModel()
        mock_session.return_value = MockLanguageModelSession()
        
        result = asyncio.run(quick_mode(developer_context="fixes ticket #123"))
        
        self.assertIsNotNone(result)


class TestDetailedMode(unittest.IsolatedAsyncioTestCase):
    @patch('smartcommit.subprocess.run')
    @patch('smartcommit.fm.SystemLanguageModel')
    @patch('smartcommit.fm.LanguageModelSession')
    def test_detailed_mode_no_staged(self, mock_session, mock_model, mock_run):
        mock_run.return_value = MagicMock(stdout="")
        
        result = asyncio.run(detailed_mode())
        
        self.assertIsNone(result)

    @patch('smartcommit.subprocess.run')
    @patch('smartcommit.fm.SystemLanguageModel')
    @patch('smartcommit.fm.LanguageModelSession')
    def test_detailed_mode_success(self, mock_session, mock_model, mock_run):
        mock_run.return_value = MagicMock(stdout="+ def new_func(): pass")
        mock_model.return_value = MockSystemLanguageModel()
        mock_session.return_value = MockLanguageModelSession()
        
        result = asyncio.run(detailed_mode())
        
        self.assertIsNotNone(result)
        self.assertIn("feat:", result)


class TestAnalyzeFunctions(unittest.IsolatedAsyncioTestCase):
    @patch('smartcommit.fm.LanguageModelSession')
    def test_analyze_scope(self, mock_session):
        mock_session.return_value = MockLanguageModelSession()
        
        result = asyncio.run(analyze_scope("+ new file", mock_session.return_value))
        
        self.assertIsNotNone(result)
        self.assertIn("user_auth.py", result)

    @patch('smartcommit.fm.LanguageModelSession')
    def test_analyze_intent(self, mock_session):
        mock_session.return_value = MockLanguageModelSession()
        
        result = asyncio.run(analyze_intent("+ new file", mock_session.return_value))
        
        self.assertIsNotNone(result)

    @patch('smartcommit.fm.LanguageModelSession')
    def test_analyze_intent_with_context(self, mock_session):
        mock_session.return_value = MockLanguageModelSession()
        
        result = asyncio.run(
            analyze_intent("+ new file", mock_session.return_value, "fixes #456")
        )
        
        self.assertIsNotNone(result)

    @patch('smartcommit.fm.LanguageModelSession')
    def test_analyze_changes(self, mock_session):
        mock_session.return_value = MockLanguageModelSession()
        
        result = asyncio.run(analyze_changes("+ new file", mock_session.return_value))
        
        self.assertIsNotNone(result)


class TestSynthesizeMessage(unittest.IsolatedAsyncioTestCase):
    @patch('smartcommit.fm.LanguageModelSession')
    def test_synthesize_message(self, mock_session):
        mock_session.return_value = MockLanguageModelSession()
        
        result = asyncio.run(synthesize_message(
            "auth.py",
            "improve security",
            "added hash function",
            mock_session.return_value
        ))
        
        self.assertIsNotNone(result)
        self.assertIn("feat:", result)


class TestCommitFlow(unittest.IsolatedAsyncioTestCase):
    @patch('smartcommit.subprocess.run')
    @patch('smartcommit.input', return_value='y')
    @patch('smartcommit.fm.SystemLanguageModel')
    @patch('smartcommit.fm.LanguageModelSession')
    def test_commit_flow_accept(self, mock_session, mock_model, mock_input, mock_run):
        mock_run.return_value = MagicMock(stdout="+ test change")
        mock_model.return_value = MockSystemLanguageModel()
        mock_session.return_value = MockLanguageModelSession()
        
        asyncio.run(commit_flow(quick=True))
        
        mock_run.assert_called()

    @patch('smartcommit.subprocess.run')
    @patch('smartcommit.input', return_value='n')
    @patch('smartcommit.fm.SystemLanguageModel')
    @patch('smartcommit.fm.LanguageModelSession')
    def test_commit_flow_reject(self, mock_session, mock_model, mock_input, mock_run):
        mock_run.return_value = MagicMock(stdout="+ test change")
        mock_model.return_value = MockSystemLanguageModel()
        mock_session.return_value = MockLanguageModelSession()
        
        asyncio.run(commit_flow(quick=True))
        
        self.assertEqual(mock_run.call_count, 1)

    @patch('smartcommit.subprocess.run')
    @patch('smartcommit.input', side_effect=['r', 'y'])
    @patch('smartcommit.fm.SystemLanguageModel')
    @patch('smartcommit.fm.LanguageModelSession')
    def test_commit_flow_retry(self, mock_session, mock_model, mock_input, mock_run):
        mock_run.return_value = MagicMock(stdout="+ test change")
        mock_model.return_value = MockSystemLanguageModel()
        mock_session.return_value = MockLanguageModelSession()
        
        asyncio.run(commit_flow(quick=True))
        
        self.assertGreater(mock_run.call_count, 1)


class TestCLIParsing(unittest.TestCase):
    def test_quick_flag_parsing(self):
        with patch('sys.argv', ['smartcommit.py', '-q']):
            from smartcommit import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument('-q', '--quick', action='store_true')
            args = parser.parse_args()
            self.assertTrue(args.quick)

    def test_context_flag_parsing(self):
        with patch('sys.argv', ['smartcommit.py', '-c', 'test context']):
            from smartcommit import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument('-c', '--context', type=str)
            args = parser.parse_args()
            self.assertEqual(args.context, 'test context')

    def test_combined_flags(self):
        with patch('sys.argv', ['smartcommit.py', '-q', '-c', 'test']):
            from smartcommit import argparse
            parser = argparse.ArgumentParser()
            parser.add_argument('-q', '--quick', action='store_true')
            parser.add_argument('-c', '--context', type=str)
            args = parser.parse_args()
            self.assertTrue(args.quick)
            self.assertEqual(args.context, 'test')


if __name__ == '__main__':
    unittest.main()
