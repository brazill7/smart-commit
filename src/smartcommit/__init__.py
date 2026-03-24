import subprocess
import asyncio
import argparse
import sys
import itertools
from typing import Optional
import apple_fm_sdk as fm

MAX_DIFF_LENGTH = 5000
MAX_RESULT_LENGTH = 1000


class Spinner:
    def __init__(self, message: str = "Working"):
        self.message = message
        self.spinner = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
        self.task = None

    async def spin(self):
        try:
            while True:
                sys.stdout.write(f"\r\033[96m{next(self.spinner)}\033[0m {self.message}")
                sys.stdout.flush()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    async def __aenter__(self):
        self.task = asyncio.create_task(self.spin())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.task:
            self.task.cancel()
        if exc_type is None:
            sys.stdout.write(f"\r\033[92m✓\033[0m {self.message}\n")
        else:
            sys.stdout.write(f"\r\033[91m✗\033[0m {self.message}\n")
        sys.stdout.flush()


def truncate_diff(diff: str, max_length: int = MAX_DIFF_LENGTH) -> str:
    if len(diff) > max_length:
        return diff[:max_length] + "\n\n... [DIFF TRUNCATED due to length limits] ..."
    return diff


def truncate_result(text: str, max_length: int = MAX_RESULT_LENGTH) -> str:
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def clean_diff(raw_diff: str) -> str:
    cleaned_lines = []
    for line in raw_diff.split("\n"):
        if line.startswith(("diff --git", "---", "+++", "+", "-")):
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def parse_single_line_commit(response: str) -> str:
    result = response.strip().strip('"').strip("'")
    
    valid_prefixes = ("feat:", "fix:", "docs:", "style:", "refactor:", "chore:", "test:", "perf:", "build:", "ci:", "revert:")
    
    # Pass 1: Try to find a valid conventional commit line
    for line in result.split("\n"):
        line = line.strip().strip('"').strip("'")
        if line.lower().startswith(valid_prefixes):
            return line
            
    # Pass 2: Find the first line that looks like a subject line
    extracted_line = result
    if "\n" in result:
        for line in result.split("\n"):
            line = line.strip().strip('"').strip("'")
            lower_line = line.lower()
            if line and not line.startswith("-") and not lower_line.startswith(("here", "sure", "i can", "the intent", "in this", "output")):
                if len(line) < 150:  # heuristic for a subject line
                    extracted_line = line
                    break
        else:
            extracted_line = result.split("\n")[0].strip().strip('"').strip("'")
            
    # Add prefix if missing
    if not extracted_line.lower().startswith(valid_prefixes):
        # Remove any leading word that might look like a wrong prefix (e.g. "update: ")
        if ":" in extracted_line[:20]:
            parts = extracted_line.split(":", 1)
            extracted_line = parts[1].strip()
        extracted_line = f"chore: {extracted_line}"
        
    return extracted_line


async def analyze_scope(diff: str, session: fm.LanguageModelSession) -> str:
    prompt = f"""
Analyze this git diff and identify the SCOPE of changes: what files, components, or modules are affected?

Diff:
{diff}

Output MUST be a brief comma-separated list of affected areas. Maximum 20 words. No conversational text.
"""
    async with Spinner("Analyzing scope..."):
        response = await session.respond(prompt)
    return truncate_result(response.strip())


async def analyze_intent(diff: str, session: fm.LanguageModelSession, developer_context: Optional[str] = None) -> str:
    context = f"\nDeveloper context: {developer_context}" if developer_context else ""
    prompt = f"""
Analyze this git diff and identify the INTENT: why was this change made? What problem does it solve?{context}

Diff:
{diff}

Output MUST be ONE single sentence. Maximum 30 words. No conversational text.
"""
    async with Spinner("Analyzing intent..."):
        response = await session.respond(prompt)
    return truncate_result(response.strip())


async def analyze_changes(diff: str, session: fm.LanguageModelSession) -> str:
    prompt = f"""
Analyze this git diff and identify the SPECIFIC CHANGES: what functions, logic, or code patterns changed?

Diff:
{diff}

Output MUST be a maximum of 3 short bullet points. Do NOT output large amounts of text. Keep it extremely brief. No conversational text.
"""
    async with Spinner("Analyzing changes..."):
        response = await session.respond(prompt)
    return truncate_result(response.strip())


async def synthesize_message(scope: str, intent: str, changes: str, session: fm.LanguageModelSession, previous_commits: Optional[list[str]] = None) -> str:
    previous_rejections = ""
    if previous_commits:
        rejections_list = "\n".join([f"- {c}" for c in previous_commits])
        previous_rejections = f"\n\nIMPORTANT: You previously suggested these commits, which the user rejected. Come up with a MORE DESCRIPTIVE message DIFFERENT from these, STILL WITH THE MANDATORY PREFIX:\n{rejections_list}\n"

    prompt = f"""
Generate EXACTLY ONE Conventional Commit message based on this analysis. Do NOT output conversational text.

Scope: {scope}
Intent: {intent}
Changes: {changes}{previous_rejections}

Rules:
1. Output ONE single line only.
2. Do NOT output any bullet points, lists, or multiple options.
3. MUST start with a prefix: feat:, fix:, docs:, style:, refactor:, chore:, test:
4. Do NOT wrap in quotes.

Example Output:
feat: add StatsView with sun exposure chart to Daylight project

Actual Output:
"""
    async with Spinner("Synthesizing commit message..."):
        response = await session.respond(prompt)
    return parse_single_line_commit(response)


async def quick_mode(diff: str, developer_context: Optional[str] = None, previous_commits: Optional[list[str]] = None) -> Optional[str]:
    if not diff:
        return None

    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Apple Intelligence unavailable: {reason}")
        return None

    session = fm.LanguageModelSession()

    context_instruction = ""
    if developer_context:
        context_instruction = f"\nAdditional context from the developer to include/consider:\n\"{developer_context}\"\n"

    previous_rejections = ""
    if previous_commits:
        rejections_list = "\n".join([f"- {c}" for c in previous_commits])
        previous_rejections = f"\nIMPORTANT: You previously suggested these commits, which the user rejected. Come up with a MORE DESCRIPTIVE message DIFFERENT from these, STILL WITH THE MANDATORY PREFIX:\n{rejections_list}\n"

    prompt = f"""
        Generate EXACTLY ONE commit message using the Conventional Commits standard for this diff.
        
        Rules:
        1. ONLY output the commit message. NO conversational text like "Here is the commit...".
        2. Output ONE single line only.
        3. DO NOT echo back the code diff.
        4. MUST start with a prefix: feat:, fix:, docs:, style:, refactor:, chore:, test:.
        
        Actual Diff to analyze:
        {diff}
        {context_instruction}{previous_rejections}
        
        Example Output:
        feat: update login component to handle edge cases
        
        Actual Output:
        """

    async with Spinner("Analyzing diff (quick mode)..."):
        response = await session.respond(prompt)
    return parse_single_line_commit(response)


async def detailed_mode(diff: str, developer_context: Optional[str] = None, previous_commits: Optional[list[str]] = None) -> Optional[str]:
    if not diff:
        return None

    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"\033[91mApple Intelligence unavailable: {reason}\033[0m")
        return None

    print("\033[93mAnalyzing diff (detailed mode)...\033[0m")

    commit_msg = None
    try:
        session_scope = fm.LanguageModelSession()
        session_intent = fm.LanguageModelSession()
        session_changes = fm.LanguageModelSession()
        session_synth = fm.LanguageModelSession()

        scope_result = await analyze_scope(diff, session_scope)
        intent_result = await analyze_intent(diff, session_intent, developer_context)
        changes_result = await analyze_changes(diff, session_changes)
        
        commit_msg = await synthesize_message(scope_result, intent_result, changes_result, session_synth, previous_commits)

    except Exception as e:
        error_msg = str(e)
        if "Context window" in error_msg or "context" in error_msg.lower() or "limit" in error_msg.lower():
            print("Diff too large for detailed mode. Falling back to quick mode...")
            commit_msg = await quick_mode(diff, developer_context, previous_commits)
            if commit_msg:
                print("(Used quick mode as fallback)")
        else:
            print(f"Error in parallel analysis: {error_msg}")
            return None

    return commit_msg


async def commit_flow(developer_context: Optional[str] = None, quick: bool = False) -> None:
    diff_process = subprocess.run(['git', 'diff', '--staged'], capture_output=True, text=True)
    raw_diff = diff_process.stdout.strip()

    if not raw_diff:
        print("No staged changes found. Run `git add` first!")
        return

    stat_process = subprocess.run(['git', 'diff', '--staged', '--stat'], capture_output=True, text=True)
    diff_stat = stat_process.stdout.strip()

    cleaned_diff = clean_diff(raw_diff)
    diff = f"{diff_stat}\n\n{cleaned_diff}"

    if len(diff) > MAX_DIFF_LENGTH:
        print("Warning: Large diff detected.")
        print("Tip: This tool works best with smaller commits. Consider breaking up large changes into multiple commits.")
        diff = truncate_diff(diff)

    commit_msg = None
    previous_commits = []

    while True:
        if quick:
            commit_msg = await quick_mode(diff, developer_context, previous_commits)
        else:
            commit_msg = await detailed_mode(diff, developer_context, previous_commits)

        if not commit_msg:
            return

        print(f"\nSuggested commit: \033[92m{commit_msg}\033[0m")
        user_input = input("Accept commit? (y/n/r): ")

        if user_input.lower() == 'y':
            subprocess.run(['git', 'commit', '-m', commit_msg])
            print("Committed successfully!")
            return
        elif user_input.lower() == 'r':
            print("Retrying...\n")
            if commit_msg not in previous_commits:
                previous_commits.append(commit_msg)
            if len(previous_commits) > 3:
                previous_commits = previous_commits[-3:]
            continue
        else:
            print("Commit aborted.")
            return


def main():
    parser = argparse.ArgumentParser(description="Generate smart Git commits using Apple Intelligence.")
    parser.add_argument(
        '-c', '--context',
        type=str,
        help='Additional context or intent to guide the AI (e.g., "fixes ticket #123")'
    )
    parser.add_argument(
        '-q', '--quick',
        action='store_true',
        help='Use quick single-pass mode (faster but less detailed)'
    )

    args = parser.parse_args()

    if args.quick:
        print("Running in --quick mode\n")

    asyncio.run(commit_flow(developer_context=args.context, quick=args.quick))


if __name__ == "__main__":
    main()
