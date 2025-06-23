import pyaudio
import numpy as np
from pedalboard import Pedalboard, PitchShift, Reverb, Chorus, Delay
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
        self.chorus = Chorus()
        self.delay = Delay()
        
        self.update_effects()

    def update_effects(self, pitch=0.0, reverb_on=False, room_size=0.0, chorus_on=False, delay_on=False):
        self.pitch_shifter.semitones = pitch
        self.reverb.room_size = room_size

        new_board = []
        if pitch != 0:
            new_board.append(self.pitch_shifter)
        if reverb_on:
            new_board.append(self.reverb)
        if chorus_on:
            new_board.append(self.chorus)
        if delay_on:
            new_board.append(self.delay)

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
        self.geometry("500x650")
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
        self.pitch_slider = ctk.CTkSlider(self.main_frame, from_=-12, to=12, number_of_steps=48, command=self._update_all_effects)
        self.pitch_slider.set(0)
        self.pitch_slider.pack(padx=10, pady=(0,10), fill="x")

        self.effects_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.effects_frame.pack(pady=10)
        self.reverb_switch = ctk.CTkSwitch(self.effects_frame, text="Reverb", command=self._update_all_effects)
        self.reverb_switch.pack(side="left", padx=10)
        self.chorus_switch = ctk.CTkSwitch(self.effects_frame, text="Chorus", command=self._update_all_effects)
        self.chorus_switch.pack(side="left", padx=10)
        self.delay_switch = ctk.CTkSwitch(self.effects_frame, text="Delay", command=self._update_all_effects)
        self.delay_switch.pack(side="left", padx=10)
        
        self.presets_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.presets_frame.pack(pady=20)
        ctk.CTkLabel(self.presets_frame, text="Presets").pack()
        
        self.preset_buttons_frame = ctk.CTkFrame(self.presets_frame)
        self.preset_buttons_frame.pack(pady=10)
        
        ctk.CTkButton(self.preset_buttons_frame, text="Deep", command=lambda: self.apply_preset(pitch=-7)).pack(side="left", padx=5)
        ctk.CTkButton(self.preset_buttons_frame, text="High", command=lambda: self.apply_preset(pitch=7)).pack(side="left", padx=5)
        ctk.CTkButton(self.preset_buttons_frame, text="Alien", command=lambda: self.apply_preset(pitch=4, chorus=True)).pack(side="left", padx=5)
        ctk.CTkButton(self.preset_buttons_frame, text="Spacious", command=lambda: self.apply_preset(pitch=0, reverb=True, delay=True)).pack(side="left", padx=5)
        ctk.CTkButton(self.preset_buttons_frame, text="Normal", command=lambda: self.apply_preset(pitch=0)).pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(self.main_frame, text="Status: Off", font=("Arial", 16))
        self.status_label.pack(pady=10)
        
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(pady=10)

        self.start_button = ctk.CTkButton(self.button_frame, text="Start", command=self.start_voice_changer)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ctk.CTkButton(self.button_frame, text="Stop", command=self.stop_voice_changer, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
    def _update_all_effects(self, pitch_value=None):
        pitch = self.pitch_slider.get()
        reverb_on = self.reverb_switch.get() == 1
        chorus_on = self.chorus_switch.get() == 1
        delay_on = self.delay_switch.get() == 1
        
        self.pitch_label.configure(text=f"Pitch Shift: {round(pitch, 2)}")
        
        self.voice_changer.update_effects(
            pitch=pitch,
            reverb_on=reverb_on,
            room_size=0.7 if reverb_on else 0.0,
            chorus_on=chorus_on,
            delay_on=delay_on
        )

    def apply_preset(self, pitch, reverb=False, chorus=False, delay=False):
        self.pitch_slider.set(pitch)
        
        if reverb: self.reverb_switch.select()
        else: self.reverb_switch.deselect()

        if chorus: self.chorus_switch.select()
        else: self.chorus_switch.deselect()

        if delay: self.delay_switch.select()
        else: self.delay_switch.deselect()

        self._update_all_effects()

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