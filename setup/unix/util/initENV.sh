#!/bin/bash
# initENV.sh - Environment initialization script
# This script calls various initialization scripts based on environment variables
# Resides in $tt_scriptDir/util

# Get the directory where this script resides
tt_utilDir=$(cd $(dirname "${BASH_SOURCE[0]}") && pwd)

# Enable debugging if tt_debug is set
if [ ! -z ${tt_debug} ]; then
    echo "initENV.sh: Starting environment initialization from $tt_utilDir" >> ${tt_tracelog}
fi

# Create uppercase variable for home basename
typeset -u l_uhome=$(basename "$HOME")
export l_uhome

if [ ! -z ${tt_debug} ]; then
    echo "initENV.sh: l_uhome=$l_uhome" >> ${tt_tracelog}
fi

# Check if init script for user home exists and is executable
init_home_script="$tt_utilDir/init${l_uhome}.sh"
if [ -f "$init_home_script" ] && [ -x "$init_home_script" ]; then
    if [ ! -z ${tt_debug} ]; then
        echo "initENV.sh: Sourcing $init_home_script" >> ${tt_tracelog}
    fi
    . "$init_home_script"
else
    if [ ! -z ${tt_debug} ]; then
        echo "initENV.sh: Script $init_home_script not found or not executable" >> ${tt_tracelog}
    fi
fi

# Create uppercase variable for appuser_type
typeset -u l_uType="$tt_appUserType"
export l_uType

if [ ! -z ${tt_debug} ]; then
    echo "initENV.sh: l_uType=$l_uType" >> ${tt_tracelog}
fi

# Check if init script for appuser type exists and is executable
init_type_script="$tt_utilDir/init${l_uType}.sh"
if [ -f "$init_type_script" ] && [ -x "$init_type_script" ]; then
    if [ ! -z ${tt_debug} ]; then
        echo "initENV.sh: Sourcing $init_type_script" >> ${tt_tracelog}
    fi
    . "$init_type_script"
else
    if [ ! -z ${tt_debug} ]; then
        echo "initENV.sh: Script $init_type_script not found or not executable" >> ${tt_tracelog}
    fi
fi

# Create uppercase variable for default appuser
typeset -u l_uenv="$tt_appUser_dflt"
export l_uenv

if [ ! -z ${tt_debug} ]; then
    echo "initENV.sh: l_uenv=$l_uenv" >> ${tt_tracelog}
fi

# Check if init script for default appuser exists and is executable
init_env_script="$tt_utilDir/init${l_uenv}.sh"
if [ -f "$init_env_script" ] && [ -x "$init_env_script" ]; then
    if [ ! -z ${tt_debug} ]; then
        echo "initENV.sh: Sourcing $init_env_script" >> ${tt_tracelog}
    fi
    . "$init_env_script"
else
    if [ ! -z ${tt_debug} ]; then
        echo "initENV.sh: Script $init_env_script not found or not executable" >> ${tt_tracelog}
    fi
fi

# Create uppercase variable for hostname
typeset -u l_uhost=$(hostname)
export l_uhost

if [ ! -z ${tt_debug} ]; then
    echo "initENV.sh: l_uhost=$l_uhost" >> ${tt_tracelog}
fi

# Check if init script for hostname exists and is executable
init_host_script="$tt_utilDir/init${l_uhost}.sh"
if [ -f "$init_host_script" ] && [ -x "$init_host_script" ]; then
    if [ ! -z ${tt_debug} ]; then
        echo "initENV.sh: Sourcing $init_host_script" >> ${tt_tracelog}
    fi
    . "$init_host_script"
else
    if [ ! -z ${tt_debug} ]; then
        echo "initENV.sh: Script $init_host_script not found or not executable" >> ${tt_tracelog}
    fi
fi

if [ ! -z ${tt_debug} ]; then
    echo "initENV.sh: Environment initialization completed" >> ${tt_tracelog}
fi



unset l_uhome
unset l_uType
unset l_uenv
unset l_uhost
unset init_home_script
unset init_type_script
unset init_env_script
unset init_host_script
