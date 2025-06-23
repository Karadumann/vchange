# V-Change: Real-Time Voice Changer

V-Change is a sophisticated real-time voice changing application built with Python and CustomTkinter. It allows users to modify their voice's pitch and timbre in real-time, apply various audio effects, and route the modified audio to other applications like Discord, Zoom, or OBS using a virtual audio cable.

## Features

- **Real-Time Audio Processing**: Modifies microphone input with minimal latency.
- **Advanced Voice Shaping**:
  - **Pitch Shifting**: Make your voice deeper or higher.
  - **Timbre (EQ) Control**: Adjust the character of your voice using High-Pass and Low-Pass filters for more realistic transformations.
- **Ambient & FX Suite**:
  - **Reverb**: Add a sense of space to your voice.
  - **Chorus**: Create the effect of multiple voices speaking in unison.
  - **Delay**: Add a distinct echo to your voice.
- **Preset System**:
  - Comes with several built-in presets like "Lower Timbre", "Higher Timbre", and "Clear Voice".
  - **Save & Delete Custom Presets**: Create your own unique voice profiles, save them, and manage them directly from the UI. Your presets are saved locally in a `presets.json` file.
- **User-Friendly Interface**:
  - A modern, tabbed UI to keep controls organized.
  - Live input volume meter.
  - **"Test My Voice" Mode**: A dedicated switch to instantly route audio to your speakers/headphones to test your effects before going live.
  - A resizable and responsive layout.

## How to Use

1.  **Virtual Audio Cable**: To use this application with other programs (like Discord), you **must** install a virtual audio cable. A popular free option is [VB-CABLE](https://vb-audio.com/Cable/).
2.  **Run the Application**:
    - If you have the `.exe` file, simply run `V-Change.exe`.
    - If running from source, run `python main.py` within the project's virtual environment.
3.  **Configure V-Change**:
    - In the `Output` dropdown, select **`CABLE Input (VB-Audio Virtual Cable)`**. This sends the modified sound to the virtual cable.
    - Choose your physical microphone in the `Input` dropdown.
    - Press **Start**.
4.  **Configure Your Target Application (e.g., Discord)**:
    - Go to your application's audio settings.
    - Set its **Input Device** to **`CABLE Output (VB-Audio Virtual Cable)`**.
5.  **Enjoy**: Your voice will now be modified in real-time! Use the "Test My Voice" switch to hear your effects directly through your headphones at any time.

## Building from Source

If you want to run or build the project from its source code:

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd vchange
    ```
2.  **Create and activate a virtual environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate  # On Windows
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run the application**:
    ```bash
    python main.py
    ```
5.  **(Optional) Build the .exe**:
    Make sure you have `rubberband.exe` in the root directory. Then, run the following command:
    ```bash
    pip install pyinstaller
    pyinstaller --noconfirm --onefile --windowed --name "V-Change" --add-data "rubberband.exe;." main.py
    ```
    The final executable will be in the `dist/` folder. 