<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/runbook-ollama.md:147 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 44d6bea22cbe87a163c7232b7cd324c8192d693e %
  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
  %ccm_git_commit_count: 147 %
  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: june bulk update %
  %ccm_git_modify_date: 2026-06-10 17:10:33 %
  %ccm_git_file_last_modified: 2026-06-10 17:10:33 %
  %ccm_git_file_name: runbook-ollama.md %
  %ccm_git_path: wiki/runbook-ollama.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 7222 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!--
-->

# Runbook: Ollama (dev1)

## Install
- scripts/system/setup-ollama-dev1.sh (SERVICE_USER/GROUP supported)

## Start/Stop
- Start: `sudo systemctl start ollama-dev1`
- Stop: `sudo systemctl stop ollama-dev1`
- Enable on boot: `sudo systemctl enable ollama-dev1`
- Status/logs: `sudo systemctl status ollama-dev1 -l` and `journalctl -u ollama-dev1 -f`

## Ports
- HTTP API: 0.0.0.0:11434

## Paths
- Program: /srv/dev1/ollama
- Models: /mnt/ai_storage/models/ollama (OLLAMA_MODELS)

## Notes
- Open WebUI and Lobe Chat use host.docker.internal:11434
- Ensure service user has rw access to /mnt/ai_storage/models/ollama

## Troubleshooting
- Permission errors: `sudo chown -R <svc>:<grp> /mnt/ai_storage/models/ollama`
- Check connectivity: `curl http://localhost:11434/api/tags`


Optimized tool selectionCompacted conversationCertainly! Below is an **upgrade documentation** for Ollama, tailored to address the issues you encountered during the upgrade process. This document will guide you through the steps to ensure a smooth and conflict-free upgrade, especially when dealing with custom service names like `ollama-dev1`.

---

## **Ollama Upgrade Documentation**

### **Overview**
This document provides step-by-step instructions for upgrading Ollama on your system. It addresses common pitfalls encountered during upgrades, such as conflicting service names and ensures that the new version is installed without disrupting existing services.

### **Prerequisites**
- Ensure you have administrative privileges (`sudo` access).
- Verify that your current Ollama installation is running correctly.
- Have a backup of important data before proceeding with the upgrade.

### **Upgrade Steps**

#### **1. Download the Latest Release**
Download the latest version of Ollama from the official GitHub repository.

```bash
sudo curl -L "https://github.com/ollama/ollama/releases/download/v0.30.6/ollama-linux-amd64.tar.zst" -o /tmp/ollama.tar.zst
```

#### **2. Extract the New Version**
Extract the downloaded tarball to usr.

```bash
sudo tar --zstd -xf /tmp/ollama.tar.zst -C /usr/
```

**Note:** Ensure that you extract the files correctly without overwriting existing configurations.

#### **3. Stop and Disable the Existing Service (if applicable)**
If you have a custom service name like `ollama-dev1`, stop and disable it to prevent conflicts during the upgrade.

```bash
sudo systemctl stop ollama-dev1 2>/dev/null
sudo systemctl disable ollama-dev1 2>/dev/null
```

**Important:** If your service name is different, replace `ollama-dev1` with your actual service name.

#### **4. Remove Old Executable (if necessary)**
If the old executable (ollama) exists and you want to ensure it's replaced, remove it.

```bash
sudo rm -f /usr/bin/ollama
```

**Caution:** Only remove the old executable if you're sure that the new version will replace it correctly. Otherwise, skip this step.

#### **5. Verify the New Installation**
Ensure that the new Ollama binary is installed and accessible.

```bash
/usr/bin/ollama -v
```

You should see the version information for the newly installed Ollama.

#### **6. Update Systemd Service Configuration (if necessary)**
If you have a custom service file like ollama-dev1.service, update it to point to the new binary location and ensure all paths are correct.

**Example `ollama-dev1.service` Content:**

```ini
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=ollama
Group=tt-ai-storage
ExecStart=/usr/bin/ollama start --config /srv/dev1/ollama/config.yaml
Restart=always
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

**Steps to Update:**

1. Open the service file for editing:

    ```bash
    sudo nano /etc/systemd/system/ollama-dev1.service
    ```

2. Ensure that `ExecStart` points to the correct binary and configuration paths.

3. Save and exit the editor (`Ctrl+X`, then `Y`, then `Enter`).

4. Reload the systemd daemon to apply changes:

    ```bash
    sudo systemctl daemon-reload
    ```

#### **7. Enable and Start the Updated Service**
Enable and start your custom service to ensure it runs on boot.

```bash
sudo systemctl enable --now ollama-dev1
```

**Note:** Replace `ollama-dev1` with your actual service name if different.

#### **8. Verify the Service Status**
Check that the service is running correctly without any errors.

```bash
sudo systemctl status ollama-dev1
```

You should see an output indicating that the service is active and running.

#### **9. Check Logs for Any Issues**
Review the logs to ensure there are no errors or warnings during startup.

```bash
sudo journalctl -u ollama-dev1 -n 20 --no-pager
```

**Troubleshooting Tips:**

- If you encounter any issues, check the service file configuration.
- Ensure that all paths (e.g., binary location, config path) are correct.
- Verify that the user and group specified in the service file have the necessary permissions.

#### **10. Adjust Permissions for Data Directory**
Ensure that the data directory has the correct ownership and permissions to allow Ollama to read/write files.

```bash
sudo chown -R ollama:tt-ai-storage /srv/dev1/ollama
sudo chmod -R 775 /srv/dev1/ollama
```

**Note:** Adjust the user, group, and directory paths as per your setup.

#### **11. Restart the Service (if necessary)**
If you made any changes to the service configuration or data permissions, restart the service to apply them.

```bash
sudo systemctl restart ollama-dev1
```

#### **12. Verify the Upgrade**
Finally, verify that Ollama is running the correct version and functioning as expected.

```bash
ollama --version
```

You should see the version information for the newly installed Ollama.

### **Common Issues and Solutions**

- **Conflicting Service Names:**
  - **Issue:** Stopping and disabling the default `ollama` service might interfere with your custom `ollama-dev1`.
  - **Solution:** Always stop and disable your custom service before proceeding with the upgrade. Use commands like:
    ```bash
    sudo systemctl stop ollama-dev1
    sudo systemctl disable ollama-dev1
    ```

- **Incorrect Executable Path:**
  - **Issue:** The new Ollama binary might not replace the old one correctly.
  - **Solution:** Ensure that the `ExecStart` path in your service file points to ollama. Verify this by checking:
    ```bash
    cat /etc/systemd/system/ollama-dev1.service | grep ExecStart
    ```

- **Permission Errors:**
  - **Issue:** Ollama might not have the necessary permissions to access its data directory.
  - **Solution:** Adjust ownership and permissions as shown in Step 10:
    ```bash
    sudo chown -R ollama:tt-ai-storage /srv/dev1/ollama
    sudo chmod -R 775 /srv/dev1/ollama
    ```

### **Conclusion**
By following these steps, you can upgrade Ollama without encountering conflicts with existing services or configurations. Always ensure that your custom service names and paths are correctly updated to avoid any issues during the upgrade process.

If you encounter any further problems, please refer to the official [Ollama documentation](https://docs.ollama.com/) or seek assistance from the community forums.

---

Feel free to reach out if you need further assistance with the upgrade process!