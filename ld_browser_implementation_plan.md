# Implementation Plan: Python PyQt6 Lockdown Browser with Dual Image Uploads

This plan details the development of a secure, cross-platform desktop wrapper (`lockdown_browser.py`) using **PyQt6** and **PyQt6-WebEngine**, alongside updates to the **EduPortal AI** web application to support lockdown verification, direct webcam capture, and a secure QR Code companion mobile upload.

---

## User Review Required

> [!IMPORTANT]
> **Network Accessibility for QR Code Uploads**
> For the **QR Code Companion** upload to work, the mobile phone must be able to reach the server. If you are running the app on `localhost` (127.0.0.1), a phone on a cellular network or different Wi-Fi won't be able to connect unless the local server is exposed via a tool like **ngrok** or deployed to a public server.
> We will design the system to use the current host IP/URL automatically.

> [!IMPORTANT]
> **Packaging Executables (.exe & .app)**
> You will need to run the compilation commands on Windows to generate `lockdown_browser.exe` and on macOS to generate `lockdown_browser.app`. Cross-compilation is not supported by PyInstaller.

> [!WARNING]
> **macOS Permissions**
> To restrict key combinations like `Cmd+Tab` and `Cmd+Option+Esc`, the macOS version of the application requires **Accessibility Permissions** to be enabled by the user in macOS System Settings.

---

## Proposed Architecture & Flow

1. **Lockdown App (`lockdown_browser.py`)**: Launches in fullscreen, monitors Focus/Screens/Processes, and loads the Streamlit application with a custom User-Agent string (e.g., `EduPortalSecureBrowser/1.0`).
2. **Streamlit App (`student_pages.py`)**: Checks the browser's User-Agent. If the custom agent is missing, it denies access to the exam, forcing the student to use the desktop app.
3. **Webcam Capture**: Uses Streamlit's built-in `st.camera_input` component (which is natively supported by `PyQt6-WebEngine` once permissions are granted).
4. **QR Code Companion**: 
   - Generates a short-lived token stored in MongoDB.
   - Renders a QR code pointing to `http://<server-ip>:8501/?page=upload&token=<token>`.
   - The student scans this with their mobile phone, snaps a picture using the mobile camera (forced via `capture="environment"`), and uploads it.
   - The student's desktop view polls the database and automatically progresses when the image is uploaded.

---

## Proposed Changes

### 1. Desktop Client Components

#### [NEW] [lockdown_browser.py](file:///c:/Users/samya/OneDrive/Desktop/projects/login_codex/lockdown_browser.py)
A PyQt6 desktop application.
* **Window Properties**: Frameless, fullscreen, set to stay on top (`Qt.WindowType.WindowStaysOnTopHint`).
* **Web View Engine**: `QWebEngineView` pointing to the Streamlit app.
  * Configured with a custom User-Agent string: `EduPortalSecureBrowser/1.0`.
  * Auto-accepts camera and microphone permission requests via `page().permissionRequested` signals.
* **Security Hooks**:
  * **Windows**: Sets a low-level keyboard hook using `ctypes` (`WH_KEYBOARD_LL`) to intercept and disable `LWin`, `RWin`, `Alt+Tab`, `Alt+Esc`, and `Ctrl+Esc`.
  * **macOS**: Sets `NSApplicationPresentationOptions` to hide the dock, menu bar, and disable process switching/force-quit shortcuts.
* **Proctoring Monitors**:
  * **Screen Monitor**: Checks `QApplication.screens()` every 2 seconds. If multiple screens are found, displays a modal warning and blocks the view.
  * **Focus Monitor**: Logs when the window loses focus and displays warning alerts.
  * **Process Monitor**: Periodically scans running processes for blocklisted apps (e.g., OBS, Discord, TeamViewer, Zoom, Chrome, Firefox).

#### [NEW] [build_lockdown.py](file:///c:/Users/samya/OneDrive/Desktop/projects/login_codex/build_lockdown.py)
A build script utilizing `PyInstaller` to bundle the app into a single executable for distribution:
* On Windows: Outputs `lockdown_browser.exe`.
* On macOS: Outputs `lockdown_browser.app` with appropriate Info.plist configurations.

---

### 2. Streamlit Web App Updates

#### [MODIFY] [db.py](file:///c:/Users/samya/OneDrive/Desktop/projects/login_codex/db.py)
Add database helper functions for handling temporary upload tokens:
* `create_upload_token(student_username, question_id)`: Generates a 6-digit or UUID token that expires in 5 minutes.
* `verify_upload_token(token)`: Validates the token and retrieves the associated student and question.
* `save_token_image(token, image_bytes)`: Saves the uploaded image to the corresponding student session and marks the token as used.
* `check_token_status(token)`: Checks if the image has been uploaded for a specific token.

#### [MODIFY] [app.py](file:///c:/Users/samya/OneDrive/Desktop/projects/login_codex/app.py)
Handle routing for the mobile upload page:
* Inspect query parameters at startup: `st.query_params`.
* If `page == "upload"` and a valid `token` is provided, render a simplified, mobile-friendly upload page.
* This mobile page will have:
  * A file uploader component configured to accept only images directly from the camera (`accept="image/*" capture="environment"`).
  * A button to submit the photo to `db.py` via `save_token_image`.

#### [MODIFY] [student_pages.py](file:///c:/Users/samya/OneDrive/Desktop/projects/login_codex/student_pages.py)
* **Lockdown Enforcement**:
  * Read `st.context.headers` (or user-agent headers through custom javascript/Streamlit mechanisms) to check for the custom User-Agent `EduPortalSecureBrowser/1.0`.
  * If the header is missing, block the student dashboard with a screen instructing the student to download and use the Lockdown Browser app.
* **Integrated Webcam Capture**:
  * Integrate `st.camera_input` in the "Image" tab for direct, secure capture.
* **QR Code Companion**:
  * Integrate a QR code generator (using the `qrcode` or `segno` library) to display the upload link.
  * Use a loop with `st.empty()` or `st.rerun()` to poll the database for the uploaded image using `check_token_status(token)`. Once the image is detected, transition the UI automatically to show the uploaded image.

---

## Verification Plan

### Automated Verification
* Write a script `test_lockdown.py` to:
  * Test token creation, validation, and expiration logic in `db.py`.
  * Verify the user-agent check logic helper.

### Manual Verification
1. **Developer Run**: Start the Streamlit app locally (`streamlit run app.py`).
2. **Access via standard browser**: Confirm access to the student dashboard is blocked and displays the "Download Lockdown Browser" page.
3. **Run the Lockdown App**: Open `python lockdown_browser.py` and confirm the student dashboard loads successfully.
4. **Test Features**:
   - Test **Webcam Capture** using the in-app camera component.
   - Test **QR Code Upload** (expose port via local network/ngrok, scan, take a photo on your phone, and check if it uploads and updates on the desktop).
   - Test **Microphone Recording** to ensure voice input still works perfectly.
   - Test **Lockdown Security**: Attempt `Alt+Tab` (Windows) or `Cmd+Tab` (Mac) and observe the blockade or logging.
5. **Multi-Monitor Test**: Plug in a second screen and verify the lock screen appears.
