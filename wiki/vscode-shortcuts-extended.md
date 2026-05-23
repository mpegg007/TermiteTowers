<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/vscode-shortcuts-extended.md:139 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 6fba76f0d445d8f817a8ea88bd1f657eca4385e3 %
  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
  %ccm_git_commit_count: 139 %
  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: march updates %
  %ccm_git_modify_date: 2026-03-22 09:03:23 %
  %ccm_git_file_last_modified: 2025-12-24 16:24:55 %
  %ccm_git_file_name: vscode-shortcuts-extended.md %
  %ccm_git_path: wiki/vscode-shortcuts-extended.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 2982 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# VS Code: Docs, Layout & Project Manager — Extended Tips

This file augments `wiki/vscode-shortcuts.md` with practical, copy-paste snippets and short workflows for keeping docs visible and switching projects quickly.

## Docs & Layout

- Keep docs on the right: Split the editor (`Ctrl+\`) and open docs with "Open to the Side" (right-click file → *Open to the Side* or `Ctrl+Enter`). Use `Ctrl+2` (or `Ctrl+3`) to focus the right column.
- Pin docs / disable preview tabs: Add to workspace settings to avoid preview tabs so clicked files open pinned:

    {
        "workbench.editor.enablePreview": false
    }

- Move terminal to editor area: Command Palette → `Terminal: Move Terminal into Editor Area`, then drag it to a column so terminal, code and docs can be visible together.
- Save layout: Save the workspace (`File → Save Workspace As...`) to preserve open editors and layout across sessions.

## Project Manager (quick notes)

- Purpose: Save and quickly switch between named projects/workspaces. Install from Extensions (`Project Manager`).
- Save current workspace: Command Palette → `Project Manager: Save Project` and give it a name.
- Open projects: Command Palette → `Project Manager: List Projects to Open`.
- Hints: Set `projectManager.openInNewWindow` to `false` if you prefer reopening in the same window.

## Useful workspace snippets

Add these snippets to your repo's `.vscode/settings.json`, `tasks.json`, and `keybindings.json` to make the layout + tasks repeatable.

`.vscode/settings.json` (workspace)

    {
      "workbench.editor.enablePreview": false,
      "terminal.integrated.defaultProfile.linux": "bash",
      "projectManager.openInNewWindow": false,
      "projectManager.git.baseFolders": ["/home/mpegg-adm/source"]
    }

`.vscode/tasks.json` (example task for your secret scanner)

    {
      "version": "2.0.0",
      "tasks": [
        {
          "label": "Run Secret Scanner",
          "type": "shell",
          "command": "${workspaceFolder}/TermiteTowers/git-automation/enhanced-secrets-pattern-scanner.sh",
          "group": "build",
          "presentation": { "panel": "shared" }
        }
      ]
    }

`keybindings.json` (example)

    [
      {
        "key": "ctrl+alt+p",
        "command": "projectManager.listProjects",
        "when": "editorTextFocus"
      }
    ]

## Quick workflow suggestion

- Left column: Explorer + primary code. Center: active coding tab(s). Right: pinned docs/help files (README, API notes). Terminal(s) in editor area or bottom panel depending on preference.
- Use `Ctrl+1`/`Ctrl+2`/`Ctrl+3` to move quickly between columns. Keep frequently-referenced docs open in the right column so you don't lose context.

---

If you'd prefer I insert these sections directly into `wiki/vscode-shortcuts.md`, I can try again — but I hit a patching error when editing that file and created this companion file instead. Want me to keep both, or try to merge into the original file inline?