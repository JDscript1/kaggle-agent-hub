from __future__ import annotations

import gradio as gr
import inspect

from core.config import CONFIG
from core.logging_store import LOGS
from core.runner import availability, run_agent
from core.session import new_session
from core.system_info import collect
from ui.chat import respond
from ui.files import export_zip, open_file, refresh_tree, save_file, upload_files
from ui.providers import initial_provider, provider_defaults
from providers.registry import names


CSS = """
#kah-title { margin-bottom: 0.2rem; }
.kah-note { opacity: 0.8; }
"""


def build_app() -> gr.Blocks:
    first = initial_provider()
    first_model, first_base, first_env, first_note = provider_defaults(first)

    with gr.Blocks(title="Kaggle Agent Hub") as demo:
        session_state = gr.State(new_session())
        gr.Markdown("# Kaggle Agent Hub", elem_id="kah-title")
        gr.Markdown("Multi-provider AI workspace for Kaggle, Colab, Linux and local Python. Secrets stay in memory unless you provide them through environment/Kaggle Secrets.", elem_classes=["kah-note"])

        with gr.Tab("Chat"):
            with gr.Row():
                provider = gr.Dropdown(names(), value=first, label="Provider", scale=1)
                model = gr.Textbox(value=first_model, label="Model", scale=2)
            with gr.Accordion("Provider connection", open=False):
                api_key = gr.Textbox(label="API key (optional if set in environment/Kaggle Secrets)", type="password")
                base_url = gr.Textbox(value=first_base, label="Base URL")
                env_hint = gr.Markdown(f"Secret name: `{first_env}`  \n{first_note}")
            with gr.Accordion("Generation settings", open=False):
                system_prompt = gr.Textbox(
                    value="You are a helpful coding assistant. Be precise, concise, and safe with file operations.",
                    label="System prompt",
                    lines=3,
                )
                include_workspace = gr.Checkbox(value=True, label="Include a text snapshot of workspace files")
                temperature = gr.Slider(0, 2, value=0.2, step=0.05, label="Temperature")
                max_tokens = gr.Slider(256, 16384, value=4096, step=256, label="Max output tokens")

            chatbot_kwargs = {"height": 520, "label": "Conversation"}
            if "type" in inspect.signature(gr.Chatbot).parameters:
                chatbot_kwargs["type"] = "messages"
            chatbot = gr.Chatbot(**chatbot_kwargs)
            prompt = gr.Textbox(label="Message", placeholder="Ask the model about your project…", lines=3)
            with gr.Row():
                send = gr.Button("Send", variant="primary")
                clear = gr.Button("Clear chat")

            def change_provider(name):
                m, b, e, note = provider_defaults(name)
                return m, b, f"Secret name: `{e}`  \n{note}"

            provider.change(change_provider, provider, [model, base_url, env_hint])
            send.click(
                respond,
                [prompt, chatbot, session_state, provider, model, api_key, base_url, temperature, max_tokens, system_prompt, include_workspace],
                [chatbot, session_state, prompt],
            )
            prompt.submit(
                respond,
                [prompt, chatbot, session_state, provider, model, api_key, base_url, temperature, max_tokens, system_prompt, include_workspace],
                [chatbot, session_state, prompt],
            )
            clear.click(lambda: ([], new_session(), ""), outputs=[chatbot, session_state, prompt])

        with gr.Tab("CLI Agents"):
            gr.Markdown(
                "Use authenticated local CLI agents against the workspace. This tab does not copy browser/session credentials into the app. "
                "Authenticate each CLI using its own supported login flow first."
            )
            cli_agent = gr.Dropdown(["Codex CLI", "Claude Code", "Gemini CLI", "Custom CLI"], value="Codex CLI", label="Agent")
            custom_command = gr.Textbox(label="Custom command prefix", placeholder="Example: kimi ...", visible=True)
            cli_prompt = gr.Textbox(label="Agent task", lines=5, placeholder="Inspect the project, implement the requested change, run tests…")
            timeout = gr.Slider(60, 3600, value=900, step=60, label="Timeout (seconds)")
            run_btn = gr.Button("Run agent", variant="primary")
            cli_output = gr.Textbox(label="Agent output", lines=24, interactive=False)
            avail = availability()
            gr.Markdown("Detected now: " + " · ".join(f"**{k}:** {'✅' if v else '❌'}" for k, v in avail.items()))
            run_btn.click(run_agent, [cli_agent, cli_prompt, timeout, custom_command], cli_output)

        with gr.Tab("Files"):
            with gr.Row():
                tree = gr.Textbox(value=refresh_tree(), label="Workspace tree", lines=28, interactive=False)
                with gr.Column():
                    path = gr.Textbox(label="Relative file path", placeholder="src/app.py")
                    content = gr.Textbox(label="File content", lines=22)
                    with gr.Row():
                        open_btn = gr.Button("Open")
                        save_btn = gr.Button("Save", variant="primary")
                    status = gr.Textbox(label="Status", interactive=False)
            with gr.Row():
                refresh_btn = gr.Button("Refresh tree")
                uploads = gr.File(label="Import files", file_count="multiple")
                upload_btn = gr.Button("Import")
                export_btn = gr.Button("Export workspace ZIP")
                exported = gr.File(label="Workspace ZIP")
            open_btn.click(open_file, path, content)
            save_btn.click(save_file, [path, content], [status, tree])
            refresh_btn.click(refresh_tree, outputs=tree)
            upload_btn.click(upload_files, uploads, [status, tree])
            export_btn.click(export_zip, outputs=exported)

        with gr.Tab("Logs"):
            logbox = gr.Textbox(value=LOGS.text(), label="Runtime logs", lines=32, interactive=False)
            with gr.Row():
                logs_refresh = gr.Button("Refresh")
                logs_clear = gr.Button("Clear")
            logs_refresh.click(LOGS.text, outputs=logbox)
            logs_clear.click(lambda: (LOGS.clear(), "")[1], outputs=logbox)

        with gr.Tab("System"):
            system_box = gr.Textbox(value=collect(), label="System information", lines=28, interactive=False)
            gr.Button("Refresh system info").click(collect, outputs=system_box)

        with gr.Tab("Settings"):
            gr.Markdown(
                f"**Workspace:** `{CONFIG.workspace}`\n\n"
                "Keys typed in the Provider panel are not written to disk by this project. "
                "For public notebooks, prefer Kaggle Secrets or environment variables.\n\n"
                "Direct API chat is intentionally separate from CLI-agent authentication. "
                "A ChatGPT/Claude/Gemini subscription login is not treated as an API key."
            )

    return demo
