#!/usr/bin/env bash
# detect-language.sh: Determine language mode and comment syntax for a file.
#
# Priority (first match wins):
#   1. Command-line override ($2)
#   2. Filename match
#   3. Content-based detection
#   4. Shebang detection
#   5. Extension fallback
#   6. Final fallback: plaintext
#
# Output (pipe-delimited):
#   mode|block_start|block_end|line_comment|line_end|template_file

set -euo pipefail

file="$1"
VSCODE_LANGUAGE_MODE="${2-}"

filename=$(basename "$file")
ext="${file##*.}"
[ "$filename" = "$ext" ] && ext=""

mode=""
block_start=""
block_end=""
line_comment=""
line_end=""
template_file=""

# 1. Command-line override
if [ -n "${VSCODE_LANGUAGE_MODE-}" ] && [ "$VSCODE_LANGUAGE_MODE" != "" ]; then
    mode="$VSCODE_LANGUAGE_MODE"
fi

# 2. Special filename detection (no extension)
if [ -z "$mode" ]; then
    case "$filename" in
        Dockerfile|dockerfile)          mode="dockerfile" ;;
        Makefile|makefile)              mode="makefile" ;;
        Jenkinsfile|jenkinsfile)        mode="groovy" ;;
        docker-compose.yml|docker-compose.yaml) mode="dockercompose" ;;
        .gitignore|.gitconfig|.gitattributes)  mode="git" ;;
        .bashrc|.bash_profile|.profile) mode="shellscript" ;;
        .vimrc|.gvimrc)                 mode="viml" ;;
        README|LICENSE|CONTRIBUTING)    mode="plaintext" ;;
    esac
fi

# 3. Content-based detection
if [ -z "$mode" ] && [ -f "$file" ]; then
    head_content=$(head -n 20 "$file")

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

# 4. Shebang detection
if [ -z "$mode" ]; then
    shebang=$(head -n 1 "$file" | grep '^#!' || true)
    if [ -n "$shebang" ]; then
        case "$shebang" in
            *python*)    mode="python" ;;
            *bash*|*sh*) mode="shellscript" ;;
            *node*|*js*) mode="javascript" ;;
            *perl*)      mode="perl" ;;
            *ruby*)      mode="ruby" ;;
            *php*)       mode="php" ;;
            *env\ python*) mode="python" ;;
            *env\ bash*)   mode="shellscript" ;;
            *env\ sh*)     mode="shellscript" ;;
            *zsh*)       mode="shellscript" ;;
            *pwsh*)      mode="powershell" ;;
        esac
    fi
fi

# 5. Extension fallback
if [ -z "$mode" ] && [ -n "$ext" ]; then
    case "$ext" in
        sh|bash|zsh|ksh) mode="shellscript" ;;
        py|pyw|pyc|pyd|pyo) mode="python" ;;
        js)  mode="javascript" ;;
        ts)  mode="typescript" ;;
        jsx) mode="javascriptreact" ;;
        tsx) mode="typescriptreact" ;;
        json|jsonc) mode="json" ;;
        md|markdown) mode="markdown" ;;
        yml|yaml) mode="yaml" ;;
        xml|svg|xaml) mode="xml" ;;
        html|htm|shtml|xhtml) mode="html" ;;
        css)  mode="css" ;;
        scss) mode="scss" ;;
        less) mode="less" ;;
        c|h)  mode="c" ;;
        cpp|cc|cxx|hpp|hxx|h++) mode="cpp" ;;
        cs)   mode="csharp" ;;
        java) mode="java" ;;
        go)   mode="go" ;;
        rs)   mode="rust" ;;
        rb)   mode="ruby" ;;
        php|phtml|php3|php4|php5|phps) mode="php" ;;
        pl|pm) mode="perl" ;;
        lua)  mode="lua" ;;
        sql)  mode="sql" ;;
        r)    mode="r" ;;
        swift) mode="swift" ;;
        bat|cmd) mode="bat" ;;
        ps1|psm1|psd1) mode="powershell" ;;
        conf|config) mode="properties" ;;
        ini)  mode="ini" ;;
        toml) mode="toml" ;;
        tf|tfvars) mode="terraform" ;;
        dart) mode="dart" ;;
        kt|kts) mode="kotlin" ;;
        graphql|gql) mode="graphql" ;;
        bicep) mode="bicep" ;;
        *)    mode="$ext" ;;
    esac
fi

# 6. Final fallback
[ -z "$mode" ] && mode="plaintext"

# Comment syntax assignment + template selection by mode
case "$mode" in
    shellscript|bash|zsh|ksh) line_comment="#" ;;
    python)      line_comment="#" ;;
    javascript|typescript|javascriptreact|typescriptreact) line_comment="//"; block_start="/*"; block_end="*/" ;;
    markdown)    template_file="CCM_MARKDOWN_HEADER_TEMPLATE.txt" ;;
    yaml|yml)    line_comment="#" ;;
    dockercompose) line_comment="#" ;;
    xml|html|htm|svg) block_start="<!--"; block_end="-->" ;;
    css|scss|less) block_start="/*"; block_end="*/"; line_comment="//" ;;
    c|cpp|cc|cxx|h|hpp) line_comment="//"; block_start="/*"; block_end="*/" ;;
    csharp|java) line_comment="//"; block_start="/*"; block_end="*/" ;;
    go)          line_comment="//"; block_start="/*"; block_end="*/" ;;
    rust)        line_comment="//"; block_start="/*"; block_end="*/" ;;
    ruby)        line_comment="#" ;;
    perl)        line_comment="#" ;;
    php)         line_comment="//"; block_start="/*"; block_end="*/" ;;
    lua)         line_comment="--"; block_start="--[["; block_end="]]" ;;
    sql)         line_comment="--"; block_start="/*"; block_end="*/" ;;
    r)           line_comment="#" ;;
    swift)       line_comment="//"; block_start="/*"; block_end="*/" ;;
    bat|cmd)     line_comment="REM" ;;
    powershell)  line_comment="#"; block_start="<#"; block_end="#>" ;;
    dockerfile)  line_comment="#" ;;
    makefile)    line_comment="#" ;;
    nginx)       line_comment="#" ;;
    properties|conf|config|git) line_comment="#" ;;
    ini)         line_comment=";" ;;
    toml)        line_comment="#" ;;
    terraform|tf) line_comment="#"; block_start="/*"; block_end="*/" ;;
    bicep)       line_comment="//"; block_start="/*"; block_end="*/" ;;
    dart)        line_comment="//"; block_start="/*"; block_end="*/" ;;
    kotlin)      line_comment="//"; block_start="/*"; block_end="*/" ;;
    graphql)     line_comment="#" ;;
    groovy)      line_comment="//"; block_start="/*"; block_end="*/" ;;
    viml)        line_comment="\"" ;;
    plaintext)   line_comment="#" ;;
    json)        template_file="CCM_JSON_HEADER_TEMPLATE.txt" ;;
    *)           line_comment="#" ;;
esac

echo "$mode|$block_start|$block_end|$line_comment|$line_end|$template_file"