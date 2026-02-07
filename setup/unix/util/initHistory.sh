#!/bin/bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: unknown %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: d791b17cb4d58c555345923be5554604e37cc622 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: unknown %
#  %ccm_git_commit_date: unknown %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2026-02-07 15:40:24 %
#  %ccm_git_file_last_modified: 2026-02-07 15:40:24 %
#  %ccm_git_file_name: initHistory.sh %
#  %ccm_git_path: setup/unix/util/initHistory.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1507 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# %git_commit_history: 2025-11-30 mpegg  cleanup  % 
# %git_commit_history: november changes % 
# initHistory.sh - History management for TermiteTowers

# Enhanced history settings
export HISTSIZE=50000                    # Commands in memory
export HISTFILESIZE=100000               # Commands in file
export HISTTIMEFORMAT="%F %T "           # Timestamps: YYYY-MM-DD HH:MM:SS
export HISTCONTROL=ignoredups:erasedups  # Ignore duplicates

# Skip heredoc commands from history (EOF, END, HERE, CONFIG)
export HISTIGNORE="**<<EOF*:*<<END*:*<<HERE*:*<<CONFIG*:ls:ll:la:l:cd:pwd:exit:clear:history:bg:fg:jobs"  # Ignore heredocs and trivial commands

# Options
shopt -s histappend                      # Append, don't overwrite
shopt -s cmdhist                         # Multi-line commands as one entry
shopt -s lithist                         # Store multi-line commands with embedded newlines

# Save after each command
PROMPT_COMMAND="history -a; history -n${PROMPT_COMMAND:+; $PROMPT_COMMAND}"

# History backup function
backup_history() {
    local backup_dir="$HOME/.bash_history_backups"
    mkdir -p "$backup_dir"
    local backup_file="$backup_dir/bash_history_$(date +%Y%m%d_%H%M%S).log"
    cp ~/.bash_history "$backup_file"
    gzip "$backup_file"
    echo "History backed up to: ${backup_file}.gz"
    
    # Keep only last 30 days of backups
    find "$backup_dir" -name "bash_history_*.log.gz" -mtime +30 -delete
}

# Aliases for history management
alias hg='history | grep'
alias h='history | tail -50'
alias hbackup='backup_history'
