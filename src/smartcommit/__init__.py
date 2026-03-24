import subprocess
import asyncio
import argparse
from typing import Optional
import apple_fm_sdk as fm


async def analyze_scope(diff: str, session: fm.LanguageModelSession) -> str:
    prompt = f"""
            Analyze this git diff and identify the SCOPE of changes: what files, components, or modules are affected?
            
            Diff:
            {diff}
            
            Output ONLY a brief list of affected areas (e.g., "user_auth.py, login component, API routes"). No other text.
            """
    response = await session.respond(prompt)
    return response.strip()


async def analyze_intent(diff: str, session: fm.LanguageModelSession, developer_context: Optional[str] = None) -> str:
    context = f"\nDeveloper context: {developer_context}" if developer_context else ""
    prompt = f"""
        Analyze this git diff and identify the INTENT: why was this change made? What problem does it solve?{context}
        
        Diff:
        {diff}
        
        Output ONLY a one-sentence intent summary. No other text.
        """
    response = await session.respond(prompt)
    return response.strip()


async def analyze_changes(diff: str, session: fm.LanguageModelSession) -> str:
    prompt = f"""
        Analyze this git diff and identify the SPECIFIC CHANGES: what functions, logic, or code patterns changed?
        
        Diff:
        {diff}
        
        Output ONLY a brief list of what changed (e.g., "added calculateTotal function, refactored validation logic"). No other text.
        """
    response = await session.respond(prompt)
    return response.strip()


async def synthesize_message(scope: str, intent: str, changes: str, session: fm.LanguageModelSession) -> str:
    prompt = f"""
        You are a Git commit message generator. Using the following analysis, generate a SINGLE Conventional Commit message.
        
        Scope (what files/components): {scope}
        Intent (why): {intent}
        Changes (what): {changes}
        
        Rules:
        - Use prefix: feat:, fix:, docs:, style:, refactor:, chore:
        - Keep it under 72 characters if possible
        - ONLY output the commit message, no quotes, no explanation
        
        Output:
        """
    response = await session.respond(prompt)
    return response.strip().strip('"').strip("'")


async def quick_mode(developer_context: Optional[str] = None) -> Optional[str]:
    diff_process = subprocess.run(['git', 'diff', '--staged'], capture_output=True, text=True)
    diff = diff_process.stdout.strip()

    if not diff:
        print("No staged changes found. Run `git add` first!")
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

    prompt = f"""
        You are a strictly formatted Git commit generator. Analyze the following code diff and generate a single commit message using the Conventional Commits standard.
        
        Allowed prefixes: feat:, fix:, docs:, style:, refactor:, chore:
        
        Rules:
        - ONLY output the commit message. No conversational text.
        - Do not wrap the output in quotes.
        - Incorporate any additional context provided by the developer.
        
        Examples:
        Diff: + function calculateTotal(a, b) {{ return a + b; }}
        Output: feat: add calculateTotal function, which adds a and b and returns the total.
        
        Actual Diff to analyze:
        {diff}
        {context_instruction}
        
        Analyze the following code diff and generate a single commit message using the Conventional Commits standard.
        
        Allowed prefixes: feat:, fix:, docs:, style:, refactor:, chore:
        
        Output:
        """

    print("Analyzing diff (quick mode)...")
    response = await session.respond(prompt)
    return response.strip().strip('"').strip("'")


async def detailed_mode(developer_context: Optional[str] = None) -> Optional[str]:
    diff_process = subprocess.run(['git', 'diff', '--staged'], capture_output=True, text=True)
    diff = diff_process.stdout.strip()

    if not diff:
        print("No staged changes found. Run `git add` first!")
        return None

    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if not is_available:
        print(f"Apple Intelligence unavailable: {reason}")
        return None

    session = fm.LanguageModelSession()

    print("Analyzing diff (detailed mode - 3 parallel agents)...")

    commit_msg = None
    try:
        async with asyncio.TaskGroup() as tg:
            task_scope = tg.create_task(analyze_scope(diff, session))
            task_intent = tg.create_task(analyze_intent(diff, session, developer_context))
            task_changes = tg.create_task(analyze_changes(diff, session))

        scope_result = task_scope.result()
        intent_result = task_intent.result()
        changes_result = task_changes.result()

        print(f"  Scope: {scope_result[:50]}...")
        print(f"  Intent: {intent_result[:50]}...")
        print(f"  Changes: {changes_result[:50]}...")

        print("Synthesizing results...")
        commit_msg = await synthesize_message(scope_result, intent_result, changes_result, session)

    except* Exception as e:
        print(f"Error in parallel analysis: {e}")

    return commit_msg


async def commit_flow(developer_context: Optional[str] = None, quick: bool = False) -> None:
    commit_msg = None
    max_retries = 3

    for attempt in range(max_retries):
        if quick:
            commit_msg = await quick_mode(developer_context)
        else:
            commit_msg = await detailed_mode(developer_context)

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
            continue
        else:
            print("Commit aborted.")
            return

    print("Max retries reached. Commit aborted.")


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
