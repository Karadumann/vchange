# V-Change: Real-Time Voice Changer

V-Change is a real-time voice changing application for desktop, allowing you to modify your voice on-the-fly for applications like Discord, Skype, or online games. It uses a virtual audio cable (like VB-CABLE) to route your modified voice to any application's input.

![V-Change Interface](https://i.ibb.co/0RwYVZKk/image.png)

---

## Features

*   **Real-Time Processing:** Modifies your voice with minimal latency.
*   **Wide Range of Effects:** Includes Pitch Shifting, Reverb, Chorus, and Delay.
*   **Fine-Tuning with EQ:** Use High-pass and Low-pass filters to shape your vocal timbre for more realistic or creative results.
*   **Device Selection:** Choose your input (microphone) and output (virtual cable) devices directly from the app.
*   **Live Volume Meter:** Get instant visual feedback on your microphone input level.
*   **Voice Test Mode:** Hear your own modified voice in real-time to adjust effects before going live.
*   **Preset Management:**
    *   Comes with built-in presets like "Deep Voice" and "Higher Timbre".
    *   Save your own custom effect combinations.
    *   Load and delete your custom presets.
*   **Modern & Intuitive UI:** Built with `customtkinter` for a clean and user-friendly experience.

---

## How It Works

The application captures audio from your selected microphone, processes it in real-time using the `pedalboard` library, and sends the modified audio to a virtual audio output. You can then select this virtual output as your microphone in other applications.

---

## Installation & Usage

### 1. Prerequisites

*   **Python:** Make sure you have Python 3.8+ installed.
*   **VB-CABLE:** You need to install a virtual audio cable.
    1.  Go to the [VB-AUDIO website](https://vb-audio.com/Cable/).
    2.  Download and install VB-CABLE. This will create a new virtual input/output device on your system.
*   **Rubberband:** This project requires the `rubberband` library and its command-line executable.
    1.  The `rubberband.exe` required for `pyrubberband` is included in this repository. Ensure it's in the same directory as the main script.

### 2. Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Karadumann/vchange.git
    cd vchange
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**
    *   **Windows:** `venv\Scripts\activate`
    *   **macOS/Linux:** `source venv/bin/activate`

4.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

### 3. Running the Application

1.  Run the main script:
    ```bash
    python main.py
    ```
2.  In the V-Change application:
    *   Select your actual microphone as the **Input Device**.
    *   Select `CABLE Input (VB-Audio Virtual Cable)` as the **Output Device**.
3.  In your desired application (e.g., Discord):
    *   Go to Voice & Video settings.
    *   Set your **Input Device** to `CABLE Output (VB-Audio Virtual Cable)`.
4.  Click "Start" in V-Change and start talking!

---

## Building the `.exe`

To create a standalone executable file, you can use `PyInstaller`:

```bash
pyinstaller --onefile --windowed --add-data "rubberband.exe;." --icon=your_icon.ico main.py -n V-Change
```
The final executable will be in the `dist/` folder.

---

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

Please read the [contributing guidelines](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Berk Karaduman 
