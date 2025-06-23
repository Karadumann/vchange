import pyaudio
import numpy as np
from pedalboard import Pedalboard, PitchShift, Reverb
import threading
import customtkinter as ctk

class VoiceChanger:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream_active = False
        self.thread = None

        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        
        self.input_device_index = self.p.get_default_input_device_info()['index']
        self.output_device_index = self.p.get_default_output_device_info()['index']
        
        self.board = Pedalboard([])
        self.pitch_shifter = PitchShift(semitones=0)
        self.reverb = Reverb(room_size=0.0)
        
        self.update_effects(pitch=0.0, reverb_on=False, room_size=0.0)

    def update_effects(self, pitch=None, reverb_on=None, room_size=None):
        if pitch is not None:
            self.pitch_shifter.semitones = pitch
        
        if room_size is not None:
            self.reverb.room_size = room_size

        new_board = []
        if self.pitch_shifter.semitones != 0:
            new_board.append(self.pitch_shifter)
            
        if reverb_on:
            new_board.append(self.reverb)

        self.board.plugins = new_board

    def set_input_device(self, index):
        self.input_device_index = index

    def set_output_device(self, index):
        self.output_device_index = index
        
    def get_devices(self):
        devices = []
        for i in range(self.p.get_device_count()):
            devices.append(self.p.get_device_info_by_index(i))
        return devices

    def start(self):
        if not self.stream_active:
            self.stream_active = True
            self.thread = threading.Thread(target=self._process_audio)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        if self.stream_active:
            self.stream_active = False
            if self.thread:
                self.thread.join(timeout=1.0)

    def _process_audio(self):
        try:
            stream_in = self.p.open(format=self.FORMAT,
                                    channels=self.CHANNELS,
                                    rate=self.RATE,
                                    input=True,
                                    frames_per_buffer=self.CHUNK,
                                    input_device_index=self.input_device_index)

            stream_out = self.p.open(format=self.FORMAT,
                                     channels=self.CHANNELS,
                                     rate=self.RATE,
                                     output=True,
                                     frames_per_buffer=self.CHUNK,
                                     output_device_index=self.output_device_index)
        except OSError:
            self.stream_active = False
            return

        while self.stream_active:
            try:
                data_in = stream_in.read(self.CHUNK, exception_on_overflow=False)
                audio_data_int16 = np.frombuffer(data_in, dtype=np.int16)
                audio_data_float32 = audio_data_int16.astype(np.float32) / 32767.0
                
                if len(self.board.plugins) > 0:
                    processed_audio = self.board(audio_data_float32, self.RATE)
                    processed_audio_int16 = (processed_audio * 32767.0).astype(np.int16)
                    data_out = processed_audio_int16.tobytes()
                else:
                    data_out = data_in

                stream_out.write(data_out)
            except IOError:
                self.stream_active = False

        stream_in.stop_stream()
        stream_in.close()
        stream_out.stop_stream()
        stream_out.close()
        
    def __del__(self):
        if self.stream_active:
            self.stop()
        self.p.terminate()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.voice_changer = VoiceChanger()

        self.title("V-Change")
        self.geometry("500x550")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        ctk.set_appearance_mode("dark")

        devices = self.voice_changer.get_devices()
        input_devices = {dev['name']: dev['index'] for dev in devices if dev['maxInputChannels'] > 0}
        output_devices = {dev['name']: dev['index'] for dev in devices if dev['maxOutputChannels'] > 0}

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(padx=20, pady=20, fill="both", expand=True)
        
        ctk.CTkLabel(self.main_frame, text="Input Device (Microphone):").pack(anchor="w", padx=10)
        self.input_menu = ctk.CTkOptionMenu(self.main_frame, values=list(input_devices.keys()), command=lambda name: self.voice_changer.set_input_device(input_devices[name]))
        self.input_menu.pack(padx=10, pady=(0, 10), fill="x")
        
        ctk.CTkLabel(self.main_frame, text="Output Device (Speaker/Virtual Cable):").pack(anchor="w", padx=10)
        self.output_menu = ctk.CTkOptionMenu(self.main_frame, values=list(output_devices.keys()), command=lambda name: self.voice_changer.set_output_device(output_devices[name]))
        self.output_menu.pack(padx=10, pady=(0, 20), fill="x")

        self.pitch_label = ctk.CTkLabel(self.main_frame, text="Pitch Shift: 0.0")
        self.pitch_label.pack()
        self.pitch_slider = ctk.CTkSlider(self.main_frame, from_=-12, to=12, number_of_steps=48, command=self.update_pitch)
        self.pitch_slider.set(0)
        self.pitch_slider.pack(padx=10, pady=(0,10), fill="x")

        self.reverb_switch = ctk.CTkSwitch(self.main_frame, text="Reverb", command=self.toggle_reverb)
        self.reverb_switch.pack(padx=10, pady=10)
        
        self.presets_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.presets_frame.pack(pady=20)
        ctk.CTkLabel(self.presets_frame, text="Presets").pack()
        
        self.preset_buttons_frame = ctk.CTkFrame(self.presets_frame)
        self.preset_buttons_frame.pack(pady=10)
        
        ctk.CTkButton(self.preset_buttons_frame, text="Deep Voice", command=lambda: self.apply_preset(pitch=-8)).pack(side="left", padx=5)
        ctk.CTkButton(self.preset_buttons_frame, text="High Voice", command=lambda: self.apply_preset(pitch=8)).pack(side="left", padx=5)
        ctk.CTkButton(self.preset_buttons_frame, text="Echo", command=lambda: self.apply_preset(pitch=0, reverb=True, room_size=0.7)).pack(side="left", padx=5)
        ctk.CTkButton(self.preset_buttons_frame, text="Normal (Reset)", command=lambda: self.apply_preset(pitch=0, reverb=False)).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Off", font=("Arial", 16))
        self.status_label.pack(pady=10)
        
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(pady=10)

        self.start_button = ctk.CTkButton(self.button_frame, text="Start", command=self.start_voice_changer)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ctk.CTkButton(self.button_frame, text="Stop", command=self.stop_voice_changer, state="disabled")
        self.stop_button.pack(side="left", padx=5)

    def apply_preset(self, pitch, reverb=False, room_size=0.0):
        self.pitch_slider.set(pitch)
        self.update_pitch(pitch)
        if reverb:
            self.reverb_switch.select()
        else:
            self.reverb_switch.deselect()
        self.voice_changer.update_effects(pitch=pitch, reverb_on=reverb, room_size=room_size)
    
    def toggle_reverb(self):
        is_on = self.reverb_switch.get() == 1
        current_pitch = self.pitch_slider.get()
        self.voice_changer.update_effects(pitch=current_pitch, reverb_on=is_on, room_size=0.7 if is_on else 0.0)

    def update_pitch(self, value):
        pitch_value = round(value, 2)
        self.pitch_label.configure(text=f"Pitch Shift: {pitch_value}")
        is_on = self.reverb_switch.get() == 1
        self.voice_changer.update_effects(pitch=pitch_value, reverb_on=is_on)

    def start_voice_changer(self):
        self.voice_changer.start()
        self.status_label.configure(text="Status: Active", text_color="green")
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.input_menu.configure(state="disabled")
        self.output_menu.configure(state="disabled")

    def stop_voice_changer(self):
        self.voice_changer.stop()
        self.status_label.configure(text="Status: Off", text_color="red")
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.input_menu.configure(state="normal")
        self.output_menu.configure(state="normal")

    def on_closing(self):
        self.voice_changer.stop()
        self.destroy()

if __name__ == '__main__':
    app = App()
    app.mainloop() 