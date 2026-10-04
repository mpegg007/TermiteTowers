<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/log-collector-setup-guide.md:111 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 4398d53122b9f359de9a80692b25a01c5fff6491 %
  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
  %ccm_git_commit_count: 111 %
  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: docker updates %
  %ccm_git_modify_date: 2025-10-29 19:12:45 %
  %ccm_git_file_last_modified: 2025-10-24 09:07:20 %
  %ccm_git_file_name: log-collector-setup-guide.md %
  %ccm_git_path: wiki/log-collector-setup-guide.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 2148 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Log Collector Setup Guide

This guide explains how to set up and use the `pull-journal-proper.sh` script for collecting journal logs from remote servers via SSH.

## 1. Install OpenSSH on the Remote Server

On the remote server, install the OpenSSH server package:

```bash
sudo apt update
sudo apt install openssh-server
```

Ensure the SSH service is running:

```bash
sudo systemctl enable ssh
sudo systemctl start ssh
```


## 2. Set Up SSH Key Authentication

On the collector host (this machine), create a custom-named SSH key for each collector user and host:

```bash
# Recommended key name format:
# id_ed25519_<hostname>_<username>
keyname="id_ed25519_$(hostname)_$(whoami)"
ssh-keygen -t ed25519 -C "$(whoami)@$(hostname)" -f ~/.ssh/$keyname
```

Copy your public key to the remote server:

```bash
ssh-copy-id -i ~/.ssh/$keyname.pub username@remote_host
```

Test SSH connection:

```bash
ssh -i ~/.ssh/$keyname username@remote_host
```

You should connect without entering a password.

## 3. Run a Test Pull (No Marker)

To test the collector script, run it with no marker file present. This will pull logs from the last hour by default:

```bash
./pull-journal-proper.sh user@remoteserver.tt.omp
```

Check the output and logs in:
- `/mnt/ai_storage/logCollector/logs/<remoteserver>/drop/journal.log`
- `/mnt/ai_storage/logCollector/logs/<remoteserver>/markers/pull-journal-proper.log`

## 4. Run a Full Pull

Once the test is successful, you can run a full pull to collect all available logs:

```bash
./pull-journal-proper.sh user@remoteserver.tt.omp --full
```

This will fetch all journal entries since 1970-01-01 00:00:00.

## 5. Regular Usage

For ongoing collection, run:

```bash
./pull-journal-proper.sh user@remoteserver.tt.omp
```

- The script will only pull new entries since the last run.
- Argument 1 must be in the format: `user@remoteserver.tt.omp`

## Notes
- Ensure the collector host has network access to the remote server's SSH port (default 22).
- The marker and log files are stored per remote host in `/mnt/ai_storage/logCollector/logs/<remoteserver>/markers/`.
- Review logs for troubleshooting if needed.
