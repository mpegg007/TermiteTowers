<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-08-31 11:51:01 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: infra/tdarr-node/tdarr-node-windows-share.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-08-31 11:51:02 %
% ccm_file_name: tdarr-node-windows-share.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: infra/tdarr-node/tdarr-node-windows-share.md %
% ccm_blob_sha: 5c0514e7cb74796073c294d8043e01d41f3eacab %
% ccm_exec: no %
% ccm_size: 3871 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Tdarr Node on Linux reading media from a Windows server (SMB/CIFS)

If your Tdarr Server (Windows) scans libraries as Windows paths like `C:\media.tt.omp\...` but your Tdarr Node runs on Linux (Docker), you need:

- A CIFS mount of the Windows share on the Linux host
- A Tdarr path substitution so the node can translate Windows paths to the Linux mount

## 1) Mount the Windows share on the Linux host

Assumptions:
- Windows server: 192.168.4.63
- Windows share name: `media.tt.omp` (the Windows path shown in logs is `C:\media.tt.omp\...`)
- Mount point on Linux: `/mnt/media`
- Container PUID/PGID: 2001/1006 (matches our compose defaults)

Commands:

1. Create mount point and credentials file

   sudo mkdir -p /mnt/media
   sudo mkdir -p /etc/samba/credentials
   sudo bash -c 'cat > /etc/samba/credentials/media.tt.omp <<EOF
   username=YOUR_WINDOWS_USERNAME
   password=YOUR_WINDOWS_PASSWORD
   domain=YOUR_DOMAIN_OR_WORKGROUP
   EOF'
   sudo chmod 600 /etc/samba/credentials/media.tt.omp

2. Add to /etc/fstab (persistent mount)

   //192.168.4.63/media.tt.omp  /mnt/media  cifs  credentials=/etc/samba/credentials/media.tt.omp,uid=2001,gid=1006,dir_mode=0775,file_mode=0664,iocharset=utf8,noserverino,vers=3.1.1  0  0

3. Mount and verify

   sudo mount -a
   ls -la /mnt/media | head

If the share name differs, adjust the `//host/share` accordingly. If SMB 3.1.1 is not supported, try `vers=3.0`.

## 2) Ensure the container can see the mount

Compose files already bind-mount `/mnt/media` into the container at `/mnt/media`. After mounting, the container will see your Windows files under `/mnt/media`.

If you use a different mount point, update the compose volumes accordingly.

## 3) Configure Tdarr path substitution (in the Server UI)

In Tdarr Server (Settings > Server > Path substitution): add rules so Windows paths map to the Linux mount used by the node.

Recommended entries:
- From: C:\\media.tt.omp  To: /mnt/media
- From: C:/media.tt.omp  To: /mnt/media

This covers both backslash and forward-slash variants seen in logs.

Save the settings, then restart the Tdarr Node container and retry a single file.

## 4) Quick test

- In the Node container, confirm a sample file exists at the translated path.
  Example (replace with a real file from your library):

  docker exec -it tdarr-node-dev1 bash -lc 'ls -la "/mnt/media/VG/shows2000" | head'

- Start/queue a small transcode and watch logs. Errors like `ENOENT: no such file or directory` for `C:/...` should disappear once substitution and mount are correct.

## Notes

- Permissions: With `uid=2001,gid=1006,dir_mode=0775,file_mode=0664` the Linux host will present files writable by that user/group. Our node runs as root for init but respects file modes on the mount; adjust as needed.
- Multiple libraries/shares: Add additional CIFS mounts and matching path substitutions for each top-level Windows path.
- If you later move libraries on Windows, update both the CIFS mount and path substitutions to match.
