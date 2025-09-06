#!/usr/bin/env bash
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: git-automation/get_language_mode_and_comments.sh:0 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 818b10f80f16e03e7862112837844d98e3d5cff1 %
#  %ccm_git_commit_id: unknown %
#  %ccm_git_commit_count: 0 %
#  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
#  %ccm_git_commit_author: unknown %
#  %ccm_git_commit_email: unknown %
#  %ccm_git_commit_message: unknown %
#  %ccm_git_modify_date: 2025-09-06 12:02:06 %
#  %ccm_git_file_last_modified: 2025-09-06 11:52:11 %
#  %ccm_git_file_name: get_language_mode_and_comments.sh %
#  %ccm_git_path: git-automation/get_language_mode_and_comments.sh %
#  %ccm_git_language_mode: shellscript %
#  %ccm_git_file_type: text/x-shellscript %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: yes %
#  %ccm_git_size: 10950 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  

file="$1"
VSCODE_LANGUAGE_MODE="$2"

filename=$(basename "$file")
ext="${file##*.}"
# Handle files with no extension
if [ "$filename" = "$ext" ]; then
    ext=""
fi
mode="" block_start="" block_end="" line_comment=""

# 1. Check for language mode override from command line argument
if [ "${VSCODE_LANGUAGE_MODE}" != "" ]; then
    mode="$VSCODE_LANGUAGE_MODE"
else
    # 2. Special filename detection (no extension)
    case "$filename" in
        Dockerfile|dockerfile) mode="dockerfile" ;;
        Makefile|makefile) mode="makefile" ;;
        Jenkinsfile|jenkinsfile) mode="groovy" ;;
        docker-compose.yml|docker-compose.yaml) mode="dockercompose" ;;
        .gitignore|.gitconfig|.gitattributes) mode="git" ;;
        .bashrc|.bash_profile|.profile) mode="shellscript" ;;
        .vimrc|.gvimrc) mode="viml" ;;
        README|LICENSE|CONTRIBUTING) mode="plaintext" ;;
        *) mode="" ;;
    esac

    # 3. Content-based detection if no mode determined yet
    if [ -z "$mode" ] && [ -f "$file" ]; then
        # Check first few lines for patterns
        head_content=$(head -n 20 "$file")
        
        # Check for YAML language server directive for Docker Compose
        if echo "$head_content" | grep -q '# yaml-language-server:.* compose-spec'; then
            mode="dockercompose"
        elif echo "$head_content" | grep -q '<?xml'; then
            mode="xml"
        elif echo "$head_content" | grep -q '<!DOCTYPE html\|<html'; then
            mode="html"
        elif echo "$head_content" | grep -q 'server {' && echo "$head_content" | grep -q 'location'; then
            mode="nginx"
        elif echo "$head_content" | grep -q 'package main' && echo "$head_content" | grep -q 'import'; then
            mode="go"
        elif echo "$head_content" | grep -q '^FROM ' && echo "$head_content" | grep -q '^RUN\|^CMD\|^ENTRYPOINT\|^COPY'; then
            mode="dockerfile"
        elif echo "$head_content" | grep -q '^version:.*' && echo "$head_content" | grep -q 'services:'; then
            mode="dockercompose"
        elif echo "$head_content" | grep -q '^upstream\|^server\|^http {'; then
            mode="nginx"
        elif echo "$head_content" | grep -q '<?php'; then
            mode="php"
        elif echo "$head_content" | grep -q '^apiVersion:' && echo "$head_content" | grep -q '\(kind:\|metadata:\)'; then
            mode="yaml.kubernetes"
        elif echo "$head_content" | grep -q '# yaml-language-server:'; then
            mode="yaml"
        fi
    fi
    
    # 4. Shebang detection if still no mode
    if [ -z "$mode" ]; then
        shebang=$(head -n 1 "$file" | grep '^#!' || true)
        if [ -n "$shebang" ]; then
            case "$shebang" in
                *python*) mode="python" ;;
                *bash*|*sh*) mode="shellscript" ;;
                *node*|*js*) mode="javascript" ;;
                *perl*) mode="perl" ;;
                *ruby*) mode="ruby" ;;
                *php*) mode="php" ;;
                *env\ python*) mode="python" ;;
                *env\ bash*) mode="shellscript" ;;
                *env\ sh*) mode="shellscript" ;;
                *zsh*) mode="shellscript" ;;
                *pwsh*) mode="powershell" ;;
                *) mode="" ;;
            esac
        fi
    fi
    
    # 5. Extension fallback
    if [ -z "$mode" ] && [ -n "$ext" ]; then
        case "$ext" in
            sh|bash|zsh|ksh) mode="shellscript" ;;
            py|pyw|pyc|pyd|pyo) mode="python" ;;
            js) mode="javascript" ;;
            ts) mode="typescript" ;;
            jsx) mode="javascriptreact" ;;
            tsx) mode="typescriptreact" ;;
            json|jsonc) mode="json" ;;
            md|markdown) mode="markdown" ;;
            yml|yaml) mode="yaml" ;;
            xml|svg|xaml) mode="xml" ;;
            html|htm|shtml|xhtml) mode="html" ;;
            css) mode="css" ;;
            scss) mode="scss" ;;
            less) mode="less" ;;
            c|h) mode="c" ;;
            cpp|cc|cxx|hpp|hxx|h++) mode="cpp" ;;
            cs) mode="csharp" ;;
            java) mode="java" ;;
            go) mode="go" ;;
            rs) mode="rust" ;;
            rb) mode="ruby" ;;
            php|phtml|php3|php4|php5|phps) mode="php" ;;
            pl|pm) mode="perl" ;;
            lua) mode="lua" ;;
            sql) mode="sql" ;;
            r) mode="r" ;;
            swift) mode="swift" ;;
            bat|cmd) mode="bat" ;;
            ps1|psm1|psd1) mode="powershell" ;;
            conf|config) mode="properties" ;;
            ini) mode="ini" ;;
            toml) mode="toml" ;;
            tf|tfvars) mode="terraform" ;;
            dart) mode="dart" ;;
            kt|kts) mode="kotlin" ;;
            graphql|gql) mode="graphql" ;;
            *) mode="$ext" ;;
        esac
    fi
    
    # 6. Final fallback to plaintext
    if [ -z "$mode" ]; then
        mode="plaintext"
    fi
fi

# Set block and line comment fields by mode
case "$mode" in
    shellscript|bash|zsh|ksh) line_comment="#" ;;
    python) line_comment="#" ;;
    javascript|typescript|javascriptreact|typescriptreact) line_comment="//"; block_start="/*"; block_end="*/" ;;
    json) line_comment="//"; block_start="/*"; block_end="*/" ;;
    markdown) block_start="<!--"; block_end="-->" ;;
    yaml|yml) line_comment="#" ;;
    xml|html|htm|svg) block_start="<!--"; block_end="-->" ;;
    css|scss|less) block_start="/*"; block_end="*/"; line_comment="//" ;;
    c|cpp|cc|cxx|h|hpp) line_comment="//"; block_start="/*"; block_end="*/" ;;
    csharp|java) line_comment="//"; block_start="/*"; block_end="*/" ;;
    go) line_comment="//"; block_start="/*"; block_end="*/" ;;
    rust) line_comment="//"; block_start="/*"; block_end="*/" ;;
    ruby) line_comment="#" ;;
    perl) line_comment="#" ;;
    php) line_comment="//"; block_start="/*"; block_end="*/" ;;
    lua) line_comment="--"; block_start="--[["; block_end="]]" ;;
    sql) line_comment="--"; block_start="/*"; block_end="*/" ;;
    r) line_comment="#" ;;
    swift) line_comment="//"; block_start="/*"; block_end="*/" ;;
    bat|cmd) line_comment="REM" ;;
    powershell) line_comment="#"; block_start="<#"; block_end="#>" ;;
    dockerfile|dockercompose) line_comment="#" ;;
    makefile) line_comment="#" ;;
    nginx) line_comment="#" ;;
    properties|conf|config) line_comment="#" ;;
    ini) line_comment=";" ;;
    toml) line_comment="#" ;;
    terraform) line_comment="#"; block_start="/*"; block_end="*/" ;;
    dart) line_comment="//"; block_start="/*"; block_end="*/" ;;
    kotlin) line_comment="//"; block_start="/*"; block_end="*/" ;;
    graphql) line_comment="#" ;;
    plaintext) line_comment="#" ;;
    *) line_comment="#" ;;
esac

echo "$mode|$block_start|$block_end|$line_comment"
