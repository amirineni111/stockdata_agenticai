"""
Agent 7: Report Compiler Agent
Role: Financial Report Editor
Compiles all agent findings into a structured HTML briefing
and sends it via email.
"""

from crewai import Agent, LLM

from config.settings import LLM_MODEL, AGENT_MAX_ITER, AGENT_VERBOSE, AGENT_MAX_RPM
from tools.email_tool import SendEmailTool


def create_report_compiler_agent() -> Agent:
    """Create and return the Report Compiler Agent."""

    email_tool = SendEmailTool()

    llm = LLM(
        model=f"anthropic/{LLM_MODEL}",
        max_tokens=8192,
        temperature=0.4,
    )

    agent = Agent(
        role="Financial Report Editor",
        goal=(
            "Compile all findings from the specialist agents into a "
            "professional, well-structured HTML email briefing. "
            "The briefing should have clear sections for: "
            "1) Market Overview (NASDAQ & NSE), "
            "2) ML Model Health Scorecard, "
            "3) Top Trade Opportunities (TIER 1 & 2), "
            "4) Active Technical Signals, "
            "5) Forex Outlook, "
            "6) Risk Warnings & Alerts. "
            "Use tables, color coding (green for bullish/positive, "
            "red for bearish/negative), and concise bullet points. "
            "Then send the email with an appropriate subject line."
        ),
        backstory=(
            "You are an expert financial report editor who transforms "
            "raw analytical data into elegant, scannable reports. "
            "You understand that busy traders need information presented "
            "in a hierarchy -- most important items first, with clear "
            "visual cues (colors, bold, tables) to quickly spot what "
            "matters. You produce clean, professional HTML emails that "
            "render well in Outlook and mobile email clients."
        ),
        tools=[email_tool],
        llm=llm,
        verbose=AGENT_VERBOSE,
        max_iter=AGENT_MAX_ITER,
        max_rpm=AGENT_MAX_RPM,
        allow_delegation=False,
    )

    return agent
